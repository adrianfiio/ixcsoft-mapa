from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(path: str, needle: str) -> None:
    content = (ROOT / path).read_text(encoding="utf-8")
    if needle not in content:
        raise AssertionError(f"{path}: marcador ausente: {needle}")


def forbid(path: str, needle: str) -> None:
    content = (ROOT / path).read_text(encoding="utf-8")
    if needle in content:
        raise AssertionError(f"{path}: conteúdo proibido ainda presente: {needle}")


def main() -> int:
    required_files = [
        "static/js/map-link-monitoring-v074.js",
        "static/css/map-v074-rework.css",
        "apps/snmp_monitoring/management/commands/cleanup_invalid_snmp_profiles.py",
    ]
    for filename in required_files:
        if not (ROOT / filename).exists():
            raise AssertionError(f"Arquivo ausente: {filename}")

    require("templates/network_map/map_editor.html", "map-v074-rework.css")
    require("templates/network_map/map_editor.html", "map-link-monitoring-v074.js")
    forbid("templates/network_map/map_editor.html", "js/map-link-monitoring.js' %}?v={{ app_version }}\"></script>")

    require("apps/snmp_monitoring/api.py", "UNIVERSAL_SNMP_EQUIPMENT_TYPES")
    require("apps/snmp_monitoring/api.py", '"monitoring_enabled"')
    require("apps/snmp_monitoring/tasks.py", "equipment__provisioning_mode")
    require("apps/network_map/api/views.py", '"monitoring_eligible"')
    require("static/js/map-master-suite.js", "data-monitoring-eligible")

    js = (ROOT / "static/js/map-link-monitoring-v074.js").read_text(encoding="utf-8")
    if "MutationObserver" in js:
        raise AssertionError("O runtime v0.74 não pode usar MutationObserver global.")
    if "15000" in js:
        raise AssertionError("O polling visual antigo de 15 segundos não pode permanecer.")
    if not re.search(r'SUPPORTED_TYPES\s*=\s*new Set\(\[.*?"switch"', js, re.S):
        raise AssertionError("Lista explícita de tipos SNMP não encontrada.")
    for forbidden_type in ('"dio"', '"pto"', '"server"', '"olt"'):
        supported_block = re.search(r"SUPPORTED_TYPES\s*=\s*new Set\((.*?)\);", js, re.S).group(1)
        if forbidden_type in supported_block:
            raise AssertionError(f"Tipo passivo/proibido em SUPPORTED_TYPES: {forbidden_type}")

    print("OK: validações estáticas da v0.74 concluídas.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
