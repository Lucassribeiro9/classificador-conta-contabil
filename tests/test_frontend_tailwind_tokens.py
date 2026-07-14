from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def read_frontend(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def test_visual_tokens_are_centralized_in_frontend_styles():
    tokens = read_frontend("src/styles/tokens.ts")

    assert "visualTokens" in tokens
    assert "#007693" in tokens
    assert "#004E61" in tokens
    assert "neutral" in tokens
    assert "compact" in tokens


def test_tailwind_config_uses_central_visual_tokens():
    config = read_frontend("tailwind.config.ts")

    assert 'from "./src/styles/tokens"' in config
    assert "visualTokens.colors.brand" in config
    assert "visualTokens.colors.brandDark" in config
    assert "visualTokens.radius" in config


def test_global_styles_expose_base_tokens_and_tailwind_layers():
    global_css = read_frontend("src/styles/global.css")

    assert "@tailwind base;" in global_css
    assert "@tailwind components;" in global_css
    assert "@tailwind utilities;" in global_css
    assert "--color-brand: #007693;" in global_css
    assert "--color-brand-dark: #004e61;" in global_css
    assert "--color-surface: #ffffff;" in global_css


def test_style_token_usage_is_documented_concisely():
    readme = read_frontend("src/styles/README.md")

    assert "Tailwind" in readme
    assert "`visualTokens`" in readme
    assert "#007693" in readme
    assert "#004E61" in readme
    assert "UI operacional compacta" in readme
