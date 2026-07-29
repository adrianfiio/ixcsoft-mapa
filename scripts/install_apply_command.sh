#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="${IXCSOFT_PROJECT_DIR:-/opt/ixcsoft-mapa}"
SOURCE="$PROJECT_DIR/scripts/apply.sh"
TARGET="/usr/local/bin/apply"

if [[ ! -f "$SOURCE" ]]; then
    printf 'Arquivo não encontrado: %s\n' "$SOURCE" >&2
    exit 1
fi

chmod +x "$SOURCE"
sudo ln -sfn "$SOURCE" "$TARGET"

printf 'Comando instalado com sucesso: %s -> %s\n' "$TARGET" "$SOURCE"
printf 'Agora execute: apply\n'
