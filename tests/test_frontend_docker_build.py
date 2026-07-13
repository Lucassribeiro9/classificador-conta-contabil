from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"


def test_frontend_image_builds_vite_spa_and_serves_it_without_api_fallback():
    dockerfile = (FRONTEND_ROOT / "Dockerfile").read_text(encoding="utf-8")
    nginx_config = (FRONTEND_ROOT / "nginx.conf").read_text(encoding="utf-8")
    dockerignore = (FRONTEND_ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "FROM node:" in dockerfile
    assert "AS build" in dockerfile
    assert "RUN npm ci" in dockerfile
    assert "ARG VITE_API_BASE_URL=/api" in dockerfile
    assert "ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}" in dockerfile
    assert "RUN npm run build" in dockerfile
    assert "FROM nginx:" in dockerfile
    assert "COPY --from=build /app/dist /usr/share/nginx/html" in dockerfile

    assert "location ^~ /api" in nginx_config
    assert "return 404;" in nginx_config
    assert "try_files $uri $uri/ /index.html;" in nginx_config

    ignored_paths = set(dockerignore.splitlines())
    assert {"node_modules", "dist", ".env", ".env.*"} <= ignored_paths
