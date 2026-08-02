# Changelog — Plataforma

Cobre Dashboard, Visão geral, Financeiro, Superadmin, empresas,
usuários e integrações administrativas — tudo que **não** pertence ao
mapa. Tags `platform-vX.Y.Z`. Releases em `docs/releases/platform/`.

Para o mapa (editor cartográfico, Rack/Torre, Canvas 2D, fusões, popups,
SNMP, enlaces), ver [CHANGELOG_MAP.md](CHANGELOG_MAP.md).

Histórico anterior a esta separação (quando plataforma e mapa ainda
compartilhavam uma única numeração `vX.Y.Z` global) está em
[CHANGELOG.md](CHANGELOG.md) — as entradas que correspondem ao que hoje
é a trilha de plataforma são `[0.76.0]`, `[0.75.1]`, `[0.75.0]` e
`[0.74.0]` (módulo financeiro, ACL, painel Superadmin, correção de
arquitetura do financeiro — construídos nesta ordem, do zero, nesta
sessão).

## [platform-0.76.0] - 2026-08-02

Ponto de partida desta trilha separada. Corresponde exatamente ao que
já estava publicado como `v0.76.0` no changelog global (commit
`cf1e118`) — ver a entrada completa em
[CHANGELOG.md#0760---2026-08-02](CHANGELOG.md) e
[docs/releases/v0.76.0.md](docs/releases/v0.76.0.md) pro detalhe
técnico completo. Resumo: correção de arquitetura do financeiro (quem é
cobrado é a empresa cliente — Provedor ISP ou Projetista —, não os
assinantes de internet de cada provedor), painel Superadmin exclusivo
pra cadastro/gestão de empresa e cobrança, liberação de confiança
(+2 dias de acesso, 1x por mês), bloqueio de acesso por assinatura com
fail-safe (empresa sem assinatura cadastrada nunca é bloqueada).

### Infraestrutura de versionamento (nesta mesma trilha)

- `PLATFORM_VERSION`/`MAP_VERSION` separados em `config/settings.py` e
  `docker-compose.yml` — `APP_VERSION` continua existindo só como alias
  de `PLATFORM_VERSION`, pra compatibilidade com código legado.
- Templates passam a ter `platform_version`/`map_version` disponíveis
  (além do `app_version` já existente, agora alias).
- `README.md` — "Versão atual" virou uma tabela com as duas trilhas.
- `docs/releases/platform/` e `docs/releases/map/` criados pra separar
  os releases detalhados de cada trilha daqui pra frente.
