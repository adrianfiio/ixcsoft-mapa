# Changelog — Mapa

Cobre o editor cartográfico, Rack/Torre, Canvas 2D, fusões, popups do
mapa, ferramentas cartográficas, monitoramento visual, SNMP, enlaces e
fichas técnicas abertas pelo mapa. Tags `map-vX.Y.Z`. Releases em
`docs/releases/map/`.

Para a plataforma (Dashboard, Financeiro, Superadmin), ver
[CHANGELOG_PLATFORM.md](CHANGELOG_PLATFORM.md).

Histórico anterior a esta separação (quando plataforma e mapa ainda
compartilhavam uma única numeração `vX.Y.Z` global) está em
[CHANGELOG.md](CHANGELOG.md) — as entradas que correspondem ao que hoje
é a trilha do mapa vão de `[0.73.1]` (hotfix estrutural do runtime do
mapa, a mais recente publicada) até `[0.67.0]` e anteriores (mapa
óptico, editor de projeto, KMZ/KML, Master Suite, monitoramento SNMP
por equipamento).

## [map-0.73.1] - 2026-08-02 (ponto de partida desta trilha separada)

Corresponde exatamente ao que já estava publicado como `v0.73.1` no
changelog global — ver a entrada completa em
[CHANGELOG.md#0731---2026-08-02](CHANGELOG.md) e
[docs/releases/v0.73.1.md](docs/releases/v0.73.1.md). Resumo: hotfix
estrutural do runtime de monitoramento do mapa (remove o laço de
reconstrução de popups por `MutationObserver`), restaura botões de ação
(Editar, Fusões, Equipamentos, Rota do cabo, Monitorar enlace) e o
cancelamento de ferramentas com `Esc`.

### Em andamento, ainda não lançado nesta trilha

Um pacote de reestruturação maior (SNMP opt-in por equipamento, runtime
sem polling ocioso, Rack/Torre/Fusões/Canvas compactados) está em
preparação desde a v0.73.1, mas **os dois pacotes recebidos até agora
falharam na validação automática** (`apply_map_v074.py --dry-run`) por
divergência de marcador em `apps/network_map/api/views.py` — o campo
`type_label` de `_container_equipment_payload` não é mais uma linha
simples (é uma expressão condicional de várias linhas, do tratamento
especial de "ONU / ONT"), e os pacotes recebidos ainda assumem a forma
antiga. Nenhum dos dois foi aplicado; ver PR #52 (branch
`agent/v0-74-snmp-map-rework`) pro estado exato do que já foi tentado.
