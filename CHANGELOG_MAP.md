# Changelog — Mapa

## [map-0.75.0] - 2026-08-02

Workspace estrutural de Torre/Rack com Canvas 2D direto.

### Adicionado

- toolbar do Canvas com D.I.O, PTO, AP, PTP, Switch, Router e ONU/ONT;
- drawers laterais para inventário, fibras, matriz e importação YAML;
- painel de propriedades do equipamento com atalhos para edição, ficha e SNMP;
- estrutura visual da torre e estado vazio guiado.

### Corrigido

- primeiro clique em Tela cheia abrindo conteúdo fora da aplicação;
- fullscreen de Rack/Torre e Fusões agora exclusivamente por CSS;
- toolbar/slider de Fusões compactos e sem barras aninhadas visíveis;
- importação YAML com validação de IP, limite de interfaces, conflito de nome e erros transacionais legíveis;
- tipos Router, AP, PTP, ONU/ONT e PTO aceitos de forma consistente em Rack/Torre.

### Versionamento

- `PLATFORM_VERSION` preservada em `0.77.0`;
- `MAP_VERSION` atualizada para `0.75.0`;
- nenhuma migration.


## [map-0.74.1] - 2026-08-02

Polimento visual final do Rack/Torre, Canvas 2D, menu lateral, ações de desenho e ficha técnica.

### Corrigido

- barra única com ícones na janela Rack/Torre;
- Canvas 2D com auto-fit, zoom `+`/`−`, botão Ajustar e `Ctrl + scroll`;
- remoção de barras desnecessárias no Canvas e menu lateral;
- mensagem do editor não aparece perdida no menu recolhido;
- apenas um cancelamento durante o desenho de cabo;
- ficha técnica sem texto vertical, metadados espremidos ou scroll dentro de scroll;
- estado de implantação integrado aos cards da ficha.

### Versionamento

- `PLATFORM_VERSION` preservada em `0.77.0`;
- `MAP_VERSION` atualizada para `0.74.1`;
- nenhuma migration.


## [map-0.74.0] - 2026-08-02

Estabilização estrutural do editor cartográfico, Rack/Torre, Canvas, ficha
técnica e monitoramento visual. Esta é uma release exclusiva da trilha do mapa;
a plataforma permanece em `platform-v0.76.0`.

### Corrigido

- removido o ciclo de renderização que gerava chamadas repetidas para
  `equipment/` e `container-layout-v3/`;
- uma única carga simultânea por abertura de Rack/Torre;
- observer do container deixa de observar filhos renderizados;
- snapshot visual deixa de consultar a cada 15 segundos e passa a cinco minutos
  quando existe monitoramento elegível;
- requisições antigas são canceladas ao trocar o projeto;
- DIO, PTO, servidor e OLT ficam fora do SNMP universal;
- servidores existentes permanecem no banco, mas não aparecem no mapa;
- fusões são centralizadas e limitadas à viewport;
- ficha técnica responsiva com impressão/Salvar como PDF;
- lateral sem barras visíveis, alternância de nomes e hover por ícone;
- menu de botão direito com ações e ícones;
- toolbar e Canvas compactados.

### Regra definitiva do SNMP universal

O equipamento precisa estar ativo, em tipo permitido, com
`provisioning_mode=snmp` e perfil ativo. Tipos: switch, roteador, firewall,
access point, PTP, ONU/ONT e outro ativo. OLT usa integração específica.

### Versionamento

- `PLATFORM_VERSION` preservada em `0.76.0`;
- `MAP_VERSION` atualizada de `0.73.1` para `0.74.0`;
- tag futura: `map-v0.74.0`;
- nenhuma migration.


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
