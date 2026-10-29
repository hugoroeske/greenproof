"""Smoke tests for the Streamlit app: theme config, one-click demo, theme switch and all views."""
import tomllib
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = str(ROOT / "app.py")
CONFIG_KEYS = {"primary": "primaryColor", "bg": "backgroundColor", "bg2": "secondaryBackgroundColor",
               "text": "textColor", "border": "borderColor"}


def load_themes():
    import ast
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "THEMES")
    return ast.literal_eval(node.value)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_config_matches_app_palette(theme):
    config = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))["theme"]
    palette = load_themes()[theme]
    for key, option in CONFIG_KEYS.items():
        assert config[theme][option].lower() == palette[key].lower(), (theme, option)
    assert config[theme]["sidebar"]["backgroundColor"].lower() == palette["sidebar"].lower()


def start_demo() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception
    at.button(key="demo_btn").click().run()
    assert not at.exception
    return at


def test_start_screen_has_one_click_demo():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert at.button(key="demo_btn").label == "Try with demo reports"
    assert "results" not in at.session_state


def test_demo_button_screens_and_keeps_ranking():
    at = start_demo()
    companies = [r.company for r in at.session_state["results"]]
    assert sorted(companies) == ["Lumen Devices", "Northpeak Apparel", "Vireo Footwear"]
    ranked = [m.value for m in at.metric]
    assert ranked[0] == "3"                                    # Companies KPI


@pytest.mark.parametrize("choice", ["light", "dark", "auto"])
def test_theme_switch_renders_every_view(choice):
    at = start_demo()
    at.segmented_control(key="theme_choice").set_value(choice).run()
    assert not at.exception
    for view in ["Ranking", "Company detail", "Validate", "Data", "Method"]:
        at.segmented_control(key="view").set_value(view).run()
        assert not at.exception, (choice, view)
