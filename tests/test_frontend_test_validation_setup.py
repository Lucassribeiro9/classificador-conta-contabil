import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def read_frontend(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def test_frontend_scripts_expose_required_validation_commands():
    package_json = read_frontend("package.json")

    assert '"lint": "eslint ."' in package_json
    assert '"typecheck": "tsc --noEmit"' in package_json
    assert '"test": "vitest run"' in package_json


def test_frontend_exposes_dedicated_format_commands_and_base_config():
    package = json.loads(read_frontend("package.json"))
    prettier_config = json.loads(read_frontend(".prettierrc.json"))
    prettier_ignore = read_frontend(".prettierignore")

    assert package["scripts"]["format"] == "prettier --write ."
    assert package["scripts"]["format:check"] == "prettier --check ."
    assert "prettier" in package["devDependencies"]
    assert prettier_config == {
        "endOfLine": "lf",
        "semi": True,
        "singleQuote": False,
        "trailingComma": "all",
    }
    assert "package-lock.json" in prettier_ignore
    assert "dist/" in prettier_ignore
    assert "playwright-report/" in prettier_ignore
    assert "test-results/" in prettier_ignore


def test_vitest_uses_jsdom_and_testing_library_setup():
    vite_config = read_frontend("vite.config.ts")
    setup = read_frontend("src/test/setup.ts")

    assert 'environment: "jsdom"' in vite_config
    assert 'include: ["src/**/*.test.{ts,tsx}"]' in vite_config
    assert 'setupFiles: ["./src/test/setup.ts"]' in vite_config
    assert 'import "@testing-library/jest-dom/vitest";' in setup


def test_minimal_component_test_validates_visible_behavior_without_snapshots():
    example_test = read_frontend("src/ui/operationalMessages.test.tsx")

    assert 'from "@testing-library/react"' in example_test
    assert "render(" in example_test
    assert "screen.getByRole" in example_test
    assert "toBeInTheDocument()" in example_test
    assert "toMatchSnapshot" not in example_test
