"""Contratos publicos dos gates ``make check`` e ``make check-full``."""

from __future__ import annotations

from pathlib import Path
import pytest
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECK_SCOPE = PROJECT_ROOT / "scripts" / "check_scope.py"
CHECK_SECURITY = PROJECT_ROOT / "scripts" / "check_diff_security.py"


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def init_repository(path: Path) -> None:
    run("git", "init", "-b", "main", cwd=path)
    run("git", "config", "user.name", "Test Runner", cwd=path)
    run("git", "config", "user.email", "test@example.invalid", cwd=path)
    (path / "README.md").write_text("# Baseline\n", encoding="utf-8")
    run("git", "add", "README.md", cwd=path)
    result = run("git", "commit", "-m", "baseline", cwd=path)
    assert result.returncode == 0, result.stderr


def test_scope_classifier_selects_docs_for_an_untracked_document(tmp_path: Path):
    init_repository(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guia.md").write_text("# Guia\n", encoding="utf-8")

    result = run(
        sys.executable,
        str(CHECK_SCOPE),
        "--base-ref",
        "HEAD",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["docs"]


def test_scope_classifier_selects_backend_and_postgres_for_persistence(tmp_path: Path):
    init_repository(tmp_path)
    core = tmp_path / "core"
    core.mkdir()
    (core / "models.py").write_text("class Conta: pass\n", encoding="utf-8")

    result = run(
        sys.executable,
        str(CHECK_SCOPE),
        "--base-ref",
        "HEAD",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["backend", "postgres"]


def test_scope_classifier_selects_frontend_and_playwright_for_ui_flow(tmp_path: Path):
    init_repository(tmp_path)
    page = tmp_path / "frontend" / "src" / "routes" / "pages"
    page.mkdir(parents=True)
    (page / "LoginPage.tsx").write_text("export const LoginPage = () => null;\n")

    result = run(
        sys.executable,
        str(CHECK_SCOPE),
        "--base-ref",
        "HEAD",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["frontend", "playwright"]


def test_scope_classifier_uses_every_gate_for_harness_changes(tmp_path: Path):
    init_repository(tmp_path)
    (tmp_path / "Makefile").write_text("check:\n\t@true\n", encoding="utf-8")

    result = run(
        sys.executable,
        str(CHECK_SCOPE),
        "--base-ref",
        "HEAD",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == [
        "backend",
        "compose",
        "docs",
        "frontend",
        "playwright",
        "postgres",
    ]


def test_scope_classifier_fails_closed_for_an_unknown_path(tmp_path: Path):
    init_repository(tmp_path)
    (tmp_path / "arquivo.bin").write_bytes(b"conteudo")

    result = run(
        sys.executable,
        str(CHECK_SCOPE),
        "--base-ref",
        "HEAD",
        cwd=tmp_path,
    )

    assert result.returncode == 2
    assert "escopo desconhecido" in result.stderr
    assert "arquivo.bin" in result.stderr
    assert result.stdout == ""


def test_security_check_reports_path_without_echoing_the_secret(tmp_path: Path):
    init_repository(tmp_path)
    exposed = "ghp_" + "A" * 32
    (tmp_path / "notes.txt").write_text(
        f"token={exposed}\n",
        encoding="utf-8",
    )

    result = run(
        sys.executable,
        str(CHECK_SECURITY),
        "--base-ref",
        "HEAD",
        cwd=tmp_path,
    )

    assert result.returncode == 1
    assert "notes.txt" in result.stderr
    assert exposed not in result.stdout
    assert exposed not in result.stderr


def test_make_exposes_proportional_and_full_check_targets():
    proportional = run(
        "make",
        "-n",
        f"PYTHON={sys.executable}",
        f"CHECK_PYTHON={sys.executable}",
        "check",
        cwd=PROJECT_ROOT,
    )
    full = run(
        "make",
        "-n",
        f"PYTHON={sys.executable}",
        f"CHECK_PYTHON={sys.executable}",
        "check-full",
        cwd=PROJECT_ROOT,
    )

    assert proportional.returncode == 0, proportional.stderr
    assert "scripts/check_scope.py" in proportional.stdout
    for gate in (
        "security", "backend", "postgres", "frontend", "playwright", "compose", "docs"
    ):
        assert f"[check] {gate}" in proportional.stdout

    assert full.returncode == 0, full.stderr
    for gate in (
        "security", "backend", "postgres", "frontend", "playwright", "compose", "docs"
    ):
        assert gate in full.stdout


@pytest.mark.parametrize(
    ("changed_path", "expected"),
    [
        ("scripts/maintenance.py", ["backend"]),
        ("tests/test_api.py", ["backend"]),
        ("requirements.txt", ["backend"]),
        ("docker-compose.hml.yml", ["compose"]),
        ("frontend/package.json", ["frontend"]),
    ],
)
def test_scope_classifier_routes_representative_project_paths(
    tmp_path: Path,
    changed_path: str,
    expected: list[str],
):
    init_repository(tmp_path)
    path = tmp_path / changed_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("conteudo\n", encoding="utf-8")

    result = run(
        sys.executable,
        str(CHECK_SCOPE),
        "--base-ref",
        "HEAD",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == expected


def test_scope_classifier_includes_committed_changes_since_the_base(tmp_path: Path):
    init_repository(tmp_path)
    core = tmp_path / "core"
    core.mkdir()
    (core / "service.py").write_text("def execute(): pass\n", encoding="utf-8")
    run("git", "add", "core/service.py", cwd=tmp_path)
    committed = run("git", "commit", "-m", "backend change", cwd=tmp_path)
    assert committed.returncode == 0, committed.stderr

    result = run(
        sys.executable,
        str(CHECK_SCOPE),
        "--base-ref",
        "HEAD~1",
        cwd=tmp_path,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines() == ["backend", "postgres"]


def test_scope_classifier_fails_closed_when_base_does_not_exist(tmp_path: Path):
    init_repository(tmp_path)

    result = run(
        sys.executable,
        str(CHECK_SCOPE),
        "--base-ref",
        "missing/base",
        cwd=tmp_path,
    )

    assert result.returncode == 2
    assert "nao foi possivel resolver a base Git" in result.stderr
    assert result.stdout == ""


def test_security_check_fails_closed_when_base_does_not_exist(tmp_path: Path):
    init_repository(tmp_path)

    result = run(
        sys.executable,
        str(CHECK_SECURITY),
        "--base-ref",
        "missing/base",
        cwd=tmp_path,
    )

    assert result.returncode == 2
    assert "nao foi possivel resolver a base Git" in result.stderr
    assert result.stdout == ""


def test_postgres_gate_is_announced_before_execution_and_always_cleans_up():
    result = run("make", "-n", "check-postgres", cwd=PROJECT_ROOT)

    assert result.returncode == 0, result.stderr
    announcement = 'echo "[check] postgres"'
    startup = "up -d --build"
    assert announcement in result.stdout
    assert startup in result.stdout
    assert result.stdout.index(announcement) < result.stdout.index(startup)
    assert "trap cleanup EXIT INT TERM" in result.stdout
    assert "down -v" in result.stdout


def test_make_check_propagates_the_first_gate_failure():
    result = run(
        "make",
        "PYTHON=false",
        f"CHECK_PYTHON={sys.executable}",
        "CHECK_BASE_REF=origin/main",
        "check",
        cwd=PROJECT_ROOT,
    )

    assert result.returncode != 0
    assert "[check] security" in result.stdout
    assert "[check] backend" in result.stdout
    assert "[check] frontend" not in result.stdout
    assert "validacao proporcional concluida" not in result.stdout


def test_readme_documents_both_executable_gates():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "Use `make check` como gate local proporcional" in readme
    assert "Use `make check-full`" in readme
