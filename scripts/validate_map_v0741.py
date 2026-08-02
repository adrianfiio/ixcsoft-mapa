#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "66180d30988527321813764e6a04a783e1797459"

ALLOWED_EXACT = {
    "templates/map.html",
    "static/js/map-v0741-ui.js",
    "static/css/map-v0741.css",
    "tests/test_map_v0741_static.py",
    "scripts/validate_map_v0741.py",
    "config/settings.py",
    "docker-compose.yml",
    "README.md",
    "CHANGELOG_MAP.md",
    "VERSIONS.md",
    "docs/releases/map/map-v0.74.1.md",
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
    result = run(["git", "status", "--porcelain", "--untracked-files=all"], check=False)
    if result.returncode:
        return set()
    paths = set()
    for line in result.stdout.splitlines():
        raw = line[3:].strip()
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        normalized = raw.replace("\\", "/")
        if "/__pycache__/" in f"/{normalized}" or normalized.endswith(".pyc"):
            continue
        paths.add(normalized)
    return paths


def main() -> int:
    head = run(["git", "rev-parse", "HEAD"], check=False).stdout.strip()
    if head:
        ancestry = run(["git", "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD"], check=False)
        require(ancestry.returncode == 0, f"HEAD ({head}) não descende da base validada {BASE_COMMIT}")

    template = read("templates/map.html")
    ui = read("static/js/map-v0741-ui.js")
    css = read("static/css/map-v0741.css")
    settings = read("config/settings.py")
    compose = read("docker-compose.yml")
    readme = read("README.md")
    versions = read("VERSIONS.md")
    changelog = read("CHANGELOG_MAP.md")
    release = read("docs/releases/map/map-v0.74.1.md")

    require("map-v0741.css' %}?v={{ map_version }}" in template, "CSS v0.74.1 não usa map_version")
    require("map-v0741-ui.js' %}?v={{ map_version }}" in template, "JS v0.74.1 não usa map_version")

    require("master-container-commandbar-v0741" in ui, "Barra única de Rack/Torre ausente")
    require("v0741-button-icon" in ui and "decorateContainer" in ui, "Ícones da toolbar ausentes")
    require("data-canvas-zoom-fit" in ui, "Botão Ajustar do Canvas ausente")
    require("event.ctrlKey" in ui, "Ctrl + scroll do Canvas ausente")
    require("fitCanvas" in ui and "applyCanvasView" in ui, "Auto-fit/zoom do Canvas ausente")
    require('const contextual = Boolean(drawingBar && !drawingBar.hidden)' in ui, "Coordenação do cancelar contextual ausente")
    require("has-nested-value-v0741" in ui and "nested-definition-v0741" in ui, "Normalização da ficha técnica ausente")
    require("v0741-lifecycle-card" in ui, "Estado de implantação não foi integrado aos cards")

    require("#map-sidebar.v072-collapsed #editor-message" in css, "Mensagem perdida no menu recolhido não foi ocultada")
    require("overflow-x: hidden" in css and "scrollbar-width: none" in css, "Barras do menu/ficha não foram tratadas")
    require(".master-canvas-scroll" in css and "overflow: hidden !important" in css, "Canvas continua permitindo barras")
    require("#drawing-bar:not([hidden])" in css and "[data-v0722-cancel]" in css, "Cancelamento duplicado não foi tratado")
    require("word-break: break-word" in css and "nested-definition-v0741" in css, "Metadados longos da ficha continuam espremidos")

    require('PLATFORM_VERSION = os.getenv("PLATFORM_VERSION", os.getenv("APP_VERSION", "0.77.0"))' in settings, "PLATFORM_VERSION foi alterada")
    require('MAP_VERSION = os.getenv("MAP_VERSION", "0.74.1")' in settings, "MAP_VERSION não está em 0.74.1")
    require('PLATFORM_VERSION: ${PLATFORM_VERSION:-0.77.0}' in compose, "Compose alterou a plataforma")
    require('MAP_VERSION: ${MAP_VERSION:-0.74.1}' in compose, "Compose não está em map 0.74.1")
    require("| Plataforma | v0.77.0 |" in readme and "| Mapa | v0.74.1 |" in readme, "README com versões divergentes")
    require("| Plataforma | v0.77.0 | `PLATFORM_VERSION`" in versions, "VERSIONS alterou a plataforma")
    require("| Mapa | v0.74.1 | `MAP_VERSION`" in versions, "VERSIONS não atualizou o mapa")
    require("## [map-0.74.1]" in changelog, "CHANGELOG_MAP sem map-0.74.1")
    require("map-v0.74.1" in release, "Documento da release ausente ou incorreto")

    unexpected = sorted(changed_paths() - ALLOWED_EXACT)
    require(not unexpected, "Arquivos fora da trilha do mapa foram alterados: " + ", ".join(unexpected))

    if shutil.which("node"):
        run(["node", "--check", "static/js/map-v0741-ui.js"])
    run([sys.executable, "-m", "py_compile", "scripts/validate_map_v0741.py", "tests/test_map_v0741_static.py"])

    print("OK: validação estrutural map-v0.74.1 concluída.")
    print("OK: PLATFORM_VERSION 0.77.0 preservada e alterações restritas à trilha do mapa.")
    print("ATENÇÃO: homologação visual e Network continuam obrigatórias antes da tag.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FALHA map-v0.74.1: {exc}", file=sys.stderr)
        raise SystemExit(1)
