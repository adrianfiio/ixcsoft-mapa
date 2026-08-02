# Versões

Este repositório mantém **um único** Django/Docker/banco, mas duas
trilhas de versão independentes — plataforma e mapa nunca mais
compartilham o mesmo número de release.

| Componente | Versão vigente | Variável de ambiente | Changelog | Tags |
|---|---:|---|---|---|
| Plataforma | v0.80.0 | `PLATFORM_VERSION` | [CHANGELOG_PLATFORM.md](CHANGELOG_PLATFORM.md) | `platform-vX.Y.Z` |
| Mapa | v0.75.3 | `MAP_VERSION` | [CHANGELOG_MAP.md](CHANGELOG_MAP.md) | `map-vX.Y.Z` |

## O que pertence a cada trilha

**Plataforma** — Dashboard, Visão geral, Financeiro, Superadmin,
empresas, usuários, integrações administrativas, templates e páginas
que não pertencem ao mapa.

**Mapa** — editor cartográfico, Rack/Torre, Canvas 2D, fusões, popups
do mapa, ferramentas cartográficas, monitoramento visual, SNMP,
enlaces, fichas técnicas abertas pelo mapa.

## Regras definitivas

- Uma entrega de plataforma nunca altera `CHANGELOG_MAP.md`, e vice-versa.
- Nenhum commit mistura os dois componentes.
- Nenhuma branch mistura os dois componentes — `agent/platform-<assunto>`
  ou `agent/map-<assunto>`, nunca as duas coisas na mesma branch.
- Nenhuma tag mistura os dois componentes — `platform-vX.Y.Z` ou
  `map-vX.Y.Z`. Nunca mais uma tag `vX.Y.Z` genérica.
- Commits de release seguem `release platform-vX.Y.Z <descrição>` ou
  `release map-vX.Y.Z <descrição>`.
- `APP_VERSION` continua existindo só como alias de `PLATFORM_VERSION`
  (compatibilidade com código legado que ainda lê essa variável) — não
  é uma terceira versão.
- O deploy continua sendo um único `docker-compose.yml`, um único banco,
  uma única aplicação Django. A separação é só de versão/branch/
  changelog/release/arquivos, não de infraestrutura.

## Como saber se um arquivo é "plataforma" ou "mapa"

Referência rápida (não exaustiva):

| Arquivo/pasta | Trilha |
|---|---|
| `apps/billing/**` | Plataforma |
| `apps/core/views.py`, `apps/core/platform_overview.py`, `apps/core/forms.py` | Plataforma |
| `templates/billing/**`, `templates/dashboard*.html`, `templates/platform_*.html`, `templates/base.html` | Plataforma |
| `templates/map.html` | Mapa |
| `static/js/map-*`, `static/css/map-*` | Mapa |
| `apps/network_map/**` (parte do editor do mapa) | Mapa |
| `apps/snmp_monitoring/**` | Mapa |
| `apps/access/**`, `apps/ixc_integration/**`, `apps/olt_integration/**`, `apps/optical/**` | Depende do ponto de uso — dado usado tanto por telas de plataforma quanto pelo mapa; a mudança em si é que define a trilha (se mexeu numa tela/endpoint do mapa, é mapa; se mexeu num cadastro/relatório administrativo, é plataforma) |

Na dúvida, perguntar antes de commitar em vez de misturar numa branch
só.
