from pathlib import Path

from packaging.requirements import Requirement


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _requirements_by_name():
    requirements = {}
    for raw_line in (PROJECT_ROOT / "requirements.txt").read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        requirement = Requirement(line)
        requirements[requirement.name.lower()] = requirement

    return requirements


def test_postgresql_driver_psycopg_v3_declared_without_removing_existing_database_dependencies():
    requirements = _requirements_by_name()

    assert "psycopg" in requirements
    assert "psycopg2" not in requirements
    assert "sqlalchemy" in requirements
    assert "binary" in requirements["psycopg"].extras
    assert requirements["psycopg"].specifier.contains("3.2.13", prereleases=False)


def test_password_hash_pwdlib_argon2_declared_for_auth_bootstrap():
    requirements = _requirements_by_name()

    assert "pwdlib" in requirements
    assert "argon2" in requirements["pwdlib"].extras
    assert requirements["pwdlib"].specifier.contains("0.3.0", prereleases=False)
