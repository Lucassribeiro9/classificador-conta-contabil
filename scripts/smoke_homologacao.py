import argparse
import json
import subprocess
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen


class SmokeHomologacaoError(RuntimeError):
    pass


def _git_reference() -> str:
    values = []
    for args in (("--abbrev-ref", "HEAD"), ("--short", "HEAD")):
        result = subprocess.run(
            ["git", "rev-parse", *args],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return "indisponivel"
        values.append(result.stdout.strip())
    return "@".join(values)


def _validated_base_url(value: str) -> str:
    base_url = value.rstrip("/")
    parsed = urlparse(base_url)
    is_loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and is_loopback
    ):
        raise SmokeHomologacaoError(
            "A URL HML deve usar HTTPS; HTTP e permitido apenas em loopback."
        )
    has_extra_parts = any(
        (parsed.path, parsed.params, parsed.query, parsed.fragment)
    )
    if not parsed.hostname or parsed.username or parsed.password or has_extra_parts:
        raise SmokeHomologacaoError(
            "Informe apenas a origem HML, sem credenciais, caminho ou query."
        )
    return base_url


def _validate_health(base_url: str) -> None:
    try:
        with urlopen(f"{base_url}/api/health", timeout=10) as response:
            payload = json.load(response)
    except (HTTPError, URLError, json.JSONDecodeError) as exc:
        raise SmokeHomologacaoError(
            "API /health indisponivel ou com resposta invalida."
        ) from exc

    if payload.get("status") != "online" or payload.get("database") != "online":
        raise SmokeHomologacaoError("API ou banco nao esta online em HML.")


def _validate_login(base_url: str) -> None:
    try:
        with urlopen(f"{base_url}/login", timeout=10) as response:
            html = response.read().decode("utf-8")
    except (HTTPError, URLError, UnicodeDecodeError) as exc:
        raise SmokeHomologacaoError(
            "Tela /login indisponivel ou com resposta invalida."
        ) from exc

    required_markers = (
        '<div id="root"',
        "<title>Classificador contabil</title>",
    )
    if not all(marker in html for marker in required_markers):
        raise SmokeHomologacaoError(
            "Tela /login nao entregou o shell esperado da SPA."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke minimo da aplicacao HML.")
    parser.add_argument("--base-url", required=True, help="Origem HTTPS de HML.")
    args = parser.parse_args()

    try:
        base_url = _validated_base_url(args.base_url)
        _validate_health(base_url)
        _validate_login(base_url)
    except SmokeHomologacaoError as exc:
        raise SystemExit(f"Smoke HML bloqueado: {exc}") from exc

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"Executado em UTC: {timestamp}")
    print(f"Git: {_git_reference()}")
    print(f"Base HML: {base_url}")
    print("API /health: APROVADO")
    print("Tela /login: APROVADO")


if __name__ == "__main__":
    main()
