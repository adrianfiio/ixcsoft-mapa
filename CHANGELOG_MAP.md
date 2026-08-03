# Changelog — Mapa

## [map-0.75.6] - 2026-08-03

### Adicionado

- cards técnicos dos cabos conectados diretamente no Canvas 2D de Rack/Torre;
- fibras individuais com as cores reais do catálogo óptico;
- terminação de fibra na porta traseira do DIO sem abrir painel legado;
- paginação de DIOs em bandejas visuais de 24 portas;
- cabos e fibras incluídos na exportação PNG/PDF do Canvas.

### Alterado

- cabos de entrada ficam à esquerda e cabos de saída à direita;
- botão **Fibras** apenas destaca cabos e DIOs no Canvas unificado;
- Rack, Torre, CTO e CEO abrem diretamente seus editores técnicos;
- organização e auto-fit passam a considerar também os cards de cabos;
- linhas e pontos de controle usam coordenadas lógicas corretas sob zoom.

### Corrigido

- perda/alinhamento incorreto do traçado após zoom, organização ou inclusão de equipamento;
- coluna interminável de portas em DIOs de alta capacidade;
- criação de DIO maior que 24 portas em Torre;
- exportação que ignorava os cabos ópticos conectados.

### Versionamento

- `PLATFORM_VERSION` preservada em `0.81.3`;
- `MAP_VERSION` atualizada para `0.75.6`;
- nenhuma migration.

## [map-0.75.5] - 2026-08-02

### Adicionado

- ícones SVG técnicos para CTO, PTO, CDO, CEO, Rack, Torre, Poste, reserva e POP/CPD;
- ações modernas de editar e excluir em notas e equipamentos do Canvas;
- abertura direta do editor óptico pelo botão Fibras.

### Alterado

- editor óptico posiciona cabos e fibras à esquerda e DIOs à direita;
- conectores e ligações continuam visíveis sobre os cards sem bloquear o movimento normal;
- ícones configurados pelo Django são reaplicados após cada renderização do mapa.

### Corrigido

- movimento do Canvas com o botão central quando a área não possui rolagem nativa;
- movimentação de equipamentos e notas respeitando o nível atual de zoom;
- linhas capturando o mouse fora do modo de edição;
- botão de fechar do editor óptico desalinhado.

### Versionamento

- `PLATFORM_VERSION` preservada em `0.80.0`;
- `MAP_VERSION` atualizada para `0.75.5`;
- nenhuma migration.

## [map-0.75.4] - 2026-08-02

### Adicionado

- visão frontal e traseira das portas do DIO no Canvas 2D;
- exclusão de ligação pela porta ocupada ou pelo menu de contexto da linha;
- edição e exclusão modernas de notas, com menu contextual no fundo do Canvas;
- identificação das fibras já ocupadas no seletor de terminações.

### Alterado

- lista de equipamentos da estrutura funciona como acordeão e respeita espaçamento entre detalhes;
- exportação PNG/PDF usa SVG próprio, sem capturar tiles ou conteúdo externo;
- botão de tela cheia removido do editor técnico.

### Corrigido

- conflito HTTP 409 ao clicar novamente em porta já ligada;
- dois menus simultâneos ao clicar com o botão direito no mapa;
- erro de segurança `Tainted canvases may not be exported`.

### Versionamento

- `PLATFORM_VERSION` preservada em `0.80.0`;
- `MAP_VERSION` atualizada para `0.75.4`;
- nenhuma migration.

## [map-0.75.3] - 2026-08-02

### Adicionado

- lápis compacto no card para abrir propriedades, sem painel automático ao clicar;
- movimentação do Canvas com o botão central do mouse;
- entrada DROP reposicionável e notas técnicas por clique direito;
- exportação do Canvas para PNG e impressão/PDF;
- tela cheia nativa do navegador com fallback CSS.

### Alterado

- conectores seguem o lado esquerdo/direito de cada porta;
- ligar portas e editar linhas são modos ativáveis e concluíveis;
- estrutura mostra lista compacta de equipamentos;
- matriz virou relatório de ligações, sem criar conexões por formulário.

### Corrigido

- ficha técnica antiga/incompleta é recriada antes de conectar seus eventos;
- clique comum no equipamento agora apenas seleciona o card.

### Versionamento

- `PLATFORM_VERSION` preservada em `0.79.1`;
- `MAP_VERSION` atualizada para `0.75.3`;
- nenhuma migration.

## [map-0.75.2] - 2026-08-02

Canvas técnico e criação contextual de ativos da torre.

### Adicionado

- seleção opcional de um cabo DROP conectado à torre ao criar ONU/ONT;
- representação do DROP externo até a porta PON da ONU no Canvas 2D.

### Alterado

- versão do MAPA movida para o rodapé do menu lateral, pequena e discreta;
- formulário de criação agora mostra somente campos compatíveis com o tipo;
- linhas e conectores ficam sobre os widgets e junto ao nome das portas;
- edição de linhas possui a ação explícita **Concluir e salvar**;
- formulários técnicos abrem com transição em fade.

### Corrigido

- novos enlaces não criam mais pontos de controle fora do Canvas;
- ligações originadas em cabos externos passam a ser retornadas e desenhadas.

### Versionamento

- `PLATFORM_VERSION` preservada em `0.79.0`;
- `MAP_VERSION` atualizada para `0.75.2`;
- nenhuma migration.

## [map-0.75.1] - 2026-08-02

Estabilização e polimento do editor técnico de Torre/Rack.

### Adicionado

- versão do MAPA visível na barra inferior;
- ações separadas para ligar portas e editar o trajeto das linhas;
- pontos de controle persistentes nas ligações internas.

### Corrigido

- workspace reposicionado corretamente em todas as aberturas;
- linhas ancoradas no centro do conector real da porta;
- formulários de equipamento orientados pelo tipo do ativo;
- ficha técnica responsiva, sem textos escapando dos cards;
- botões unificados com visual moderno e realce no hover.

### Versionamento

- `PLATFORM_VERSION` preservada em `0.78.0`;
- `MAP_VERSION` atualizada para `0.75.1`;
- nenhuma migration.

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
