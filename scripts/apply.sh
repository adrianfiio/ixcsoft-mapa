#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="${IXCSOFT_PROJECT_DIR:-/opt/ixcsoft-mapa}"
BRANCH="${IXCSOFT_DEPLOY_BRANCH:-main}"
HEALTH_TIMEOUT="${IXCSOFT_HEALTH_TIMEOUT:-180}"
STARTED_AT="$(date +%s)"
CURRENT_STEP="inicialização"
BEFORE_COMMIT=""
AFTER_COMMIT=""
DEPLOY_VERSION=""
APP_VERSION_VALUE=""

if [[ -t 1 ]]; then
    GREEN=$'\033[0;32m'
    RED=$'\033[0;31m'
    YELLOW=$'\033[0;33m'
    CYAN=$'\033[0;36m'
    RESET=$'\033[0m'
else
    GREEN=""
    RED=""
    YELLOW=""
    CYAN=""
    RESET=""
fi

info() {
    printf '%s→%s %s\n' "$CYAN" "$RESET" "$1"
}

success() {
    printf '%s✓%s %s\n' "$GREEN" "$RESET" "$1"
}

warning() {
    printf '%s!%s %s\n' "$YELLOW" "$RESET" "$1"
}

fail() {
    printf '%s✗%s %s\n' "$RED" "$RESET" "$1" >&2
}

show_report() {
    local result="$1"
    local finished_at duration version
    finished_at="$(date +%s)"
    duration="$((finished_at - STARTED_AT))"
    version="${DEPLOY_VERSION:-$(git -C "$PROJECT_DIR" describe --tags --always 2>/dev/null || printf 'desconhecida')}"

    printf '\n'
    printf '========================================\n'
    printf ' Relatório IXCSoft Mapa\n'
    printf '========================================\n'
    printf ' Resultado:       %s\n' "$result"
    printf ' Projeto:         %s\n' "$PROJECT_DIR"
    printf ' Branch:          %s\n' "$BRANCH"
    printf ' Versão:          %s\n' "$version"
    printf ' Commit anterior: %s\n' "${BEFORE_COMMIT:-não verificado}"
    printf ' Commit atual:    %s\n' "${AFTER_COMMIT:-não verificado}"
    printf ' Duração:         %ss\n' "$duration"
    printf ' Data:            %s\n' "$(date '+%d/%m/%Y %H:%M:%S %Z')"
    printf '========================================\n'
}

abort() {
    fail "$1"
    show_report "FALHA"
    exit 1
}

on_error() {
    local exit_code="$?"
    fail "Falha durante: $CURRENT_STEP"
    if [[ -d "$PROJECT_DIR" ]] && command -v docker >/dev/null 2>&1; then
        warning "Últimas linhas dos serviços:"
        docker compose --project-directory "$PROJECT_DIR" \
            -f "$PROJECT_DIR/docker-compose.yml" logs --tail=40 web worker beat \
            2>/dev/null || true
    fi
    show_report "FALHA (código $exit_code)"
    exit "$exit_code"
}

trap on_error ERR

printf '\nIXCSoft Mapa — atualização automática\n\n'

CURRENT_STEP="verificação do ambiente"
[[ $EUID -ne 0 ]] || {
    warning "Executando como root. Use este modo somente no servidor administrado diretamente como root."
}
[[ -d "$PROJECT_DIR/.git" ]] || {
    abort "Repositório não encontrado em $PROJECT_DIR"
}
command -v git >/dev/null 2>&1 || {
    abort "Git não está instalado."
}
command -v docker >/dev/null 2>&1 || {
    abort "Docker não está instalado."
}
docker compose version >/dev/null
success "Ambiente verificado"

CURRENT_STEP="verificação do repositório"
cd "$PROJECT_DIR"
if [[ -n "$(git status --porcelain)" ]]; then
    fail "Existem alterações locais. A atualização foi cancelada para não sobrescrever arquivos."
    git status --short
    show_report "FALHA"
    exit 1
fi
BEFORE_COMMIT="$(git rev-parse --short HEAD)"
info "Buscando atualizações do GitHub"
git fetch --prune origin
git switch "$BRANCH"
git pull --ff-only origin "$BRANCH"
AFTER_COMMIT="$(git rev-parse --short HEAD)"
DEPLOY_VERSION="$(git describe --tags --always --match 'v*')"
APP_VERSION_VALUE="${DEPLOY_VERSION#v}"
export APP_VERSION="$APP_VERSION_VALUE"
if [[ "$BEFORE_COMMIT" == "$AFTER_COMMIT" ]]; then
    success "Código já estava atualizado ($AFTER_COMMIT)"
else
    success "Código atualizado: $BEFORE_COMMIT → $AFTER_COMMIT"
fi

CURRENT_STEP="validação da configuração"
info "Validando configuração do Docker Compose"
docker compose config --quiet
success "Configuração válida"

CURRENT_STEP="construção e inicialização dos serviços"
info "Construindo e iniciando web, worker e beat"
docker compose up --build -d
success "Serviços iniciados"

CURRENT_STEP="health check da aplicação"
info "Aguardando a aplicação ficar saudável (limite: ${HEALTH_TIMEOUT}s)"
deadline="$(( $(date +%s) + HEALTH_TIMEOUT ))"
web_container="$(docker compose ps -q web)"
[[ -n "$web_container" ]]

while true; do
    health_status="$(
        docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
            "$web_container"
    )"

    if [[ "$health_status" == "healthy" ]]; then
        break
    fi

    if [[ "$health_status" == "unhealthy" || "$(date +%s)" -ge "$deadline" ]]; then
        fail "Aplicação não ficou saudável. Estado atual: $health_status"
        false
    fi

    printf '.'
    sleep 5
done
printf '\n'
success "Aplicação saudável"

CURRENT_STEP="verificação dos arquivos da interface"
info "Verificando o CSS da interface"
curl --fail --silent --show-error \
    -H "Host: localhost" \
    "http://127.0.0.1:8000/assets/static/css/app.css?v=$APP_VERSION_VALUE" \
    >/dev/null
curl --fail --silent --show-error \
    -H "Host: localhost" \
    "http://127.0.0.1:8000/assets/static/admin/css/base.css?v=$APP_VERSION_VALUE" \
    >/dev/null
curl --fail --silent --show-error \
    -H "Host: localhost" \
    "http://127.0.0.1:8000/assets/static/img/afservice-logo.png?v=$APP_VERSION_VALUE" \
    >/dev/null
if curl --fail --silent \
    -H "Host: localhost" \
    "http://127.0.0.1:8000/assets/static/img/afservice-map-favicon.png?v=$APP_VERSION_VALUE" \
    >/dev/null; then
    success "CSS da aplicação, Django Admin, logotipo e favicon disponíveis"
else
    warning "Favicon ainda não encontrado em static/img/afservice-map-favicon.png"
    success "CSS da aplicação, Django Admin e logotipo disponíveis"
fi

CURRENT_STEP="verificação final dos serviços"
for service in web worker beat; do
    container_id="$(docker compose ps -q "$service")"
    [[ -n "$container_id" ]]
    container_state="$(docker inspect --format '{{.State.Status}}' "$container_id")"
    [[ "$container_state" == "running" ]] || {
        fail "Serviço $service está em estado $container_state"
        false
    }
    success "Serviço $service em execução"
done

show_report "SUCESSO"
