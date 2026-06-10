from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/02-auth-usuarios-permissoes.md"


def test_auth_spec_records_jwt_and_password_hash_libraries():
    spec = SPEC.read_text(encoding="utf-8")

    assert "PyJWT" in spec
    assert "HS256" in spec
    assert "pwdlib[argon2]" in spec
    assert "Argon2id" in spec


def test_auth_spec_records_access_token_shape_without_refresh_token():
    spec = SPEC.read_text(encoding="utf-8")

    assert "`sub`" in spec
    assert "`exp`" in spec
    assert "`iat`" in spec
    assert "`type`" in spec
    assert "`access`" in spec
    assert "sem refresh token" in spec


def test_auth_spec_records_library_compatibility_and_refresh_boundary():
    spec = SPEC.read_text(encoding="utf-8")

    assert "compativeis com Python 3.12 e FastAPI" in spec
    assert "Refresh token permanece fora desta fase" in spec


def test_auth_spec_no_longer_has_jwt_hash_library_as_open_question():
    spec = SPEC.read_text(encoding="utf-8")

    assert "Qual biblioteca JWT/hash sera usada na implementacao?" not in spec
