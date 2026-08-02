#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "a141a28ebe2c6de9cf2d264041c9362203bffa54"

ALLOWED_EXACT = {
    "templates/map.html",
    "static/js/map-master-suite.js",
    "static/js/map-link-monitoring-v074.js",
    "static/js/map-v074-ui.js",
    "static/css/map-v074.css",
    "apps/network_map/api/views.py",
    "apps/snmp_monitoring/api.py",
    "apps/snmp_monitoring/tasks.py",
    "apps/snmp_monitoring/management/commands/cleanup_invalid_snmp_profiles.py",
    "scripts/validate_map_v074.py",
    "tests/test_map_v074_static.py",
    "config/settings.py",
    "docker-compose.yml",
    "README.md",
    "CHANGELOG_MAP.md",
    "VERSIONS.md",
    "docs/releases/map/map-v0.74.0.md",
}


def read(relative: str) -> str:
    path = ROOT / relative
    if not path.exists():
        raise AssertionError(f"Arquivo ausente: {relative}")
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run(cmd: list[str], *, check=True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if check and result.returncode:
        raise AssertionError(f"Comando falhou: {' '.join(cmd)}\n{result.stdout}\n{result.stderr}")
    return result


def changed_paths() -> set[str]:
    result = run(["git", "status", "--porcelain"], check=False)
    if result.returncode:
        return set()
    paths = set()
    for line in result.stdout.splitlines():
        raw = line[3:].strip()
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        paths.add(raw.replace("\\", "/"))
    return paths


def main() -> int:
    head = run(["git", "rev-parse", "HEAD"], check=False).stdout.strip()
    require(not head or head == BASE_COMMIT, f"HEAD inesperado durante validação: {head}")

    template = read("templates/map.html") if (ROOT / "templates/map.html").exists() else read("templates/network_map/map_editor.html")
    master = read("static/js/map-master-suite.js")
    monitor = read("static/js/map-link-monitoring-v074.js")
    ui = read("static/js/map-v074-ui.js")
    css = read("static/css/map-v074.css")
    api = read("apps/snmp_monitoring/api.py")
    tasks = read("apps/snmp_monitoring/tasks.py")
    network_api = read("apps/network_map/api/views.py")
    settings = read("config/settings.py")
    compose = read("docker-compose.yml")
    readme = read("README.md")
    versions = read("VERSIONS.md")
    changelog_map = read("CHANGELOG_MAP.md")

    require("map-link-monitoring-v074.js' %}?v={{ map_version }}" in template, "Runtime SNMP não usa map_version")
    require("map-v074-ui.js' %}?v={{ map_version }}" in template, "UI do mapa não usa map_version")
    require("map-v074.css' %}?v={{ map_version }}" in template, "CSS do mapa não usa map_version")
    require("map-link-monitoring.js'" not in template and 'map-link-monitoring.js"' not in template, "Runtime antigo ainda carregado")

    require("loadingPromise" in master and "loadingElementId === id" in master, "Proteção de requisição simultânea ausente")
    require("await loadContainerMaster(false)" in master, "A abertura continua forçando recarga")
    require("scheduledContainer" in master, "Observer do container não foi estabilizado")
    container_observer = re.search(r'new MutationObserver\(\(\) => \{.*?scheduledContainer.*?\)\.observe\(container, \{(.*?)\}\);', master, re.S)
    require(bool(container_observer), "Observer do container não localizado")
    require("childList" not in container_observer.group(1) and "subtree" not in container_observer.group(1), "Observer do container ainda reage à própria renderização")

    require("5 * 60 * 1000" in monitor, "Snapshot web não está em cinco minutos")
    require("MutationObserver" not in monitor, "Runtime de monitoramento voltou a usar MutationObserver")
    require("setInterval" not in monitor, "Runtime de monitoramento voltou a usar setInterval")
    require('button.textContent = "SNMP"' in monitor, "Ação SNMP compacta ausente")
    require('SUPPORTED_TYPES = new Set(["switch", "router", "firewall", "access_point", "ptp", "onu", "other"])' in monitor, "Tipos monitoráveis divergentes")

    require("UNIVERSAL_SNMP_EQUIPMENT_TYPES" in api, "Backend sem lista central de elegibilidade")
    require('"refresh_interval_seconds": 300' in api, "Snapshot backend não informa cinco minutos")
    require("equipment__provisioning_mode=ContainerEquipment.ProvisioningMode.SNMP" in api, "Snapshot aceita equipamento manual")
    require("equipment__equipment_type__in=UNIVERSAL_SNMP_EQUIPMENT_TYPES" in api, "Snapshot não filtra tipos")
    require('equipment__provisioning_mode="snmp"' in tasks, "Celery aceita equipamento manual")
    require('equipment__equipment_type__in=eligible_types' in tasks, "Celery não filtra tipos")

    container_block = re.search(r'def container_equipment\(.*?return JsonResponse', network_api, re.S)
    require(bool(container_block), "Endpoint container_equipment não localizado")
    require("EquipmentType.SERVER" not in container_block.group(0), "Servidor ainda permitido no cadastro do mapa")
    require('"monitoring_eligible"' in network_api and '"monitoring_configured"' in network_api, "Payload de elegibilidade ausente")

    require("map-context-v074" in ui and "contextmenu" in ui, "Menu de botão direito ausente")
    require("data-v074-labels" in ui, "Alternância de nomes ausente")
    require("compactContainerWorkspace" in ui, "Compactação do Rack/Torre ausente")
    require("master-sheet-grid" in master and "Imprimir / PDF" in master, "Ficha técnica nova ausente")
    require("--v074-nav-color" in css and ".map-context-v074" in css, "Estilos de hover/menu contextual ausentes")

    require('PLATFORM_VERSION = os.getenv("PLATFORM_VERSION", os.getenv("APP_VERSION", "0.76.0"))' in settings, "PLATFORM_VERSION foi alterada")
    require('MAP_VERSION = os.getenv("MAP_VERSION", "0.74.0")' in settings, "MAP_VERSION não está em 0.74.0")
    require('PLATFORM_VERSION: ${PLATFORM_VERSION:-0.76.0}' in compose, "Versão da plataforma no Compose foi alterada")
    require('MAP_VERSION: ${MAP_VERSION:-0.74.0}' in compose, "Versão do mapa no Compose não está em 0.74.0")
    require("| Plataforma | v0.76.0 |" in readme and "| Mapa | v0.74.0 |" in readme, "Tabela de versões do README divergente")
    require("| Plataforma | v0.76.0 | `PLATFORM_VERSION`" in versions, "VERSIONS alterou a plataforma")
    require("| Mapa | v0.74.0 | `MAP_VERSION`" in versions, "VERSIONS não atualizou o mapa")
    require("## [map-0.74.0]" in changelog_map, "CHANGELOG_MAP sem release map-0.74.0")

    unexpected = sorted(changed_paths() - ALLOWED_EXACT)
    require(not unexpected, "Arquivos fora da trilha do mapa foram alterados: " + ", ".join(unexpected))

    if shutil.which("node"):
        run(["node", "--check", "static/js/map-link-monitoring-v074.js"])
        run(["node", "--check", "static/js/map-v074-ui.js"])
        run(["node", "--check", "static/js/map-master-suite.js"])

    run([sys.executable, "-m", "py_compile", "apps/snmp_monitoring/api.py", "apps/snmp_monitoring/tasks.py", "apps/network_map/api/views.py", "apps/snmp_monitoring/management/commands/cleanup_invalid_snmp_profiles.py"])

    print("OK: validação estrutural map-v0.74.0 v2 concluída.")
    print("OK: PLATFORM_VERSION 0.76.0 preservada e diff restrito à trilha do mapa.")
    print("ATENÇÃO: a homologação no navegador/Network continua obrigatória.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FALHA map-v0.74.0: {exc}", file=sys.stderr)
        raise SystemExit(1)
