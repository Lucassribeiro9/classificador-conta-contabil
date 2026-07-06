from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def read_frontend(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def test_login_page_implements_jwt_form_and_operational_states():
    login_page = read_frontend("src/routes/pages/LoginPage.tsx")

    assert "authClient.login" in login_page
    assert 'name="email"' in login_page
    assert 'name="password"' in login_page
    assert 'type="password"' in login_page
    assert "Credenciais invalidas" in login_page
    assert "Nao foi possivel conectar" in login_page
    assert "Sessao expirada" in login_page
    assert "ROUTES.empresas" in login_page
    assert "Esqueci minha senha" not in login_page


def test_auth_client_posts_credentials_to_api_login_endpoint():
    auth_client = read_frontend("src/lib/api/authClient.ts")

    assert "VITE_API_BASE_URL" in auth_client
    assert '"/auth/login"' in auth_client
    assert "email" in auth_client
    assert "password" in auth_client
    assert "access_token" in auth_client
    assert "InvalidCredentialsError" in auth_client
    assert "NetworkAuthError" in auth_client


def test_auth_session_persists_jwt_in_memory_boundary_only():
    auth_context = read_frontend("src/app/auth.tsx")

    assert "accessToken" in auth_context
    assert "userEmail" in auth_context
    assert "localStorage" not in auth_context
    assert "sessionStorage" not in auth_context
