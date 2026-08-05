from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from ipaddress import ip_address, ip_network
from typing import Callable, Protocol

from agent_runner import RunnerAction, RunnerRequest, RunnerResponse

ENVELOPE_FIELDS = {
    "contract_version",
    "event_id",
    "action",
    "repository",
    "issue_number",
    "requested_at",
    "nonce",
    "expected_state",
    "payload",
}
FORBIDDEN_FIELDS = {
    "command",
    "prompt",
    "script",
    "shell",
    "instructions",
    "secret",
    "accounting_data",
    "diff",
}
ALLOWED_PAYLOAD_FIELDS = {
    "implement": {"base_branch", "base_sha", "approved_branch", "task_review_ref"},
    "resume": {"execution_id", "checkpoint_ref"},
    "cancel": {"execution_id"},
    "status": {"execution_id"},
}
ALLOWED_EXPECTED_STATES = {
    "agent:awaiting-task-review",
    "agent:awaiting-human",
    "agent:ready-to-implement",
    "agent:running",
    "agent:awaiting-manual-test",
    "agent:validated",
    "agent:blocked",
    "agent:cancelled",
}
REQUIRED_HEADERS = {
    "X-Agent-Key-Id",
    "X-Agent-Timestamp",
    "X-Agent-Nonce",
    "X-Agent-Signature",
}


@dataclass(frozen=True)
class HmacKey:
    secret: str
    active: bool


class HmacKeyStore(Protocol):
    def get(self, key_id: str) -> HmacKey | None: ...


class ReplayStore(Protocol):
    def register_nonce(self, key_id: str, nonce: str, timestamp: str) -> bool: ...


class RunnerHandler(Protocol):
    def handle(self, request: RunnerRequest) -> RunnerResponse: ...


class InMemoryHmacKeyStore:
    def __init__(self, keys: dict[str, HmacKey]) -> None:
        self._keys = keys

    def get(self, key_id: str) -> HmacKey | None:
        return self._keys.get(key_id)


class InMemoryNonceStore:
    def __init__(self) -> None:
        self._seen: set[tuple[str, str]] = set()

    def register_nonce(self, key_id: str, nonce: str, timestamp: str) -> bool:
        key = (key_id, nonce)
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


