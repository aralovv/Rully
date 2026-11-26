"""
Phase 3 Verification Suite — Driver's Cockpit Design System & Core Navigation.

Verifies unified 5-tab IA ordering across desktop and mobile docks, Daylight Asphalt
and Midnight Carbon OLED design tokens, 240-degree speedometer geometry helpers,
required DOM hooks, 3-language cockpit telemetry translations, and FastAPI static delivery.
"""
import re
from pathlib import Path
from fastapi.testclient import TestClient

from src.api.main import app


ROOT_DIR = Path(__file__).resolve().parent.parent
client = TestClient(app)


def test_unified_navigation_order_and_core_ids():
    html = (ROOT_DIR / "static" / "index.html").read_text(encoding="utf-8")

    # Desktop sidebar and mobile dock must share identical 5-tab IA order
    expected_tabs = ["home", "tests", "amaliy", "ai", "profile"]
    sidebar_block = re.search(r'<aside class="desktop-sidebar".*?</aside>', html, re.S)
    dock_block = re.search(r'<nav class="mobile-dock".*?</nav>', html, re.S)
    assert sidebar_block is not None
    assert dock_block is not None

    sidebar_tabs = re.findall(r'data-tab="([a-z]+)"', sidebar_block.group(0))
    dock_tabs = re.findall(r'data-tab="([a-z]+)"', dock_block.group(0))
    assert sidebar_tabs == expected_tabs
    assert dock_tabs == expected_tabs

    # Required defer scripts & v5 cache-busters preserved
    assert '/static/css/rully.css?v=5.0.0' in html
    for js in ("icons.js", "translations.js", "cheatsheet_data.js", "core/theme.js", "views/reference.js", "views/home.js", "app.js"):
        assert f'script defer src="/static/js/{js}?v=5.0.0"' in html

    # Required view containers and modals preserved
    for dom_id in (
        "view-home",
        "view-tests",
        "view-amaliy",
        "view-ai",
        "view-profile",
        "view-quiz",
        "view-results",
        "readiness-diagnostic-modal",
        "daily-goal-modal",
        "lang-modal",
    ):
        assert f'id="{dom_id}"' in html


def test_cockpit_design_tokens_and_accessibility_rules():
    css = (ROOT_DIR / "static" / "css" / "rully.css").read_text(encoding="utf-8")
    assert "--bg-canvas: #F1F2F4;" in css
    assert "--bg-canvas: #090B0E;" in css
    assert ".cockpit-gauge-box" in css
    assert ".cockpit-needle" in css
    assert ".exam-launch-card" in css
    assert ".modal-sheet::before" in css
    assert "@media (prefers-reduced-motion: reduce)" in css

    theme_js = (ROOT_DIR / "static" / "js" / "core" / "theme.js").read_text(encoding="utf-8")
    assert "#090B0E" in theme_js
    assert "#F1F2F4" in theme_js


def test_cockpit_home_dial_and_translations():
    home_js = (ROOT_DIR / "static" / "js" / "views" / "home.js").read_text(encoding="utf-8")
    assert "buildCockpitTicks" in home_js
    assert "276.46" in home_js
    assert "cockpit_free_quota" in home_js
    for dom_id in (
        "home-diag-btn",
        "home-start-exam-btn",
        "home-daily-goal-card",
        "home-smart-rec-btn",
        "tile-tickets",
        "tile-categories",
        "tile-mistakes",
        "tile-adaptive",
        "tile-amaliy",
        "tile-cheatsheet",
    ):
        assert dom_id in home_js

    trans_js = (ROOT_DIR / "static" / "js" / "translations.js").read_text(encoding="utf-8")
    cockpit_keys = (
        "cockpit_live_badge:",
        "cockpit_spec_questions:",
        "cockpit_spec_time:",
        "cockpit_spec_limit:",
        "cockpit_free_quota:",
    )
    for key in cockpit_keys:
        assert trans_js.count(key) == 3, f"Expected {key} in all 3 languages"


def test_cockpit_static_assets_served():
    for path in (
        "/",
        "/static/css/rully.css?v=5.0.0",
        "/static/js/views/reference.js?v=5.0.0",
        "/static/js/views/home.js?v=5.0.0",
        "/static/js/core/theme.js?v=5.0.0",
    ):
        res = client.get(path)
        assert res.status_code == 200
