#!/usr/bin/env python3
"""Rejeita indicios de segredos no diff sem ecoar o conteudo detectado."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from check_scope import changed_files, git


SECRET_PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    (
        "assigned-secret",
        re.compile(
            r"(?i)\b(?:password|passwd|secret|token|api[_-]?key|credential)\b"
            r"\s*[:=]\s*['\"]?[A-Za-z0-9+/=_-]{24,}"
        ),
    ),
)
FORBIDDEN_NAMES = {".env", "id_rsa", "id_ed25519"}
FORBIDDEN_SUFFIXES = {".pem", ".p12", ".pfx", ".key"}


def merge_base(base_ref: str) -> str:
    result = git("merge-base", base_ref, "HEAD")
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"nao foi possivel resolver a base Git {base_ref!r}")
    return result.stdout.strip()


def added_content_by_path(base_ref: str) -> dict[str, str]:
    base = merge_base(base_ref)
    chunks: dict[str, list[str]] = {}
    for command in (
        ("diff", "--unified=0", f"{base}..HEAD"),
        ("diff", "--cached", "--unified=0"),
        ("diff", "--unified=0"),
    ):
        result = git(*command)
        if result.returncode != 0:
            raise RuntimeError("nao foi possivel ler o diff Git")
        current_path: str | None = None
        for line in result.stdout.splitlines():
            if line.startswith("+++ b/"):
                current_path = line[6:]
                chunks.setdefault(current_path, [])
            elif line.startswith("+") and not line.startswith("+++"):
                if current_path is not None:
                    chunks[current_path].append(line[1:])

    tracked = set(git("ls-files").stdout.splitlines())
    for raw_path in changed_files(base_ref):
        if raw_path in tracked:
            continue
        path = Path(raw_path)
        try:
            chunks[raw_path] = [path.read_text(encoding="utf-8")]
        except (OSError, UnicodeDecodeError):
            continue
    return {path: "\n".join(lines) for path, lines in chunks.items()}


def suspicious_paths(paths: list[str]) -> list[str]:
    suspicious: list[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            if path.name not in {".env.example", ".env.hml.example", ".env.prod.example"}:
                suspicious.append(raw_path)
    return suspicious


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", default="origin/main")
    args = parser.parse_args()

    try:
        paths = changed_files(args.base_ref)
        content_by_path = added_content_by_path(args.base_ref)
    except RuntimeError as exc:
        print(f"check-security: {exc}", file=sys.stderr)
        return 2

    findings = [(path, "sensitive-file") for path in suspicious_paths(paths)]
    for path, content in content_by_path.items():
        for category, pattern in SECRET_PATTERNS:
            if pattern.search(content):
                findings.append((path, category))

    if findings:
        affected = ", ".join(sorted({path for path, _ in findings}))
        categories = ", ".join(sorted({category for _, category in findings}))
        print(
            f"check-security: material potencialmente sensivel em {affected} "
            f"(categorias: {categories})",
            file=sys.stderr,
        )
        return 1

    print("check-security: diff sem indicios de segredo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