class PrivateRunnerInterface:
    def __init__(
        self,
        *,
        runner: RunnerHandler,
        key_store: HmacKeyStore,
        now: Callable[[], datetime],
        allowed_repositories: set[str],
        allowed_client_networks: tuple[str, ...] = (
            "127.0.0.0/8",
            "10.0.0.0/8",
            "172.16.0.0/12",
            "192.168.0.0/16",
        ),
        replay_store: ReplayStore | None = None,
        timestamp_window_seconds: int = 300,
    ) -> None:
        self.runner = runner
        self.key_store = key_store
        self.now = now
        self.allowed_repositories = allowed_repositories
        self.allowed_client_networks = tuple(
            ip_network(network) for network in allowed_client_networks
        )
        self.replay_store = replay_store or InMemoryNonceStore()
        self.timestamp_window_seconds = timestamp_window_seconds

    def handle_http_like_request(
        self,
        *,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes,
        client_host: str,
    ) -> dict[str, object]:
        data = self._decode_body(body)
        event_id = data.get("event_id") if isinstance(data, dict) else None
        action = self._parse_action(data)
        if action is None:
            return self._rejected(event_id, RunnerAction.STATUS, "ACTION_NOT_ALLOWED", "Action is not allowed.")
        if not self._contract_allowed(data):
            return self._rejected(event_id, action, "ACTION_NOT_ALLOWED", "Action is not allowed.")
        if not REQUIRED_HEADERS <= set(headers):
            return self._rejected(event_id, action, "INVALID_SIGNATURE", "Invalid signature.")

        key_id = headers["X-Agent-Key-Id"]
        timestamp = headers["X-Agent-Timestamp"]
        nonce = headers["X-Agent-Nonce"]
        key = self.key_store.get(key_id)
        if key is None or not key.active:
            return self._rejected(event_id, action, "INVALID_SIGNATURE", "Invalid signature.")
        if not self._private_client(client_host):
            return self._rejected(event_id, action, "ACTION_NOT_ALLOWED", "Action is not allowed.")
        if method != "POST" or path != "/agent/runner":
            return self._rejected(event_id, action, "ACTION_NOT_ALLOWED", "Action is not allowed.")
        if timestamp != data["requested_at"] or not self._timestamp_current(timestamp):
            return self._rejected(
                event_id,
                action,
                "REPLAY_REJECTED",
                "Request timestamp was rejected.",
            )
        if not self._signature_valid(
            method=method,
            path=path,
            timestamp=timestamp,
            nonce=nonce,
            body=body,
            secret=key.secret,
            signature=headers["X-Agent-Signature"],
        ):
            return self._rejected(event_id, action, "INVALID_SIGNATURE", "Invalid signature.")
        if not self.replay_store.register_nonce(key_id, nonce, timestamp):
            return self._rejected(
                event_id,
                action,
                "REPLAY_REJECTED",
                "Request replay was rejected.",
            )
        if data["repository"] not in self.allowed_repositories:
            return self._rejected(event_id, action, "ACTION_NOT_ALLOWED", "Action is not allowed.")

        response = self.runner.handle(
            RunnerRequest(
                event_id=data["event_id"],
                action=action,
                repository=data["repository"],
                issue_number=data["issue_number"],
                expected_state=data["expected_state"],
                payload=data["payload"],
            )
        )
        return {
            "contract_version": "1",
            "event_id": response.event_id,
            "execution_id": response.execution_id,
            "action": response.action.value,
            "status": response.status.value,
            "code": response.code,
            "message": self._sanitize_message(response.message),
            "retryable": response.retryable,
            "github_ref": None,
        }

    def _decode_body(self, body: bytes) -> dict[str, object] | None:
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def _parse_action(self, data: dict[str, object] | None) -> RunnerAction | None:
        if not isinstance(data, dict):
            return None
        try:
            return RunnerAction(str(data.get("action")))
        except ValueError:
            return None

    def _contract_allowed(self, data: dict[str, object] | None) -> bool:
        if not isinstance(data, dict):
            return False
        if set(data) != ENVELOPE_FIELDS:
            return False
        if data["contract_version"] != "1":
            return False
        action = data.get("action")
        if action not in ALLOWED_PAYLOAD_FIELDS:
            return False
        if data.get("expected_state") not in ALLOWED_EXPECTED_STATES:
            return False
        if not isinstance(data.get("issue_number"), int) or data["issue_number"] <= 0:
            return False
        payload = data.get("payload")
        if not isinstance(payload, dict):
            return False
        if self._contains_forbidden_field(data):
            return False
        return set(payload) == ALLOWED_PAYLOAD_FIELDS[str(action)]

    def _contains_forbidden_field(self, value: object) -> bool:
        if isinstance(value, dict):
            return any(
                key in FORBIDDEN_FIELDS or self._contains_forbidden_field(nested)
                for key, nested in value.items()
            )
        if isinstance(value, list):
            return any(self._contains_forbidden_field(item) for item in value)
        return False

    def _private_client(self, client_host: str) -> bool:
        address = ip_address(client_host)
        return any(address in network for network in self.allowed_client_networks)

    def _timestamp_current(self, value: str) -> bool:
        try:
            requested_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return False
        if requested_at.tzinfo is None:
            return False
        delta = abs(
            (
                self.now().astimezone(timezone.utc)
                - requested_at.astimezone(timezone.utc)
            ).total_seconds()
        )
        return delta <= self.timestamp_window_seconds

    def _signature_valid(
        self,
        *,
        method: str,
        path: str,
        timestamp: str,
        nonce: str,
        body: bytes,
        secret: str,
        signature: str,
    ) -> bool:
        body_hash = hashlib.sha256(body).hexdigest()
        canonical = "\n".join([method, path, timestamp, nonce, body_hash])
        expected = hmac.new(
            secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def _sanitize_message(self, value: str) -> str:
        lowered = value.lower()
        forbidden = (
            "token",
            "secret",
            "signature",
            "prompt",
            "diff",
            "raw_log",
            "/home/",
            "/tmp/",
        )
        if any(item in lowered for item in forbidden):
            return "Sanitized message withheld."
        return value

    def _rejected(
        self,
        event_id: str | None,
        action: RunnerAction,
        code: str,
        message: str,
    ) -> dict[str, object]:
        return {
            "contract_version": "1",
            "event_id": event_id,
            "execution_id": None,
            "action": action.value,
            "status": "rejected",
            "code": code,
            "message": message,
            "retryable": False,
            "github_ref": None,
        }
