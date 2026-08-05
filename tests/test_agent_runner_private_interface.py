from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

from agent_runner import ExecutionStatus, RunnerAction, RunnerResponse
from agent_runner.private_interface import (
    HmacKey,
    InMemoryHmacKeyStore,
    PrivateRunnerInterface,
)


class FakeRunner:
    def __init__(self, response: RunnerResponse) -> None:
        self.response = response
        self.requests = []

    def handle(self, request):
        self.requests.append(request)
        return self.response


def _body(**overrides) -> bytes:
    data = {
        "contract_version": "1",
        "event_id": "00000000-0000-4000-8000-000000000377",
        "action": "implement",
        "repository": "Lucassribeiro9/classificador-conta-contabil",
        "issue_number": 377,
        "requested_at": "2026-08-05T12:00:00Z",
        "nonce": "nonce-377",
        "expected_state": "agent:ready-to-implement",
        "payload": {
            "base_branch": "main",
            "base_sha": "abc1234",
            "approved_branch": "feat/agent-runner-interface-privada",
            "task_review_ref": "issue-377-task-review",
        },
    }
    data.update(overrides)
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _headers(body: bytes, *, secret: str = "super-secret", nonce: str = "nonce-377"):
    timestamp = "2026-08-05T12:00:00Z"
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = "\n".join(["POST", "/agent/runner", timestamp, nonce, body_hash])
    signature = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256)
    return {
        "X-Agent-Key-Id": "primary",
        "X-Agent-Timestamp": timestamp,
        "X-Agent-Nonce": nonce,
        "X-Agent-Signature": signature.hexdigest(),
    }


def _interface(runner: FakeRunner):
    return PrivateRunnerInterface(
        runner=runner,
        key_store=InMemoryHmacKeyStore(
            {"primary": HmacKey(secret="super-secret", active=True)}
        ),
        now=lambda: datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
        allowed_repositories={"Lucassribeiro9/classificador-conta-contabil"},
    )


def test_valid_signed_private_request_calls_runner_and_returns_contract_envelope():
    body = _body()
    runner = FakeRunner(
        RunnerResponse(
            event_id="00000000-0000-4000-8000-000000000377",
            execution_id="execution-377",
            action=RunnerAction.IMPLEMENT,
            status=ExecutionStatus.AWAITING_MANUAL_TEST,
            code="EXECUTION_COMPLETED",
            message="Draft ready for manual test.",
            retryable=False,
        )
    )

    response = _interface(runner).handle_http_like_request(
        method="POST",
        path="/agent/runner",
        headers=_headers(body),
        body=body,
        client_host="127.0.0.1",
    )

    assert response == {
        "contract_version": "1",
        "event_id": "00000000-0000-4000-8000-000000000377",
        "execution_id": "execution-377",
        "action": "implement",
        "status": "awaiting_manual_test",
        "code": "EXECUTION_COMPLETED",
        "message": "Draft ready for manual test.",
        "retryable": False,
        "github_ref": None,
    }
    assert len(runner.requests) == 1
    assert runner.requests[0].payload["approved_branch"] == "feat/agent-runner-interface-privada"


def test_interface_rejects_invalid_method_path_signature_and_key_before_runner():
    body = _body()
    runner = FakeRunner(
        RunnerResponse(
            event_id="00000000-0000-4000-8000-000000000377",
            execution_id="execution-377",
            action=RunnerAction.IMPLEMENT,
            status=ExecutionStatus.AWAITING_MANUAL_TEST,
            code="EXECUTION_COMPLETED",
            message="Should not run.",
            retryable=False,
        )
    )
    interface = _interface(runner)

    wrong_method = interface.handle_http_like_request(
        method="GET",
        path="/agent/runner",
        headers=_headers(body),
        body=body,
        client_host="127.0.0.1",
    )
    wrong_path = interface.handle_http_like_request(
        method="POST",
        path="/api/agent/runner",
        headers=_headers(body),
        body=body,
        client_host="127.0.0.1",
    )
    wrong_signature = interface.handle_http_like_request(
        method="POST",
        path="/agent/runner",
        headers={**_headers(body), "X-Agent-Signature": "invalid"},
        body=body,
        client_host="127.0.0.1",
    )
    wrong_key = interface.handle_http_like_request(
        method="POST",
        path="/agent/runner",
        headers={**_headers(body), "X-Agent-Key-Id": "unknown"},
        body=body,
        client_host="127.0.0.1",
    )

    assert wrong_method["code"] == "ACTION_NOT_ALLOWED"
    assert wrong_path["code"] == "ACTION_NOT_ALLOWED"
    assert wrong_signature["code"] == "INVALID_SIGNATURE"
    assert wrong_key["code"] == "INVALID_SIGNATURE"
    assert runner.requests == []


