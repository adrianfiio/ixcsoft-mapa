from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_container_observer_does_not_watch_rendered_children():
    master = content("static/js/map-master-suite.js")
    start = master.index("let scheduledContainer")
    end = master.index("    }\n\n    async function init", start)
    block = master[start:end]
    assert "childList" not in block
    assert "subtree" not in block
    assert "await loadContainerMaster(false)" in master


def test_monitoring_browser_snapshot_is_five_minutes_and_without_observer():
    runtime = content("static/js/map-link-monitoring-v074.js")
    assert "5 * 60 * 1000" in runtime
    assert "MutationObserver" not in runtime
    assert "setInterval" not in runtime


def test_passive_and_server_types_are_not_universal_snmp():
    api = content("apps/snmp_monitoring/api.py")
    allowed = api.split("UNIVERSAL_SNMP_EQUIPMENT_TYPES = {", 1)[1].split("}", 1)[0]
    for forbidden in ("DIO", "PTO", "SERVER", "OLT"):
        assert forbidden not in allowed


def test_new_ui_assets_use_map_version():
    template_path = ROOT / "templates/map.html"
    if not template_path.exists():
        template_path = ROOT / "templates/network_map/map_editor.html"
    template = template_path.read_text(encoding="utf-8")
    for asset in ("map-v074.css", "map-v074-ui.js", "map-link-monitoring-v074.js"):
        assert f"{asset}' %}}?v={{{{ map_version }}}}" in template


def test_platform_version_is_untouched():
    settings = content("config/settings.py")
    compose = content("docker-compose.yml")
    assert 'PLATFORM_VERSION = os.getenv("PLATFORM_VERSION", os.getenv("APP_VERSION", "0.76.0"))' in settings
    assert 'MAP_VERSION = os.getenv("MAP_VERSION", "0.74.0")' in settings
    assert 'PLATFORM_VERSION: ${PLATFORM_VERSION:-0.76.0}' in compose
    assert 'MAP_VERSION: ${MAP_VERSION:-0.74.0}' in compose


def test_ficha_and_context_menu_exist():
    master = content("static/js/map-master-suite.js")
    ui = content("static/js/map-v074-ui.js")
    assert "master-sheet-grid" in master
    assert "Imprimir / PDF" in master
    assert "map-context-v074" in ui
    assert "data-v074-labels" in ui
