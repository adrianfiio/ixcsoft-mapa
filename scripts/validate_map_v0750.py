#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "f57c6dadf67baa847e417d2a965f383ba5b2a750"

ALLOWED = {
    "templates/map.html",
    "static/js/map-v0750-tower-workspace.js",
    "static/css/map-v0750-tower-workspace.css",
    "static/js/container-device-type.js",
    "static/js/map-fusion-polish.js",
    "static/js/map-master-suite.js",
    "static/js/map-optical-editor-v3.js",
    "apps/network_map/api/device_type_views.py",
    "tests/test_map_v0750_static.py",
    "scripts/validate_map_v0750.py",
    "config/settings.py",
    "docker-compose.yml",
    "README.md",
    "CHANGELOG_MAP.md",
    "VERSIONS.md",
    "docs/releases/map/map-v0.75.0.md",
}


def read(path):
    target = ROOT / path
    if not target.exists():
        raise AssertionError(f"Arquivo ausente: {path}")
    return target.read_text(encoding="utf-8")


def run(cmd, check=True):
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if check and result.returncode:
        raise AssertionError(f"Comando falhou: {' '.join(cmd)}\n{result.stdout}\n{result.stderr}")
    return result


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def changed_paths():
    result = run(["git", "status", "--porcelain", "--untracked-files=all"], check=False)
    if result.returncode:
        return set()
    paths = set()
    for line in result.stdout.splitlines():
        raw = line[3:].strip()
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        paths.add(raw.replace("\\", "/"))
    return paths


def main():
    if (ROOT / ".git").exists():
        ancestry = run(["git", "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD"], check=False)
        require(ancestry.returncode == 0, f"HEAD não descende da base validada {BASE_COMMIT}")

    template = read("templates/map.html")
    js = read("static/js/map-v0750-tower-workspace.js")
    css = read("static/css/map-v0750-tower-workspace.css")
    backend = read("apps/network_map/api/device_type_views.py")
    settings = read("config/settings.py")
    compose = read("docker-compose.yml")
    readme = read("README.md")
    versions = read("VERSIONS.md")
    changelog = read("CHANGELOG_MAP.md")

    require("map-v0750-tower-workspace.css' %}?v={{ map_version }}" in template, "CSS v0.75.0 não usa map_version")
    require("map-v0750-tower-workspace.js' %}?v={{ map_version }}" in template, "JS v0.75.0 não usa map_version")
    require("activateCanvas" in js and "Canvas 2D da estrutura" in js, "Abertura direta no Canvas ausente")
    loaded_runtimes = [
        js,
        read("static/js/map-fusion-polish.js"),
        read("static/js/map-master-suite.js"),
        read("static/js/map-optical-editor-v3.js"),
    ]
    for runtime in loaded_runtimes:
        require(not any(token in runtime for token in ("requestFullscreen", "exitFullscreen", "document.fullscreenElement", "fullscreenchange")), "Fullscreen ainda depende da API nativa")
    require("map-v0750-css-fullscreen" in js, "Classe CSS de fullscreen ausente")
    require("MutationObserver" not in js, "Runtime v0.75.0 observa a própria renderização")
    extension = read("static/js/container-device-type.js")
    require("new MutationObserver" not in extension, "Complemento YAML voltou a observar o diálogo")
    require("event.detail?.data" in extension, "Complemento YAML não reutiliza o payload carregado")
    require('data-quick-add="dio"' in js and 'data-quick-add="pto"' in js, "DIO/PTO não estão na toolbar")
    for equipment_type in ("access_point", "ptp", "switch", "router", "onu"):
        require(f'data-quick-add="{equipment_type}"' in js, f"Tipo ativo ausente: {equipment_type}")
    require("openInspector" in js and "data-inspector-snmp" in js, "Painel de propriedades/SNMP ausente")
    require("fusion-v0750" in css and "scrollbar-width: none" in css, "Compactação de fusões ausente")
    require("MAX_IMPORTED_INTERFACES = 256" in backend, "Limite seguro do YAML ausente")
    require("except IntegrityError" in backend and "status=409" in backend, "Importação YAML ainda pode gerar 500 por conflito")
    require('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.0")' in settings, "MAP_VERSION divergente")
    require('PLATFORM_VERSION = os.getenv("PLATFORM_VERSION", os.getenv("APP_VERSION", "0.77.0"))' in settings, "PLATFORM_VERSION alterada")
    require('MAP_VERSION: ${MAP_VERSION:-0.75.0}' in compose, "MAP_VERSION do Compose divergente")
    require('PLATFORM_VERSION: ${PLATFORM_VERSION:-0.77.0}' in compose, "PLATFORM_VERSION do Compose alterada")
    require("| Mapa | v0.75.0 |" in readme, "README sem map-v0.75.0")
    require("| Mapa | v0.75.0 | `MAP_VERSION`" in versions, "VERSIONS sem map-v0.75.0")
    require("## [map-0.75.0]" in changelog, "CHANGELOG_MAP sem map-0.75.0")

    unexpected = sorted(changed_paths() - ALLOWED)
    require(not unexpected, "Arquivos fora da trilha do mapa: " + ", ".join(unexpected))

    if shutil.which("node"):
        run(["node", "--check", "static/js/map-v0750-tower-workspace.js"])
    run([sys.executable, "-m", "py_compile", "apps/network_map/api/device_type_views.py", "tests/test_map_v0750_static.py"])

    print("OK: validação estrutural map-v0.75.0 concluída.")
    print("OK: Canvas 2D direto, fullscreen CSS, fusões compactas e YAML protegido.")
    print("OK: PLATFORM_VERSION 0.77.0 preservada e alterações restritas ao mapa.")
    print("ATENÇÃO: homologação visual e importação YAML real continuam obrigatórias no servidor.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FALHA map-v0.75.0: {exc}", file=sys.stderr)
        raise SystemExit(1)
