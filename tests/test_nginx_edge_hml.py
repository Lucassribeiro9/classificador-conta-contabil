from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EDGE_COMPOSE_PATH = PROJECT_ROOT / "docker-compose.edge.yml"
NGINX_CONFIG_PATH = PROJECT_ROOT / "infra/nginx/hml.conf"


def test_hml_edge_compose_exposes_only_nginx_on_http_and_https():
    compose = yaml.safe_load(EDGE_COMPOSE_PATH.read_text(encoding="utf-8"))

    assert compose["name"] == "classificador-edge-hml"
    assert set(compose["services"]) == {"nginx"}

    nginx = compose["services"]["nginx"]
    assert nginx["image"] == "nginx:1.27-alpine"
    assert nginx["ports"] == ["80:80", "443:443"]
    assert nginx["networks"] == ["hml-edge"]
    assert "healthcheck" in nginx

    assert compose["networks"]["hml-edge"] == {
        "external": True,
        "name": "classificador-hml-edge",
    }

    volumes = nginx["volumes"]
    assert "./infra/nginx/hml.conf:/etc/nginx/conf.d/default.conf:ro" in volumes
    assert any(
        volume.startswith("${HML_TLS_CERT_PATH:")
        and volume.endswith(":/etc/nginx/certs/classificador-hml.crt:ro")
        for volume in volumes
    )
    assert any(
        volume.startswith("${HML_TLS_KEY_PATH:")
        and volume.endswith(":/etc/nginx/certs/classificador-hml.key:ro")
        for volume in volumes
    )


def test_hml_nginx_terminates_tls_and_routes_frontend_and_api():
    nginx_config = " ".join(
        NGINX_CONFIG_PATH.read_text(encoding="utf-8").split()
    )

    required_directives = (
        "listen 80;",
        "listen 443 ssl;",
        "server_name classificador-hml.interno;",
        'return 200 "ok\\n";',
        "return 301 https://$host$request_uri;",
        "ssl_certificate /etc/nginx/certs/classificador-hml.crt;",
        "ssl_certificate_key /etc/nginx/certs/classificador-hml.key;",
        "location /api/ { proxy_pass http://api:8000/;",
        "location / { proxy_pass http://frontend:80;",
        "proxy_set_header X-Forwarded-Proto $scheme;",
    )

    for directive in required_directives:
        assert directive in nginx_config


def test_hml_edge_environment_ci_and_runbook_cover_safe_operation():
    env_example = (PROJECT_ROOT / ".env.hml.example").read_text(encoding="utf-8")
    ci = (PROJECT_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    runbook = " ".join(
        (PROJECT_ROOT / "docs/devops-hml.md")
        .read_text(encoding="utf-8")
        .split()
    )

    assert "HML_TLS_CERT_PATH=/etc/classificador/certs/classificador-hml.crt" in (
        env_example
    )
    assert "HML_TLS_KEY_PATH=/etc/classificador/certs/classificador-hml.key" in (
        env_example
    )
    assert (
        "docker compose --env-file .env.hml.example "
        "-f docker-compose.edge.yml config --quiet"
    ) in ci

    required_operations = (
        "docker network create classificador-hml-edge",
        "classificador-hml.interno",
        "certificado emitido pela CA interna",
        "docker-compose.hml.yml up -d --build",
        "somente depois que `api` e `frontend` estiverem `healthy`",
        "docker-compose.edge.yml up -d",
        "docker-compose.edge.yml exec nginx nginx -t",
        "docker network inspect classificador-hml-edge",
        "python -m scripts.smoke_homologacao",
        "docker-compose.edge.yml down",
    )
    for operation in required_operations:
        assert operation in runbook

    tracked_certificates = tuple(
        path
        for path in (PROJECT_ROOT / "infra/nginx").rglob("*")
        if path.suffix.lower() in {".crt", ".key", ".pem"}
    )
    assert tracked_certificates == ()
