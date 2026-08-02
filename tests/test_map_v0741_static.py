from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_v0741_assets_are_loaded_with_map_version():
    template = content("templates/map.html")
    assert "map-v0741.css' %}?v={{ map_version }}" in template
    assert "map-v0741-ui.js' %}?v={{ map_version }}" in template


def test_canvas_has_fit_zoom_and_no_scrollbars():
    ui = content("static/js/map-v0741-ui.js")
    css = content("static/css/map-v0741.css")
    assert "data-canvas-zoom-fit" in ui
    assert "event.ctrlKey" in ui
    assert "fitCanvas" in ui
    assert ".master-canvas-scroll" in css
    assert "overflow: hidden !important" in css


def test_cancel_button_is_not_duplicated_with_drawing_bar():
    ui = content("static/js/map-v0741-ui.js")
    css = content("static/css/map-v0741.css")
    assert 'const contextual = Boolean(drawingBar && !drawingBar.hidden)' in ui
    assert "cancel.hidden = !active || contextual" in ui
    assert '#drawing-bar:not([hidden])' in css
    assert '[data-v0722-cancel]' in css


def test_collapsed_sidebar_hides_message_and_scrollbars():
    css = content("static/css/map-v0741.css")
    assert "#map-sidebar.v072-collapsed #editor-message" in css
    assert "scrollbar-width: none" in css
    assert "overflow-x: hidden" in css


def test_asset_sheet_handles_nested_metadata_without_vertical_text():
    ui = content("static/js/map-v0741-ui.js")
    css = content("static/css/map-v0741.css")
    assert "has-nested-value-v0741" in ui
    assert "nested-definition-v0741" in ui
    assert "word-break: break-word" in css
    assert "overflow-x: hidden" in css
    assert "v0741-lifecycle-card" in ui


def test_container_toolbar_has_icons_and_single_commandbar():
    ui = content("static/js/map-v0741-ui.js")
    css = content("static/css/map-v0741.css")
    assert "master-container-commandbar-v0741" in ui
    assert "v0741-button-icon" in ui
    assert "master-container-commandbar-v0741" in css


def test_versions_are_independent():
    settings = content("config/settings.py")
    compose = content("docker-compose.yml")
    assert 'PLATFORM_VERSION = os.getenv("PLATFORM_VERSION", os.getenv("APP_VERSION", "0.77.0"))' in settings
    assert 'MAP_VERSION = os.getenv("MAP_VERSION", "0.74.1")' in settings
    assert 'PLATFORM_VERSION: ${PLATFORM_VERSION:-0.77.0}' in compose
    assert 'MAP_VERSION: ${MAP_VERSION:-0.74.1}' in compose


def test_validator_expands_untracked_files():
    validator = content("scripts/validate_map_v0741.py")
    assert '"--untracked-files=all"' in validator
