import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def _read(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def test_frontend_package_declares_expected_stack_and_scripts():
    package = json.loads((FRONTEND / "package.json").read_text(encoding="utf-8"))

    assert package["scripts"] == {
        "dev": "vite",
        "build": "vite build",
        "typecheck": "tsc --noEmit",
        "lint": "eslint .",
        "test": "vitest run",
    }
    dependencies = package["dependencies"]
    assert "react" in dependencies
    assert "react-dom" in dependencies
    assert "react-router-dom" in dependencies
    assert "@tanstack/react-query" in dependencies


def test_frontend_route_constants_cover_mvp_paths():
    routes = _read("src/routes/paths.ts")

    expected_paths = [
        "/login",
        "/empresas",
        "/empresas/:empresaId",
        "/empresas/:empresaId/movimentos/importar",
        "/empresas/:empresaId/movimentos/lotes/:loteId",
        "/empresas/:empresaId/movimentos/:movimentoId",
        "/empresas/:empresaId/razao",
    ]
    missing = [path for path in expected_paths if path not in routes]
    assert missing == []


def test_frontend_shell_protects_internal_routes_and_shows_company_context():
    app_router = _read("src/app/AppRouter.tsx")
    protected_route = _read("src/app/ProtectedRoute.tsx")
    app_shell = _read("src/app/AppShell.tsx")

    assert "ProtectedRoute" in app_router
    assert 'to={ROUTES.login}' in protected_route
    assert "Sessao expirada" in protected_route
    assert "useParams" in app_shell
    assert "Empresa selecionada" in app_shell
    assert "empresaId" in app_shell


def test_frontend_non_login_pages_are_placeholders_without_api_implementation():
    pages = "\n".join(
        [
            _read("src/routes/pages/EmpresasPage.tsx"),
            _read("src/routes/pages/OperacaoEmpresaPage.tsx"),
            _read("src/routes/pages/ImportarMovimentosPage.tsx"),
            _read("src/routes/pages/LoteMovimentosPage.tsx"),
            _read("src/routes/pages/RevisarMovimentoPage.tsx"),
            _read("src/routes/pages/RazaoContasPage.tsx"),
        ]
    )
    placeholder = _read("src/routes/pages/PagePlaceholder.tsx")
    login_page = _read("src/routes/pages/LoginPage.tsx")

    assert pages.count("<PagePlaceholder") == 6
    assert "<PagePlaceholder" not in login_page
    assert "Placeholder da issue #272" in placeholder
    assert "chamada real da API fica fora do escopo" in placeholder
