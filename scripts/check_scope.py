#!/usr/bin/env python3
"""Seleciona gates de validacao a partir do diff Git do checkout atual."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        text=True,
        capture_output=True,
        check=False,
    )


def changed_files(base_ref: str) -> list[str]:
    merge_base = git("merge-base", base_ref, "HEAD")
    if merge_base.returncode != 0 or not merge_base.stdout.strip():
        raise RuntimeError(f"nao foi possivel resolver a base Git {base_ref!r}")

    paths: set[str] = set()
    commands = (
        ("diff", "--name-only", f"{merge_base.stdout.strip()}..HEAD"),
        ("diff", "--cached", "--name-only"),
        ("diff", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    )
    for command in commands:
        result = git(*command)
        if result.returncode != 0:
            raise RuntimeError("nao foi possivel ler o diff Git")
        paths.update(line for line in result.stdout.splitlines() if line)
    return sorted(paths)


FULL_GATES = {"backend", "compose", "docs", "frontend", "playwright", "postgres"}


def classify(paths: list[str]) -> list[str]:
    gates: set[str] = set()
    unknown: list[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        first_part = path.parts[0] if path.parts else ""
        if (
            raw_path == "Makefile"
            or raw_path.startswith("scripts/check_")
            or raw_path == "tests/test_make_check.py"
            or raw_path.startswith(".github/workflows/")
        ):
            gates.update(FULL_GATES)
        elif first_part in {"api", "core", "alembic"}:
            gates.update({"backend", "postgres"})
        elif first_part in {"scripts", "tests"} or path.name in {
            "requirements.txt",
            "pyproject.toml",
            "pytest.ini",
            "ruff.toml",
        } or (len(path.parts) == 1 and path.suffix == ".py"):
            gates.add("backend")
        elif first_part == "frontend":
            gates.add("frontend")
            if len(path.parts) > 1 and path.parts[1] in {"src", "e2e"}:
                gates.add("playwright")
        elif path.name.startswith("docker-compose") or path.name in {
            "Dockerfile",
            ".dockerignore",
        } or (path.name.startswith(".env") and path.name.endswith(".example")):
            gates.add("compose")
        elif first_part == "docs" or path.name == "README.md":
            gates.add("docs")
        else:
            unknown.append(raw_path)

    if unknown:
        raise RuntimeError(
            "escopo desconhecido para: " + ", ".join(sorted(unknown))
        )
    if not gates:
        raise RuntimeError("nenhuma alteracao encontrada para validar")
    return sorted(gates)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", default="origin/main")
    args = parser.parse_args()
    try:
        for gate in classify(changed_files(args.base_ref)):
            print(gate)
    except RuntimeError as exc:
        print(f"check-scope: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
