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
