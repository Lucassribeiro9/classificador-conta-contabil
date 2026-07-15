import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SMOKE_GUIDE = PROJECT_ROOT / "docs/homologacao-smoke-aplicacao.md"
HML_GUIDE = PROJECT_ROOT / "docs/devops-hml.md"


class SmokeHandler(BaseHTTPRequestHandler):
    requested_paths: list[str] = []
    mode = "ok"

    def do_GET(self):
        self.requested_paths.append(self.path)
        if self.path == "/api/health":
            health = (
                {"status": "offline", "database": "offline"}
                if self.mode == "health_offline"
                else {"status": "online", "database": "online"}
            )
            payload = json.dumps(health).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)
            return

        if self.path == "/login":
            html = (
                "<html><body>resposta incompleta</body></html>"
                if self.mode == "login_invalid"
                else (
                    "<!doctype html><html><head><title>Classificador contabil</title>"
                    '</head><body><div id="root"></div></body></html>'
                )
            )
            payload = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(payload)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, _format, *_args):
        pass


@pytest.fixture()
def smoke_server():
    SmokeHandler.requested_paths = []
    SmokeHandler.mode = "ok"
    server = ThreadingHTTPServer(("127.0.0.1", 0), SmokeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_smoke_cli_validates_healthy_api_and_prints_sanitized_evidence(smoke_server):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.smoke_homologacao",
            "--base-url",
            smoke_server,
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Executado em UTC:" in result.stdout
    assert "Git:" in result.stdout
    assert "API /health: APROVADO" in result.stdout
    assert "Base HML: http://127.0.0.1:" in result.stdout
    assert "/api/health" in SmokeHandler.requested_paths


def test_smoke_cli_validates_login_shell(smoke_server):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.smoke_homologacao",
            "--base-url",
            smoke_server,
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Tela /login: APROVADO" in result.stdout
    assert "/login" in SmokeHandler.requested_paths


def test_smoke_cli_blocks_release_when_api_or_database_is_offline(smoke_server):
    SmokeHandler.mode = "health_offline"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.smoke_homologacao",
            "--base-url",
            smoke_server,
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "API ou banco nao esta online em HML" in result.stderr
    assert "APROVADO" not in result.stdout


def test_smoke_cli_blocks_release_when_login_shell_is_invalid(smoke_server):
    SmokeHandler.mode = "login_invalid"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.smoke_homologacao",
            "--base-url",
            smoke_server,
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "nao entregou o shell esperado da SPA" in result.stderr
    assert "APROVADO" not in result.stdout


def test_smoke_cli_rejects_credentials_embedded_in_url():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.smoke_homologacao",
            "--base-url",
            "https://usuario:segredo@classificador-hml.interno",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "sem credenciais" in result.stderr
    assert "segredo" not in result.stdout


def test_smoke_guide_records_release_commands_and_evidence_contract():
    guide = " ".join(SMOKE_GUIDE.read_text(encoding="utf-8").lower().split())

    required_content = (
        "python -m pytest -q tests",
        "npm run lint",
        "npm run typecheck",
        "npm test",
        "npm run build",
        "npm run test:e2e",
        "python -m scripts.smoke_homologacao --base-url",
        "api `/health`",
        "tela `/login`",
        "anexe a saida",
        "nao registre senhas, tokens ou segredos",
        "resultado: liberado / bloqueado",
    )

    for content in required_content:
        assert content in guide


def test_hml_runbook_routes_release_validation_to_smoke_gate():
    guide = " ".join(HML_GUIDE.read_text(encoding="utf-8").lower().split())

    assert "docs/homologacao-smoke-aplicacao.md" in guide
    assert "python -m scripts.smoke_homologacao --base-url" in guide
