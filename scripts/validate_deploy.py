from pathlib import Path
import py_compile
import sys

ROOT = Path(__file__).resolve().parent.parent
required = [
    "Dockerfile",
    "docker-compose.yml",
    ".dockerignore",
    "docker/entrypoint.sh",
    "deploy/nginx/default.conf",
    "docs/DEPLOY_EASYPANEL.md",
    "docs/releases/v0.6.0.md",
]

missing = [name for name in required if not (ROOT / name).exists()]
if missing:
    print("Arquivos ausentes:", ", ".join(missing))
    sys.exit(1)

for path in ROOT.rglob("*.py"):
    if "__pycache__" not in path.parts:
        py_compile.compile(str(path), doraise=True)

print("Validação estrutural e sintática concluída.")