def test_interface_rejects_expired_timestamp_repeated_nonce_and_public_client(tmp_path):
    body = _body()
    runner = FakeRunner(
        RunnerResponse(
            event_id="00000000-0000-4000-8000-000000000377",
            execution_id="execution-377",
            action=RunnerAction.IMPLEMENT,
            status=ExecutionStatus.AWAITING_MANUAL_TEST,
            code="EXECUTION_COMPLETED",
            message="Draft ready.",
            retryable=False,
        )
    )
    interface = _interface(runner)

    expired = PrivateRunnerInterface(
        runner=runner,
        key_store=InMemoryHmacKeyStore({"primary": HmacKey(secret="super-secret", active=True)}),
        now=lambda: datetime(2026, 8, 5, 12, 6, tzinfo=timezone.utc),
        allowed_repositories={"Lucassribeiro9/classificador-conta-contabil"},
    ).handle_http_like_request(
        method="POST",
        path="/agent/runner",
        headers=_headers(body),
        body=body,
        client_host="127.0.0.1",
    )
    public_client = interface.handle_http_like_request(
        method="POST",
        path="/agent/runner",
        headers=_headers(body),
        body=body,
        client_host="8.8.8.8",
    )
    first = interface.handle_http_like_request(
        method="POST",
        path="/agent/runner",
        headers=_headers(body),
        body=body,
        client_host="127.0.0.1",
    )
    replay = interface.handle_http_like_request(
        method="POST",
        path="/agent/runner",
        headers=_headers(body),
        body=body,
        client_host="127.0.0.1",
    )

    assert expired["code"] == "REPLAY_REJECTED"
    assert public_client["code"] == "ACTION_NOT_ALLOWED"
    assert first["code"] == "EXECUTION_COMPLETED"
    assert replay["code"] == "REPLAY_REJECTED"
    assert len(runner.requests) == 1


def test_interface_rejects_closed_contract_violations_and_forbidden_fields():
    runner = FakeRunner(
        RunnerResponse(
            event_id="00000000-0000-4000-8000-000000000377",
            execution_id="execution-377",
            action=RunnerAction.IMPLEMENT,
            status=ExecutionStatus.AWAITING_MANUAL_TEST,
            code="EXECUTION_COMPLETED",
            message="Should not run.",
            retryable=False,
        )
    )
    interface = _interface(runner)

    extra_envelope_body = _body(extra="not allowed", nonce="nonce-extra")
    invalid_version_body = _body(contract_version="2.0.0", nonce="nonce-version")
    forbidden_nested_body = _body(
        nonce="nonce-forbidden",
        payload={
            "base_branch": "main",
            "base_sha": "abc1234",
            "approved_branch": "feat/agent-runner-interface-privada",
            "task_review_ref": "issue-377-task-review",
            "shell": "pytest",
        },
    )

    extra = interface.handle_http_like_request(
        method="POST",
        path="/agent/runner",
        headers=_headers(extra_envelope_body, nonce="nonce-extra"),
        body=extra_envelope_body,
        client_host="127.0.0.1",
    )
    invalid_version = interface.handle_http_like_request(
        method="POST",
        path="/agent/runner",
        headers=_headers(invalid_version_body, nonce="nonce-version"),
        body=invalid_version_body,
        client_host="127.0.0.1",
    )
    forbidden = interface.handle_http_like_request(
        method="POST",
        path="/agent/runner",
        headers=_headers(forbidden_nested_body, nonce="nonce-forbidden"),
        body=forbidden_nested_body,
        client_host="127.0.0.1",
    )

    assert extra["code"] == "ACTION_NOT_ALLOWED"
    assert invalid_version["code"] == "ACTION_NOT_ALLOWED"
    assert forbidden["code"] == "ACTION_NOT_ALLOWED"
    assert runner.requests == []


def test_interface_sanitizes_runner_message_before_external_response():
    body = _body(nonce="nonce-sensitive")
    runner = FakeRunner(
        RunnerResponse(
            event_id="00000000-0000-4000-8000-000000000377",
            execution_id="execution-377",
            action=RunnerAction.IMPLEMENT,
            status=ExecutionStatus.BLOCKED,
            code="EXECUTION_BLOCKED",
            message="token abc leaked at /home/n8n-user/private/path",
            retryable=True,
        )
    )

    response = _interface(runner).handle_http_like_request(
        method="POST",
        path="/agent/runner",
        headers=_headers(body, nonce="nonce-sensitive"),
        body=body,
        client_host="127.0.0.1",
    )

    assert response["message"] == "Sanitized message withheld."
    assert response["retryable"] is True
    assert "/home" not in str(response)
    assert "token" not in str(response).lower()


def test_interface_requires_action_specific_payload_fields():
    runner = FakeRunner(
        RunnerResponse(
            event_id="00000000-0000-4000-8000-000000000377",
            execution_id="execution-377",
            action=RunnerAction.IMPLEMENT,
            status=ExecutionStatus.AWAITING_MANUAL_TEST,
            code="EXECUTION_COMPLETED",
            message="Should not run.",
            retryable=False,
        )
    )
    interface = _interface(runner)
    missing_implement_branch = _body(nonce="nonce-missing", payload={"base_branch": "main"})
    missing_status_execution = _body(
        nonce="nonce-status",
        action="status",
        expected_state="agent:running",
        payload={},
    )

    implement_response = interface.handle_http_like_request(
        method="POST",
        path="/agent/runner",
        headers=_headers(missing_implement_branch, nonce="nonce-missing"),
        body=missing_implement_branch,
        client_host="127.0.0.1",
    )
    status_response = interface.handle_http_like_request(
        method="POST",
        path="/agent/runner",
        headers=_headers(missing_status_execution, nonce="nonce-status"),
        body=missing_status_execution,
        client_host="127.0.0.1",
    )

    assert implement_response["code"] == "ACTION_NOT_ALLOWED"
    assert status_response["code"] == "ACTION_NOT_ALLOWED"
    assert runner.requests == []
