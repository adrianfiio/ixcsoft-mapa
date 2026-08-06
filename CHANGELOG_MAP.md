## [0.75.50] - 2026-08-05

## MAP v0.75.52 — Rack navegável, uplinks funcionais e DIO pareado

- Switches de 8, 12 e 16 portas usam uma única linha na largura útil do Rack;
- clique esquerdo segurado movimenta o Canvas em qualquer nível de zoom;
- slots de uplink aparecem apenas no topo e aceitam RJ45, SFP, SFP+, XFP e QSFP+;
- equipamentos podem trocar posições em U ao serem arrastados um sobre o outro;
- cada porta do DIO mantém frente e traseira pareadas;
- sem migration e sem alteração na versão da Plataforma.

## MAP v0.75.51 — Switch de 16 portas, YAML tipado e cores por velocidade

- adiciona 16 portas à criação de Switches e mantém as 16 numa única linha;
- permite editar nome, RJ45, SFP, SFP+, XFP, QSFP+ e velocidade por porta;
- preserva nomes do YAML e torna a reimportação idempotente por chave estável;
- colore porta e conexão em verde/azul/roxo/laranja/vermelho para 1/10/25/40/100 Gbps;
- preserva a estabilidade de pan, zoom, OLT e observers da MAP v0.75.50;
- não requer migration.

### Estabilização crítica do Rack
- O ciclo MutationObserver → enhance → fetch → render foi interrompido.
- Consultas de uplink passam a usar cache, chamada compartilhada e cooldown após falha.
- Alterações geradas pelo próprio painel de uplinks não disparam nova melhoria.
- O fluxo físico deixa de chamar refresh recursivamente.
- Falhas temporárias da API de uplink não derrubam a OLT nem o Rack.
- Nenhuma migration foi adicionada.

## [0.75.49] - 2026-08-05

### Rack, navegação e fluxo físico
- O Rack vazio fica alinhado ao cartão inicial.
- Clique esquerdo segurado movimenta o Canvas; a roda altera somente o zoom.
- Mudanças assíncronas de tamanho disparam novo cálculo e sobreposições acionam organização automática.

### OLT e uplinks
- Slot de serviço vazio abre com clique comum; placa instalada abre por botão direito.
- O editor permanece aberto depois de instalar a placa e permite potência manual por PON.
- Slots de uplink ficam no topo e aceitam modelo e portas individuais RJ45 1G, SFP 1G e SFP+ 10G.

### DIO e matriz de fusão
- Frente segue a cor SC/APC ou SC/UPC; traseira livre fica vermelha e fundida fica laranja.
- A matriz fica compacta e o botão Desvincular cabo volta a funcionar.
- Nenhuma migration foi adicionada.

## [0.75.48] - 2026-08-05

### Rack vazio e cadastro
- O gabinete físico e os cartões de cabos ficam ocultos enquanto não houver OLT, DIO ou Switch.
- O cadastro da OLT deixa de exibir PONs por slot e cria todos os slots de serviço/uplink informados.
- PTO e Outro deixam de aparecer no menu do Rack.

### OLT e potência
- O editor próprio da OLT permite ampliar o chassi, instalar mais placas e informar potência TX por PON no modo manual.
- Cada PON pode destacar o caminho conhecido OLT → DIO → cabo e calcular a potência estimada após as perdas cadastradas.

### DIO e estabilidade
- Portas do DIO ficam compactas, com detalhes no hover/botão direito e linhas terminando no centro dos pontos.
- O cabo traseiro ligado ao DIO volta a ser desenhado a partir da topologia persistida.
- Helpers de consulta do módulo v0.75.8 passam a tolerar raízes ausentes, eliminando o TypeError ao editar o Rack.
- Nenhuma migration foi adicionada.

## [0.75.47] - 2026-08-05

### OLT e portas PON
- O número da PON fica acima do ponto de conexão, sem sobreposição visual.
- O cadastro inicial da OLT pede slots de serviço e slots de uplink, sem criar PONs automaticamente.
- As portas PON continuam sendo criadas somente ao instalar uma placa no slot de serviço.

### Navegação do Rack
- O clique esquerdo segurado movimenta o Rack mantendo o zoom atual.
- Os handlers antigos são interceptados antes de disputar o mesmo gesto.

### Menu do Rack
- PTO e Outro deixam de aparecer na inclusão de equipamentos do Rack.
- Nenhuma migration foi adicionada.

## [0.75.46] - 2026-08-05

### Navegação do Rack
- Um único controlador passa a cuidar de zoom, pan e botões de ajuste.
- O Rack pode ser arrastado vertical e horizontalmente depois do zoom, inclusive sobre o gabinete, organizadores e áreas vazias dos equipamentos.
- O arraste de equipamentos pelo cabeçalho e os cliques nas portas continuam separados do pan.

### Correção de conflito
- Os handlers antigos da v0.75.42 e v0.75.45 deixam de disputar wheel e pointer events.
- Nenhuma migration e nenhuma alteração de topologia foram adicionadas.

## [0.75.45] - 2026-08-05

### Chassi e placas de serviço
- A OLT passa a ser criada como chassi com slots vazios, em disposição vertical ou horizontal.
- Duplo clique ou botão direito em cada slot instala ou edita a placa de serviço.
- Cada placa define modelo, GPON/XG-PON/XGS-PON e quantidade exata de portas PON.

### Navegação
- O pan após zoom usa eventos globais e funciona com botão esquerdo na área vazia ou botão central.

### Uplinks
- Uplinks ficam fora desta rodada; novas OLTs são criadas sem uplinks.

### Compatibilidade
- DIO, organizadores, calhas e roteamento traseiro foram preservados.
- Nenhuma migration foi adicionada.

## [0.75.44] - 2026-08-05

### OLT determinística
- O cadastro da OLT cria exatamente a quantidade informada de placas e PONs por placa.
- A face da OLT passa a ser renderizada pelas placas persistidas, sem transformar PONs em linhas genéricas.

### Uplinks explícitos
- Grupos de uplink são definidos no cadastro com nome, quantidade de portas e tipo RJ45, SFP ou SFP+.
- Zero grupos cria a OLT sem uplinks.
- Somente portas registradas no metadata da v0.75.44 são exibidas como uplink.

### Navegação
- Zoom pela roda passa a preservar o ponto sob o cursor.
- Arrastar a área vazia altera a translação do Canvas, permitindo navegar em qualquer direção após o zoom.

### Compatibilidade
- Organizadores e roteamento por calhas foram preservados.
- Nenhuma migration foi adicionada.

## [0.75.43] - 2026-08-05

### Navegação do Rack
- O Canvas volta a permitir deslocamento por arraste na área vazia, preservando a roda do mouse para zoom.
- O arraste do cabeçalho continua reservado ao encaixe dos equipamentos em unidades U.

### Organizadores e rotas
- Cada equipamento usa seu organizador local antes de entrar na calha lateral.
- Cada cavidade do DIO recebe um organizador próprio, inclusive a última cavidade.
- Cabos externos e cordões frontais deixam de entrar diretamente nas portas sem passar pelo organizador correspondente.

### OLT, uplinks e placas
- A área inferior da OLT separa placas de serviço e uplinks físicos.
- Uplinks RJ45 1G, SFP 1G e SFP+ 10G podem ser criados e editados.
- Placas de serviço podem registrar modelo e tecnologia GPON, XG-PON ou XGS-PON pelo botão direito.

### Interface
- Os botões redundantes Ligar portas e Editar linhas são removidos da barra superior do Rack.
- Nenhuma migration foi adicionada.

## [0.75.42] - 2026-08-05

### Rack 19 polegadas compacto
- O Rack passa a acompanhar a largura padrão da OLT/DIO, sem gabinete vazio maior que os equipamentos.
- A altura visual usa somente as unidades U necessárias para a ocupação atual.
- OLT, DIO, Switch, Roteador e Firewall compartilham a mesma largura 19 polegadas.

### Organizadores e caminhos
- O Rack reserva 1U entre equipamentos para organizadores horizontais.
- Cordões frontais usam calhas laterais e o organizador mais próximo.
- Cabos externos chegam às cavidades do DIO pela lateral mais adequada, mantendo um tronco traseiro por cabo.

### DIO e Switch
- DIO mantém cavidades de 12 portas com organizadores ópticos entre bandejas.
- Switches são cadastrados em modal moderno com nome, fabricante, modelo, IP e quantidade de portas.
- Portas de Switch/Roteador/Firewall são geradas no backend e exibidas em até 12 por linha.

### Tipos e zoom
- PTO, ONU/ONT, Rádio PTP, Access Point e Outro deixam de ser oferecidos dentro do Rack.
- A roda do mouse controla diretamente o zoom; os botões de zoom e ajuste permanecem.
- Nenhuma migration foi adicionada.

## [0.75.41] - 2026-08-05

### Correção do Rack físico
- Corrigido o erro de JavaScript causado por `closest()` receber um elemento DOM em vez de seletor CSS.
- Equipamentos podem ser movidos pelo cabeçalho com encaixe vertical em unidades U.
- Posições manuais são persistidas no layout do elemento e podem ser descartadas com Auto organizar.

### Prevenção de sobreposição
- Posições U repetidas são realocadas para o espaço livre mais próximo.
- A altura é medida depois da largura final do Rack, evitando OLT e DIO sobrepostos.
- O Rack usa 42U por padrão e cresce quando necessário.

### Compatibilidade
- Calhas, troncos traseiros, deduplicação e Torre em Canvas livre foram preservados.
- Nenhuma migration e nenhum endpoint novo.

## [0.75.40] - 2026-08-05

### Rack físico e calhas
- O Rack passa a posicionar equipamentos por unidades U dentro de um gabinete travado.
- Cordões frontais saem do ponto exato da porta e percorrem a calha lateral mais próxima.
- Cabos externos usam um único tronco traseiro por cabo, com derivações curtas até os DIOs.

### Correção de duplicações
- Corrigidos atributos data inconsistentes que duplicavam resumos de cabos, alvos CABOS e botões Fusões após reaberturas.
- Rack e Torre removem cartões e controles visuais repetidos pelo mesmo ID.

### Compatibilidade
- Nenhuma migration e nenhum endpoint novo.

## [0.75.39] - 2026-08-05

### DIO com frente e traseira independentes
- Cada porta do DIO exibe a fusão/terminação traseira em laranja e o cordão frontal em roxo, permitindo os dois vínculos simultaneamente.
- A fusão traseira não bloqueia a PON da OLT na frente da mesma porta; romper um lado preserva o outro.
- DIO organizado em cavidades de 12 posições, com indicador laranja na frente quando a traseira está ligada.

### Rack, OLT, PTO, ONU/ONT e DROP
- OLT compacta com larguras persistentes P/M/G/Auto.
- PTO mostra entrada óptica e conector SC/APC ou SC/UPC; ONU/ONT mostra PON, LAN e potência RX opcional.
- DROP pode terminar diretamente em DIO, PTO ou porta PON de ONU/ONT.
- Editor legado de equipamentos é substituído no Canvas por um modal moderno de criação e edição.

### CTO, CEO e CDO
- CTO passa a compartilhar o divisor direcional, cabos verticais nos dois lados e splitters centrais de CEO/CDO.
- Entrada/saída considera a topologia real; mover visualmente não altera origem/destino sem comando explícito.

### Cabos, reservas e informações
- Botão direito no cabo oferece informações, edição, inversão, CTO, CEO, CDO, reserva, associação/desassociação e exclusão.
- Painel do cabo reúne fibras, conexões, caixas, reservas, comprimento, ocupação e orçamento óptico estimado.
- Reserva técnica registra metragem, tipo, posição, responsável e observação usando os modelos existentes.

### Persistência e estabilidade
- Preferências adicionais de OLT e cavidades do DIO são persistidas no metadata do elemento.
- Nenhuma migration foi adicionada.

## [0.75.38] - 2026-08-04

### Rack, OLT e DIO
- O ponto agregado do cabo no Rack foi movido para a esquerda, reduzindo a volta visual da linha ao vincular em DIOs posicionados à esquerda do cabo.
- O traçado de arraste e as ligações agregadas Rack → DIO passam a usar atualização em requestAnimationFrame, deixando a direção mais responsiva durante o movimento.
- O DIO no Canvas passa a seguir o mesmo idioma visual de bandejas/cavidades do restante do Rack, com o alvo de cabos separado da frente do equipamento.
- A OLT compacta fica mais flexível para leitura, com largura ampliável e portas só com números.

### CEO, CDO e CTO
- CEO/CDO/CTO passam a usar um divisor central pontilhado no Canvas para reforçar entrada à esquerda e saída à direita.
- Em caixas de distribuição, cabos podem nascer dos dois lados e a legenda muda automaticamente entre entrada e saída.
- As fibras continuam verticais, uma abaixo da outra.

### UX do editor
- O editor óptico destaca que a captura de cabos próximos está limitada a 5 m.
- O resumo de conexões evita mensagens confusas quando só existem ligações de splitter.

## [0.75.37] - 2026-08-04

### CEO/CDO — cabos em coluna real
- Cada cabo de CEO/CDO é desenhado verticalmente, um abaixo do outro, com uma única coluna de fibras numeradas. CTO mantém seu arranjo próprio.
- O painel lateral passa a chamar tudo de Conexões e separa fusões cabo a cabo de ligações de entrada/saída/cascata de splitter.

### Rack, DIO e fusões
- O cabo no Rack vira um cartão compacto com um único ponto agregado; arrastar esse ponto até o DIO vincula o cabo sem espalhar todas as fibras no Canvas principal.
- O DIO ganha botão Fusões e uma janela própria em matriz: cabos/tubos/fibras à esquerda, seleção rápida ao centro e portas agrupadas de 12 à direita.
- Um clique na fibra seguido de um clique na porta cria a fusão. Auto fusão sequencial distribui fibras livres nas portas livres a partir da porta escolhida.
- Botão direito ou duplo clique numa porta ocupada rompe a fusão com confirmação própria.

### OLT compacta e desempenho
- A OLT passa a usar linhas por slot e até 16 colunas de portas, exibindo somente os números das interfaces. Textos repetidos como PON e numerações longas saem do Canvas.
- Nenhum MutationObserver novo, nenhuma migration e nenhuma alteração destrutiva de dados.

## [0.75.36] - 2026-08-04

### CEO/CDO — cabos verticais e traçados editáveis
- CEO e CDO continuam no mesmo workspace óptico e recebem organização vertical específica dos cabos na migração do layout v3; CTO preserva o arranjo anterior.
- Cada ligação pode permanecer em autoajuste ou ser convertida em traçado manual com pontos arrastáveis. Estilos curva, ortogonal e reta são opcionais e persistidos no layout.
- Botão direito no Canvas abre menu próprio para adicionar splitter ou nota. Sobre uma ligação, oferece editar, autoajustar, escolher estilo e romper/desligar.
- Duplo clique numa fusão ou ligação abre confirmação para rompimento, sem `alert`, `prompt` ou `confirm` nativos.

### Cores e captura
- Fusão cabo a cabo usa gradiente meio a meio com as cores reais das duas fibras. Ligações entre splitter e cabo usam a cor da fibra ligada.
- Captura e associação por proximidade de caixas ópticas passam a ter limite rígido de 5 metros no frontend e backend.

### Arquitetura
- Rotas manuais são salvas em `unifilar_layout.links`, sem migration e sem alterar Rack/Torre.
- O menu contextual e a edição de linhas permanecem dentro da raiz isolada do workspace óptico.

## [0.75.35] - 2026-08-04

### Editor óptico — ligações diretas
- CTO, CEO e CDO continuam isoladas do DOM do Rack/Torre, mas a interface passa a se apresentar apenas como Caixa óptica.
- Cabos organizados em colunas verticais. Ligações podem ser criadas selecionando ponta a ponta ou arrastando uma linha diretamente no Canvas.
- Fusão fibra-fibra, entrada/saída de splitter e cascata usam o mesmo fluxo simples de pontas.
- A ideia de bandeja foi removida da UX; o agrupamento legado do backend é criado e usado internamente sem pedir IDs ao projetista.
- Notas livres podem ser criadas e editadas com o texto definido pelo projetista.

### Diálogos
- Novo `IXCMapDialog` substitui os popups nativos do navegador no editor óptico, com confirmação, texto, seleção e formulário próprios.

### Rack e DIO
- DIO deixa explícito o sentido: esquerda para OLT/equipamento e direita para cabos/rede externa.
- Widgets de cabo ganham alça de redimensionamento, alternância de largura e grade de fibras responsiva, com preferência persistida no navegador.

### Segurança e arquitetura
- Nenhuma migration. Nenhum dado óptico é apagado.
- O polimento do Rack usa apenas os eventos públicos do workspace e não adiciona `MutationObserver`.

## [0.75.34] - 2026-08-04

### Adicionado — workspace óptico isolado
- Novo Canvas 2D exclusivo para CTO, CEO e CDO, carregado pelos módulos `static/js/optical/*` e pelo CSS `map-optical-workspace-v07534.css`.
- Cabos e fibras em painel próprio, criação/remoção de bandejas e fusões, ligação de entrada e saídas de splitters, criação/remoção de splitters, notas e layout persistente.
- Portas de atendimento da CTO ficam em seção separada das saídas ópticas do splitter, evitando a confusão de modelos que existia no editor experimental.
- Cabos próximos podem ser associados à caixa sem reutilizar o DOM do Rack/Torre.

### Arquitetura e estabilidade
- O workspace cria uma raiz DOM própria por abertura, usa `AbortController`, `ResizeObserver` descartável, seletores locais e token de sessão.
- Fechar ou trocar a caixa aborta requisições pendentes, remove o DOM e encerra timers/listeners da sessão.
- Nenhum arquivo do novo módulo contém referências a `#map-master-container`, `#container-dialog`, `#unifilar-dialog` ou `openContainerWorkspace`.
- Rack e Torre permanecem no fluxo original, sem alteração de seus arquivos de Canvas.

### Segurança
- POST/DELETE de fusões, PATCH de layout, CRUD de bandejas e POST/PATCH/DELETE de splitters agora exigem permissão de edição da empresa no backend.
- Sem migrations e sem exclusão automática de dados.

## [0.75.33] - 2026-08-04

### Removido — integração experimental CTO/CEO/CDO no motor do Rack/Torre
- Reversão completa das v0.75.26 a v0.75.32: CTO, CEO e CDO não abrem mais `openContainerWorkspace` (o Canvas 2D/shell do Rack e da Torre). Elas reutilizavam e alteravam o mesmo DOM interno (`#container-dialog`, `#map-master-container`, `.tower-workspace-actions-v0750`) usado pelo Rack/Torre, causando `Cannot read properties of null (reading 'value')` em `redrawOpticalLinks` e `Cannot set properties of null (setting 'innerHTML')` em `renderEquipmentList`/`openContainerWorkspace` depois de abrir uma caixa óptica.
- `static/js/map-cto-suite.js` removido do repositório e de `templates/map.html`. Nenhum script, import, callback global ou integração de clique/menu de contexto do módulo óptico experimental permanece carregado.
- `map-editor.js`, `map-v0758-core-ui.js` e `map-v0750-tower-workspace.js` revertidos ao comportamento anterior à integração: `containerIdentity`/`updateContainerIdentity` voltam a tratar só `rack`/`tower`.
- Os 5 endpoints compartilhados (`container_equipment`, `container_port_links`, `container_layout_v3`, `create_passive_endpoint_v3`, `import_container_device_type_yaml`) voltam a aceitar só `RACK`/`TOWER`.
- Clicar ou usar o menu de contexto numa CTO/CEO/CDO agora mostra "Editor óptico temporariamente desativado para reconstrução." — sem abrir o Canvas do Rack/Torre e sem reabrir o antigo `#unifilar-dialog` como solução improvisada.

### Corrigido — Rack/Torre
- `renderEquipmentList` (`map-master-suite.js`) ganhou uma guarda defensiva: se `[data-panel="equipment"]` não existir, registra o erro no console e retorna, em vez de derrubar o editor com um `TypeError`.
- Preservada a correção genuína de `.tower-workspace-actions-v0750 [hidden]`/`.tower-popover-v0750 [hidden]` (CSS `display:none !important`, introduzida junto da integração mas não específica dela — afeta o Rack/Torre em geral).

### Adicionado
- Comando `python manage.py reset_optical_test_data [--dry-run|--confirm]`: relata o volume de dados ópticos de CTO/CEO/CDO (splitters, bandejas, fusões, portas ocupadas por clientes reais, cabos conectados) e remove apenas resíduos estruturais da integração quebrada (equipamento genérico e metadata de layout do Canvas do Rack/Torre presos numa caixa óptica). Nunca apaga splitters, bandejas ou fusões reais — não há como distinguir dado de teste de dado de produção nesses modelos.

### Segurança
- Sem migrations. Nenhum dado é apagado automaticamente; `reset_optical_test_data` exige `--confirm` e roda dentro de `transaction.atomic()`.
- Prepara terreno para a reconstrução isolada do editor óptico de CTO/CEO/CDO, em arquivo/arquitetura própria, sem depender do DOM do Rack/Torre.

## [0.75.32] - 2026-08-04

### Corrigido — Canvas óptico abre repetidamente sem quebrar
- Corrige `Cannot read properties of null (reading 'value')` em `redrawOpticalLinks`: controles de estilo e zoom agora são procurados dentro do Canvas da sessão atual, nunca globalmente no documento.
- Cada abertura/renderização de CTO, CEO ou CDO agora cria uma sessão própria, invalida a anterior e remove listeners de `window`, `document`, Canvas e gráfico ao fechar, trocar de caixa ou atualizar.
- Respostas assíncronas atrasadas são descartadas por geração; uma caixa fechada não consegue mais sobrescrever a caixa aberta depois.
- O `#container-dialog` encerra explicitamente a sessão óptica ao fechar.

### Corrigido — portas de atendimento da CTO
- O contador da CTO não confunde mais saída de splitter fusionada com cliente atendido. Agora mostra separadamente `atendimentos/capacidade` (portas legadas vinculadas a `access_point_id`) e `saídas fusionadas/saídas ópticas`.

### Interface
- Estado próprio de carregamento e erro dentro do Canvas óptico, sem janela antiga sobreposta.
- Rack e Torre não tiveram seu motor alterado.
- Sem migrations e sem endpoint novo.

## [0.75.31] - 2026-08-04

### Alterado — CTO, CEO e CDO no mesmo editor 2D do Rack/Torre
- CEO/CDO (`element_type=splice_box`) agora abrem `openContainerWorkspace`, exatamente o mesmo motor/shell usado por Rack, Torre e CTO. O conteúdo específico de splitter, cabo, nota e fusão continua pertencendo ao `map-cto-suite.js`, embutido no painel comum — sem reabrir o editor antigo em outra janela.
- O menu de contexto também abre o editor técnico comum; não existe mais caminho lateral que mande CEO/CDO para `showUnifilar()`.
- Identidade própria preservada pelo subtipo (`CEO`, `CDO` ou fallback `CEO/CDO`), com título, estrutura e estado óptico corretos.
- Controles de equipamento genérico permanecem ocultos em CTO/CEO/CDO; Rack e Torre não foram alterados.
- O widget superior mostra portas usadas/capacidade na CTO e quantidade de fusões/splitters na CEO/CDO.

### Backend
- Os mesmos cinco endpoints do shell comum agora aceitam também `NetworkElement.ElementType.SPLICE_BOX`: equipamentos do container (bootstrap do shell), links internos, layout v3, endpoint passivo v3 e importação YAML.
- O payload do container passa a incluir `subtype`, necessário para diferenciar CEO de CDO no frontend.

### Segurança
- Mudanças aditivas; sem migrations.
- Base validada contra `main` no commit `64d9cca1bf998d15542794ebbf03d67837906e93` (MAP v0.75.30).

## [0.75.30] - 2026-08-04

### Corrigido — bug real reportado com print
- Usuário mostrou print: clicar em "+ Nota"/"Fusões" abria o "Editor técnico" **antigo** como uma janela flutuante separada, por cima do Canvas novo — exatamente o formato que vinha sendo eliminado a sessão inteira. Causa: a v0.75.28/29 fazia esses botões chamarem `showUnifilar()`, que abre `#unifilar-dialog` (um `<dialog>` HTML diferente do `#container-dialog` da Torre) — e esse dialog, ao abrir dentro do Canvas da Torre, vira uma janela flutuante arrastável (mesmo mecanismo que o Rack usa pra fusão de DIO, `enhanceFusion()`). Pra CTO isso resultava em 2 janelas visíveis ao mesmo tempo.

### Alterado — arquitetura: Canvas da CTO embutido de verdade
- O Canvas de splitter/cabo/nota (`map-cto-suite.js`) agora é renderizado **dentro** do mesmo painel `[data-panel="canvas"]` que o Rack/Torre usa pro Canvas de equipamento — não abre mais `#unifilar-dialog` como janela separada pra CTO em nenhum fluxo.
- `map-cto-suite.js`: `render()` ganhou um 3º parâmetro `options` — `options.embedded` (pula os `unifilarDialog.showModal()`/`classList.add()`, já não faz sentido fora de uma janela própria) e `options.onRefresh` (callback usado no lugar do antigo `unifilarDialog.close(); await showUnifilar(...)` — sem isso, qualquer ação dentro do Canvas embutido reabriria a janela antiga de novo). Os ~15 pontos internos de "refresh depois de uma ação" (criar fusão, adicionar splitter, excluir nota, etc.) foram trocados por uma chamada única, `await refreshCtoView()`, que decide qual dos dois comportamentos usar.
- Corrigido também um vazamento de listener: sem o evento "close" do dialog pra limpar, cada refresh no modo embutido empilharia mais um listener de `resize` sem remover o anterior — agora há um `activeResizeHandler` compartilhado que é removido no início de cada `render()`.
- `map-v0758-core-ui.js`: `ensureCtoEmbeddedCanvas()` cria (uma vez) e mantém atualizado o Canvas embutido; `triggerCtoAction()` faz os botões "+ Splitter"/"+ Nota"/"Estrutura" da barra de ferramentas clicarem direto nos botões já existentes de dentro do Canvas embutido (escondidos visualmente, mas continuam clicáveis via JS) — reaproveita a lógica de sempre, não duplica.
- Botão **"Fibras"/"Fusões" removido da CTO** (ficou só pro Rack, onde já fazia sentido) — a fusão agora acontece direto no Canvas, sem precisar de um botão pra "abrir" nada.
- `.tower-empty-v0750` (estado vazio de equipamento) e `.master-canvas-scroll` (Canvas de equipamento) forçados a sumir via CSS (`!important`) quando o container é uma CTO — o Canvas embutido ocupa o lugar deles.

### Segurança
- `map-master-suite.js` (o motor de renderização de equipamento do Rack/Torre) **não foi tocado** — o Canvas embutido da CTO vive como um elemento irmão novo dentro do mesmo painel, sem competir pelo `.master-canvas-nodes` que esse arquivo gerencia.
- Sem migrations. Sem endpoint novo.

## [0.75.29] - 2026-08-04

### Alterado — CTO sem equipamento genérico, com splitter/nota/fusões/portas
- Confirmado pelo usuário: "agora sim tá como eu queria" (v0.75.28, CTO abrindo o motor real da Torre). Pedido de continuação: "tire tudo que for equipamento e adicione pra fazer as fusões aí e adicionar splitter, nota, e já aparecer 1 widget da quantidade de porta que a CTO aceita para ligar clientes e DROPs."
- **Removido da CTO** (só dela — Rack/Torre continuam com tudo): botão "+ Adicionar" (equipamento genérico), "Ligar portas", "Editar linhas", e no menu Ferramentas: "Inventário" e "Relatório de ligações".
- **Adicionado na barra de ferramentas da CTO**: botões "+ Splitter" e "+ Nota" — abrem o editor de fusões (`map-cto-suite.js`) já disparando a mesma ação que os botões internos dele usam (reaproveitado, não duplicado). Botão "Fibras" renomeado pra "Fusões" no contexto da CTO (já abria o editor de fusões desde a v0.75.28).
- **Widget de portas**: mostra `usadas/capacidade` na barra de ferramentas — capacidade vem de `element.cto.capacity`, uso conta as saídas de splitter já ligadas a fibra (clientes/DROPs).
- Estado vazio da CTO no Canvas também ganhou botões próprios ("+ Splitter", "+ Nota", "Abrir Fusões") em vez do texto genérico de equipamento.

### Corrigido
- Achado durante a implementação: `.tower-workspace-actions-v0750 button`/`.tower-popover-v0750 button` têm `display:inline-flex` sem `!important`, que vence a regra `[hidden] { display:none }` do navegador por origem de cascata (estilo de autor sempre vence estilo de user-agent, mesmo com especificidade menor). Isso significa que o filtro **já existente** de tipos de equipamento por rack/tower (`button.hidden = !allowed.has(...)`) pode não estar escondendo visualmente os botões corretamente. Adicionado um reforço defensivo (`[hidden] { display:none !important; }`) que corrige isso tanto pros toggles novos da CTO quanto pro filtro antigo.

### Segurança
- Endpoint de API novo usado pelo widget de portas: nenhum — reaproveita `GET /api/map/elements/<id>/`, já existente, já usado por `showUnifilar()`.
- `map-v0758-core-ui.js` mantém a regra "sem URL de API crua nesse arquivo" (garantida pelo teste `test_map_v0750_static.py`) — o widget busca dados via um helper novo exposto em `window.networkMap.fetchElement()`, não com a URL escrita direto nesse arquivo.
- Sem migrations. Nenhuma mudança de comportamento pro Rack/Torre — todos os toggles são reavaliados (`identity.type === "cto"`), nunca aditivos, então rack/tower continuam mostrando exatamente o que já mostravam.

## [0.75.28] - 2026-08-04

### Alterado — mudança de arquitetura (só CTO)
- Pedido direto do usuário: "não pensa só faz, copia geral da torre pra CTO... identico, toda função." A CTO agora abre **o mesmo motor/janela do Rack/Torre** (`openContainerWorkspace`/`map-master-suite.js`), não uma cópia visual — o mesmo Canvas de equipamento, o mesmo "+ Adicionar", "Ligar portas", "Editar linhas", "Ferramentas" (Inventário, Relatório, Importar YAML, Organizar, Exportar PNG/PDF), tudo. CDO/CEO continuam no editor próprio (`map-cto-suite.js`) — pedido foi só CTO por enquanto.
- **Backend**: 5 endpoints que antes só aceitavam `rack`/`tower` agora também aceitam `cto`: `container_equipment` (criar/listar equipamento), `container_port_links` (cordões internos), `container_layout_v3` (posição dos nós no Canvas), `create_passive_endpoint_v3` (criar PTO), `import_container_device_type_yaml` (Importar YAML). Corrigido também um `KeyError` real que teria derrubado a importação de YAML numa CTO (`ALLOWED_BY_CONTAINER[container.element_type]` sem chave pra `cto`).
- **Frontend**: clicar numa CTO no mapa agora abre `openContainerWorkspace` (antes abria `showUnifilar`). A CTO ganhou identidade própria no Canvas (título "Editor técnico da CTO", ícone da CTO, texto do estado vazio) — antes qualquer coisa que não fosse "rack" caía no rótulo de "Torre" por padrão, o que teria feito uma CTO aberta por esse motor aparecer com título/ícone de Torre.
- O botão **"Fibras"** do toolbar (que na Torre/Rack só destaca fibra) agora, na CTO, abre direto o editor de splitter/cabo (`map-cto-suite.js`) por cima do Canvas — mesmo padrão que o Rack usa pra abrir a fusão de DIO clicando na porta traseira (janela flutuante arrastável, feita por `enhanceFusion()` em `map-master-suite.js`, sem nenhuma mudança nela).

### Segurança
- Toda mudança em código compartilhado com Rack/Torre foi feita como **extensão aditiva de 2 vias pra 3 vias** (`tipo === "rack" ? X : tipo === "cto" ? Y : Z`) — o comportamento de rack e tower não muda em nenhum dos pontos tocados, só foi adicionado um terceiro branch pra "cto". Verificado em cada um dos ~13 pontos de decisão encontrados por busca em `map-master-suite.js`/`map-v0758-core-ui.js`/`map-v0750-tower-workspace.js`.
- Sem migrations.

### Nota técnica (limitação conhecida, não é bug)
- Quando a CTO abre o editor de splitter/cabo por cima do Canvas (via "Fibras"), a janela flutuante fica sem o cabeçalho nativo visível (mesma regra da v0.75.27, que esconde esse cabeçalho pra CTO) — isso significa que **arrastar a janela flutuante pela barra de título não funciona** nesse caso específico (o Rack, que usa o cabeçalho nativo pra isso, não tem esse problema). A janela abre, funciona e fecha normalmente — só não é arrastável nesse fluxo aninhado. Ajustável numa próxima rodada se incomodar.

## [0.75.27] - 2026-08-04

### Corrigido
- Usuário apontou que só o conteúdo interno da CTO/CDO/CEO tinha ficado igual ao Rack/Torre — a **janela em si** (como abre, borda, sombra, z-index, cabeçalho) continuava diferente. Corrigido:
  - A janela da CTO/CDO/CEO (`#unifilar-dialog`) agora usa os **mesmos valores literais** de borda, sombra e z-index que a janela do Rack/Torre (`#container-dialog`) — não só "parecido", copiado direto do CSS da Torre.
  - Offset da barra lateral recolhida corrigido pra bater com a Torre (72px/54px, antes era 66px e não tratava o modo "minimizado" da sidebar).
  - **Cabeçalho nativo duplicado removido**: a CTO/CDO/CEO mostrava o título nativo do `<dialog>` ("Fusões · NOME" + X) E a barra de ferramentas nova por baixo — duas barras empilhadas, diferente da Torre (que esconde o cabeçalho nativo e usa só a barra de ferramentas). Agora, só quando é CTO/CDO/CEO, o cabeçalho nativo fica escondido e a barra de ferramentas ganhou seu próprio botão fechar (mesmo estilo `.tower-workspace-close-v0758` que a Torre usa). O Rack (fusão de DIO/cabo) e o fallback continuam com o cabeçalho nativo normal — não usam a barra nova, não tinham esse problema.

## [0.75.26] - 2026-08-04

### Alterado — mudança de arquitetura
- **Canvas 2D da CTO/CDO/CEO ganhou arquivo próprio**: `static/js/map-cto-suite.js`, extraído do bloco `if (element.splice_box)` que vivia dentro de `showUnifilar()` em `map-editor.js` (~600 linhas movidas, não reescritas). Mesma lógica de arquitetura do Rack/Torre, que já tem seu próprio dono (`map-master-suite.js`). Pedido explícito do usuário: separar o código da CTO/CDO/CEO num sistema com nome próprio, pra poder adicionar/remover funções dela sem nenhum risco de afetar o Rack/Torre (e vice-versa).
- Extração **mecânica** (recorte e cola): nenhuma linha de lógica foi reescrita, só relocada. Mesmos IDs/classes DOM preservados (`.unifilar-zoom`, `#unifilar-feedback`, `.optical-links`, `.ceo-quick-toolbar-v07521` etc.), então os 3 scripts decoradores que dependem dessa estrutura (`map-fusion-polish.js`, `map-optical-editor-v2.js`, `map-optical-editor-v3.js`) continuam funcionando sem nenhuma mudança.
- Dependências que o novo arquivo precisa de `map-editor.js` (`api`, `notify`, `escapeHtml`, `askValue`, `centerWithin`, `formatBudgetTooltip`, `splitterLossLabel`, `openRouteInfoDialog`, `unifilarDialog`) são expostas via `window.networkMap`, lidas em tempo de chamada — não importa a ordem de carregamento entre os dois arquivos.
- `map-editor.js` agora só chama `window.mapCtoSuite.render(element, content)` no lugar do bloco antigo.

### Segurança
- **Nenhum arquivo do Rack/Torre tocado.**
- **Nenhum endpoint de API mudou** — o novo arquivo chama exatamente as mesmas rotas de sempre (`/api/map/elements/<id>/splices/`, `/layout/`, `/splitters/...`).
- Verificação rigorosa da extração: catalogados programaticamente TODOS os identificadores externos usados dentro do bloco extraído (via regex sobre chamadas de função e acesso de propriedade), confirmando que a lista de dependências passadas via `window.networkMap` está completa.

## [0.75.25] - 2026-08-04

### Corrigido
- **Bug real de "2 ícones sobrepostos"**: encontrado em `map-optical-editor-v3.css` — pra CTO/CEO/RACK existiam DOIS sistemas de ícone ativos ao mesmo tempo no mesmo marcador: o SVG normal (`networkIcon()`, `map-editor.js`) e um ícone `::before` em máscara (hardcoded nesse CSS), que ficava escondendo o SVG normal via `display:none` só nesses 3 tipos. Removido o sistema `::before` — agora só existe 1 ícone por marcador, igual pra todos os tipos.
- **Texto "CDO" duplicado**: `map-v092.css` tinha `small::after { content: "CDO"; }`, que acrescentava um segundo "CDO" ao lado do rótulo que o próprio ícone já mostra — removido.

### Alterado
- **Ícones do mapa substituídos** pelo kit SVG fornecido pelo usuário (CTO, PTO, CDO, CEO, RACK, TORRE, POSTE, RESERVA técnica, POP/CPD) — `networkIcon()` em `map-editor.js` e o marcador de reserva técnica. OLT/DIO não tinham ícone novo no kit, mantidos como estavam (usados só dentro do Rack/Torre, não no kit fornecido).
- Caixa do ícone no mapa (`.network-marker svg`) ajustada de 21×17px pra 22×22px — os ícones novos usam viewBox quadrado (32×32) e ficavam espremidos no tamanho retangular antigo.
- **"Organizar equipamentos" removido da CTO/CDO/CEO**: o botão "Organizar" que `map-fusion-polish.js` injeta na barra de linhas continua existindo pro Rack (faz sentido lá, com DIO/cabo), mas é removido quando o editor é de CTO/CDO/CEO (detectado pela barra `.ceo-quick-toolbar-v07521`, feita na v0.75.23) — pedido explícito do usuário.

### Confirmado (sem mudança de código)
- CTO/CDO/CEO só aceitam splitter, cabo e nota — nunca existiu opção de adicionar equipamento genérico nessas seções (não é algo que precisou ser "removido", nunca esteve lá).

## [0.75.24] - 2026-08-04

### Corrigido
- Confirmado com print real do usuário: o nó de cabo da CTO/CDO/CEO já tinha o contorno do Canvas 2D (`master-canvas-node`, desde a v0.75.20/22), mas as fibras **dentro** dele ainda apareciam como lista vertical simples (uma por linha, sem borda) — a v0.75.22 só tinha dado o visual em pílula às portas do splitter (`.master-node-port`), nunca às fibras do cabo (`.fiber-port`). Agora as fibras também ficam em grade de 2 colunas com borda/fundo em pílula, igual às portas do splitter e do Rack/Torre.
- Mudança **só em CSS**, escopada a `.master-cable-node-v07519 .fiber-port` — não afeta o card de fusão do Rack (`renderRackFusionDiagram`), que reaproveita `.fiber-port` sem essa classe.

## [0.75.23] - 2026-08-04

### Alterado
- **Barra de ferramentas da CTO/CDO/CEO reescrita para reaproveitar as mesmas classes CSS do Rack/Torre** (`.tower-workspace-toolbar-v0750`, `.tower-workspace-actions-v0750`, `.tower-popover-v0750`, `.tower-drawer-v0750`, `.tower-structure-*`), a pedido explícito do usuário ("copie da torre a mesma função"). Botões novos: **Estrutura** (mostra os splitters e cabos já cadastrados, sem poder adicionar equipamento genérico — a CTO/CDO/CEO não tem esse conceito), **Fibras** (destaca portas livres/ocupadas), **Atualizar** (recarrega). **Ferramentas** ficou só com o que faz sentido aqui (estilo de linha) — sem "Importar YAML"/"Organizar equipamentos", que são conceitos de equipamento genérico que não existem na CTO/CDO.
- "+ Splitter"/"+ Nota" (da v0.75.21) foram mantidos — não são "equipamento" no sentido do Rack/Torre (switch/DIO/AP/etc.), são o próprio conteúdo da CTO/CDO, e o usuário pediu explicitamente pra manter a parte de cabo/splitter sem alteração.
- **Nenhuma linha da lógica de clique-para-ligar fibra/splitter foi tocada** — só a moldura ao redor. Confirmado por `tests/test_map_v07523_contract.py`.

### Segurança
- Backup dos 2 arquivos alterados (`map-editor.js`, `map-v0758-core-ui.css`) feito em `.map-v074-backup/` antes de editar, a pedido do usuário.
- **Nenhum arquivo do Rack/Torre foi alterado** (`map-master-suite.js`, `map-v0750-tower-workspace.js` intactos) — a reutilização foi só de classes CSS já publicadas e reaproveitáveis, não de código/endpoint.
- **O endpoint de equipamento do Rack/Torre (`/api/map/elements/<id>/equipment/`) não foi tocado nem estendido** para aceitar CTO/CDO — ele continua restrito a `rack`/`tower`. Ver nota técnica abaixo.

### Nota técnica (por que não é literalmente o mesmo componente)
- O pedido original era "copie da torre" o componente inteiro (`openContainerWorkspace`/Canvas de equipamento do Rack/Torre). Investigando o código, esse componente depende de um endpoint de backend (`/api/map/elements/<id>/equipment/`) hoje filtrado para `element_type in (rack, tower)` — CTO/CDO nunca tiveram o conceito de "equipamento genérico" (`ContainerEquipment`), só splitter/cabo (modelos completamente diferentes). Estender esse endpoint pra aceitar CTO/CDO tocaria o mesmo código que serve o Rack/Torre em produção — risco desnecessário, já que o pedido explícito era justamente **não** ter equipamento genérico na CTO/CDO.
- Em vez disso: a barra de ferramentas (visual) foi reconstruída com as mesmas classes CSS, mas o conteúdo abaixo dela continua sendo o editor de fusões já existente (splitter + cabo), sem mudar nenhuma chamada de API. Resultado prático pro usuário é o mesmo pedido — visual igual ao Rack/Torre, sem opção de adicionar equipamento — sem o risco de tocar o backend compartilhado.

## [0.75.22] - 2026-08-04

### Corrigido
- visual "formato antigo" reportado nas telas de CTO/CDO/CEO: o herdeiro visual do Canvas 2D (`master-canvas-node`, feito na v0.75.20) só usava propriedades sem `!important`, dependendo da ordem de carregamento entre `map-editor.css` e `map-master-suite.css` pra vencer o CSS antigo (`.fiber-cable-node`/`.graph-splitter-node`). Reforçado com `!important` pra garantir a aparência do Rack/Torre (fundo, borda, sombra) independente disso.
- saídas do splitter (F1, F2, ...) agora ficam em uma grade de 2 colunas do lado direito, em vez de uma lista vertical única — mesma leitura visual esquerda=entra/direita=sai do DIO.

### Confirmado (já existia, não é novo)
- CTOs já recebem splitter e portas de atendimento ao cliente automaticamente na criação (`apps/network_map/cto_defaults.py::ensure_cto_default_splitters`, chamado tanto na criação manual quanto na importação KMZ).
- nós de cabo já invertem o lado da porta (esquerda/direita) automaticamente conforme a posição em que são arrastados no diagrama (`side-left-v0758`/`side-right-v0758`, calculado em `centerWithin()` de `map-editor.js`), inclusive nas linhas de fusão e nos handles de rota.

### Nota técnica (o que ainda falta pra paridade completa)
- Ainda não existe uma "caixa" física de CTO/CDO no diagrama (equivalente ao chassi do DIO) hospedando os cabos à esquerda/direita — hoje splitter e cabos são nós independentes conectados por linha. Construir essa caixa é a próxima fatia grande dessa frente de trabalho.

## [0.75.21] - 2026-08-04

### Adicionado
- barra de atalhos nova no topo do editor de fusões da CTO/CDO/CEO, com a mesma aparência da barra de ferramentas do Rack/Torre ("+ Splitter", "+ Nota"). **100% aditivo**: a barra de instruções antiga continua exatamente como estava, inalterada — os botões novos só chamam os mesmos menus de contexto que já existiam (clique com botão direito no fundo do quadro).

### Nota técnica (por que não fui além)
- Investigação encontrou que a área de toolbar/zoom (`.unifilar-zoom`) e o desenho de linhas (`.optical-links`) desse editor são reconstruídos em sequência por 5 scripts decoradores diferentes (`map-optical-editor-v2.js`, `v3.js`, `map-fusion-polish.js`, `map-v0750-tower-workspace.js`, `map-v0758-core-ui.js`) — `map-fusion-polish.js`, por exemplo, substitui inteiramente o conteúdo de `.unifilar-zoom` por um slider próprio. Reescrever essas áreas sem poder ver o resultado ao vivo arrisca quebrar algum desses 5 scripts. Decisão tomada com o usuário: continuar só adicionando (nunca removendo/renomeando) até dar pra testar ao vivo.

## [0.75.20] - 2026-08-04

### Adicionado
- **Primeira fatia real do "sistema próprio" da CTO/CDO/CEO** (decisão do usuário: construir isolado do código do Rack/Torre, sem risco de quebrar o que já funciona lá): nós de splitter e cabo do editor de fusões ganham as classes visuais do Canvas 2D (`master-canvas-node`/`master-node-port`) — mesma borda, sombra, raio e estilo de porta em pílula do Rack/Torre. Porta do splitter usada fica verde. Nenhuma lógica de clique-para-ligar, arraste ou dado foi tocada — só herança visual, isolada dentro de `#unifilar-dialog` (nunca usado pelo Rack/Torre).

### Nota sobre o caminho escolhido
- Avaliadas 2 arquiteturas: (a) sistema próprio isolado, mesmo visual — **escolhida**; (b) reaproveitar literalmente o mesmo painel/endpoints do Rack/Torre, fingindo splitter como equipamento — descartada por risco real de quebrar Rack/Torre em produção caso a tradução de dados saísse errada. Trabalho continua em fatias pequenas e testáveis, como todas as versões anteriores.

## [0.75.19] - 2026-08-04

### Corrigido
- enlace PTP mostrava "Status: Livre" na torre de DESTINO mesmo já ligado — causa raiz: um enlace PTP é gravado como `ContainerPortLink` apontando só para a torre de ORIGEM; a torre de destino nunca via essa ligação nos próprios dados. Agora consulta também a lista de enlaces PTP do projeto inteiro (que tem os dois lados) antes de decidir se a porta está livre.

### Adicionado
- distância real entre as duas torres (Haversine, a partir das coordenadas já existentes) exibida na linha tracejada do mapa (tooltip e popup) e no tooltip da porta wireless.
- bolinha da porta wireless muda de cor: amarela = livre, verde = enlace PTP configurado.

### Não incluído nesta versão (honestidade sobre o que falta)
- Terceiro estado "vermelho = caiu" pedido pelo usuário **não foi implementado** — exigiria monitoramento real (SNMP/telemetria) do enlace PTP, que não existe hoje para este tipo de ligação. Mostrar "vermelho" sem medir de verdade seria inventar um dado, não uma correção.

## [0.75.18] - 2026-08-04

### Adicionado
- editor de fusões da CTO/CDO/CEO ganha zoom com Ctrl+roda do mouse e pan arrastando o fundo — mesma sensação de navegação do Canvas 2D do Rack/Torre. Nenhuma lógica de clique-para-ligar (cabo/splitter/porta), arraste de nó ou zoom por botão foi alterada — só um jeito a mais de navegar no mesmo `.optical-graph`.

### Nota sobre "restringir a splitter padrão"
- Confirmado por leitura do código: o editor de fusões **nunca** permitiu adicionar equipamento arbitrário — o menu de contexto do fundo só tem "+ Adicionar splitter" e "+ Adicionar nota". Essa parte do pedido já era o comportamento existente, não precisou de mudança.

## [0.75.17] - 2026-08-04

### Corrigido
- **PTP retornava 500 sempre**: `ContainerEquipmentPort` não tem `company`/`company_id` próprio (só `ContainerEquipment`, via `equipment`), mas os 3 endpoints de PTP (`ptp_link_candidates`, `ptp_links` POST, `ptp_link_detail` DELETE) acessavam `.company_id` direto na porta — `AttributeError` derrubava a requisição com HTTP 500 toda vez, mesmo em enlaces criados manualmente com interface wireless corretamente marcada. Corrigido acessando `.equipment.company_id` (ou `.container.company_id` no link). Confirmado com traceback real do servidor.
- Mensagem de "porta já em uso" do DIO (`container_port_links`) agora diz qual lado (frontal/traseira) e qual ligação existente conflitou, em vez de um genérico "uma das portas já está em uso" — não achei inconsistência na lógica em si (frente e trás do mesmo slot já eram tratadas como ocupações independentes), mas sem a mensagem específica não dava pra diagnosticar sem acesso direto ao banco.

## [0.75.16] - 2026-08-04

### Corrigido
- rota de ligação (cordão/fusão) que tinha ponto de dobra ajustado manualmente ficava "presa" na posição antiga quando o equipamento ou cabo era movido, voltando a cortar por cima de outra coisa — ao terminar de mover, os links tocando o item movido agora recalculam a rota automática (com desvio de obstáculo) do zero.

### Adicionado
- passar o mouse por cima de uma linha de ligação acende (glow) o cordão/fusão inteiro, pra dar pra seguir o caminho exato mesmo com várias linhas cruzando o Canvas.

### Investigado, aguardando mais informação
- **DIO "porta já em uso"**: revisão da validação de conflito de porta (`container_port_links`) não encontrou inconsistência entre a orientação esquerda/direita (frente/trás) trocada na v0.75.14 e a checagem de uso — front e rear do mesmo slot já são tratados como ocupações independentes no banco. Preciso de um passo a passo exato (qual cabo/porta, em qual equipamento) pra reproduzir e confirmar se é um bug real ou uma tentativa de reconectar uma porta já ocupada.
- **PTP — erro 500**: ainda sem o traceback do servidor pedido na v0.75.15. Sem ele não dá pra avançar com segurança.
- **Roteamento pela canaleta entre placas da OLT** (como no HTML de referência do Gemini) e **CTO/CDO/CEO com o mesmo Canvas do Rack/Torre, restrito a splitter padrão + cabos**: escopo confirmado pelo usuário como parte da mesma frente de trabalho da "Organização Rack" 44U — fica para a entrega dedicada combinada.

## [0.75.15] - 2026-08-04

### Corrigido
- alça do fio: o círculo de clique maior (fill transparente) podia não responder no centro exato em alguns navegadores — forçado `pointer-events: all` explicitamente, sem depender da cor de preenchimento;
- cordão OLT → DIO: a descida reta a partir da porta de origem podia atravessar outra porta da mesma placa numa linha abaixo (ex.: PON 13/1 descendo por cima de PON 13/9) — agora desvia lateralmente até achar uma coluna livre antes de descer;
- OLT: a grade de portas de cada placa deixou de ser fixa em 2 colunas e passa a ser fluida — quantas cabem lado a lado depende só da largura disponível.

### Adicionado
- OLT: alça de redimensionar (arrastar a lateral do card) para aumentar a largura do chassi — mais portas passam a caber lado a lado automaticamente, sem precisar editar nada; largura fica salva por equipamento.
- OLT: os slots utilitários do chassi (módulos vazios, fonte de alimentação) do YAML do fabricante deixaram de ser desenhados — só as placas de serviço (PON/uplink) aparecem.

### Investigado, não resolvido nesta versão
- **Enlace PTP retorna erro 500** ao abrir a lista de torres/rádios de destino (`GET /api/map/ptp-links/candidates/`). Revisão completa do código do endpoint (`apps/network_map/api/ptp_links.py`) e das funções relacionadas não encontrou causa aparente — todos os campos, imports e permissões conferem. Preciso do traceback real do servidor (`docker logs` do container web no momento do erro) para diagnosticar com segurança, em vez de arriscar uma mudança sem prova.
- **CTO/CDO/CEO ainda com a mesma tela**: a modernização visual da v0.75.14 (CSS) foi aplicada, mas não é o que foi pedido — o usuário quer o mesmo tipo de Canvas 2D usado no Rack/Torre, não uma repintura do editor de fusões existente. Isso exige reescrever a renderização interna de `showUnifilar()` e todos os seletores que dependem dela em pelo menos 5 arquivos (`map-editor.js`, `map-optical-editor-v2.js`, `map-optical-editor-v3.js`, `map-fusion-polish.js`, `map-v0750-tower-workspace.js`) — escopo do tamanho de uma versão inteira, não uma correção pontual.

## [0.75.14] - 2026-08-04

### Corrigido
- alça de dobra do fio: bolinha visual volta ao tamanho pequeno, mas o clique/arraste passa a usar uma área de clique invisível maior por cima dela — não precisa mais mirar o pixel exato nem inflar o desenho;
- enlace PTP: rádio PTP e Access Point recém-criados não vinham com nenhuma porta, então clicar "Ligar PTP?" não tinha porta wireless nenhuma pra clicar — agora já nascem com uma porta wireless padrão; o aviso de "nenhum destino disponível" também deixou de ser um toast discreto e virou um diálogo que não passa despercebido;
- orientação do DIO no Canvas 2D: porta da esquerda passa a ser a frente (cordão pro equipamento/OLT) e a da direita a traseira (fusão com o cabo) — estava invertido; o roteamento automático do cordão OLT→DIO também passou a escolher o lado do canal de acordo com onde a porta de destino realmente está, em vez de sempre sair pela direita.

### Atualizado
- editor de fusões de CTO/CDO/CEO (cabo, splitter, portas): a estrutura de nós arrastáveis e clique-para-ligar já existia e já funciona (não é um formulário antigo) — a aparência foi modernizada para a mesma linguagem visual do Canvas 2D de Rack/Torre (cores, raio de borda, sombra), sem alterar nenhuma lógica de conexão.

## [0.75.13] - 2026-08-04

### Corrigido
- notas do Canvas: o contêiner-pai (`.master-canvas-nodes`) bloqueava todo evento de ponteiro por herança e nunca reabria a exceção pra `.master-canvas-note` — clique, arraste, editar e excluir não chegavam ao elemento em um navegador real. Corrigido com `pointer-events: auto` na nota;
- roteamento automático de ligações ("Organizar equipamentos" e novas ligações sem ponto manual) passa a medir as caixas realmente renderizadas de equipamentos, cabos e notas e desviar delas, em vez de usar uma coordenada de meio-caminho fixa que cortava por cima de outras caixas;
- alça de reposicionamento do meio do fio ganhou raio de clique maior (8px → 13px) e o sistema de alças antigo (que ficava duplicado sobre o mesmo ponto e "fantasma" depois de um arraste) foi desativado, já que o sistema novo (seleção por clique na linha, arraste, exclusão por botão direito) já cobre tudo sozinho;
- botão "Fibras" deixa de aparecer no editor da Torre (o destaque de fibra é específico do DIO em Rack); segue disponível no Rack.

### Adicionado
- botão "Atualizar" no meio do editor de Rack/Torre, recarrega os dados de equipamentos/cabos sem sair do Canvas nem recarregar a página;
- OLT ganha uma opção de placa de uplink (SFP/SFP+/gerência) além das placas de PON já existentes, direto pelo editor de equipamento — sem precisar de importação de YAML pra isso.

## [0.75.12] - 2026-08-03

### Corrigido
- rotas internas deixam de reutilizar pontos antigos incompatíveis com o layout atual e passam a usar caminhos ortogonais arredondados;
- notas do Canvas passam a salvar corretamente arraste, edição e exclusão;
- cliques em portas e ligações ganham área útil maior sem engrossar o desenho;
- cargas concorrentes do mapa deixam de tentar registrar os mesmos markers duas vezes.

### Adicionado
- placas PON da OLT em linhas horizontais com canaletas entre placas para passagem dos cordões;
- tooltip de porta mostrando status livre ou o destino conectado;
- conector visual SC/APC verde e SC/UPC azul nas terminações ópticas;
- terminação direta de DROP em DIO, PTO e porta PON de ONU/ONT;
- enlace PTP guiado entre torres e linha tracejada persistida no mapa;
- busca automática por latitude e longitude digitadas;
- atualização do equipamento dentro do editor, sem recarregar a página inteira.

## [0.75.10] - 2026-08-03

### Corrigido
- o workspace de Rack/Torre passa a ocupar a linha útil inteira do grid; equipamentos, cabos e notas deixam de ficar em um Canvas com altura zero;
- o menu global não reage ao botão direito sobre rótulos permanentes do Leaflet;
- a atualização após importar YAML volta ao fluxo único `mapMasterSuite.openContainerWorkspace`.

### Adicionado
- DIOs acima de 24 portas mostram todas as bandejas, com 12 posições por bandeja e corredor visual entre elas;
- cards de cabos ficam verticais no Canvas de Rack/Torre e no workspace óptico;
- importação YAML expande intervalos como `PON 13/[1-16]`, preserva slots, módulos, alimentação, altura e comentários;
- OLTs importadas por YAML usam chassi modular agrupado por slot/placa;
- o editor óptico existente passa a usar shell amplo em tela inteira sem trocar o motor de fusões já homologado.

# Changelog — Mapa

## [map-0.75.9] - 2026-08-03

### Hotfix: elimina renderização duplicada e restaura o Canvas

Investigação confirmou (com dados reais do banco, sem duplicidade de
registro em nenhum dos pontos testados) que os problemas relatados na
homologação da v0.75.8 eram todos de frontend, não de dado:

- **Rack/Torre** tinham DOIS renderers reagindo à mesma abertura: o
  `manageContainer()` legado (lista antiga) fazia sua própria chamada
  `equipment/`, e um `MutationObserver` observando `#container-dialog`
  disparava `enhanceContainer()` por baixo, fazendo uma SEGUNDA chamada
  `equipment/` + `container-layout-v3/` — daí o Canvas às vezes ficar
  vazio (condição de corrida entre os dois) e o Network mostrar
  `equipment/` duas vezes.
- O mesmo observer, reagindo cegamente a qualquer mudança de atributo
  no dialog, causava chamadas "stale" de `equipment/`/`container-layout-v3/`
  também ao abrir CTO/CDO — que nunca deveriam tocar nesse dialog.
- `canonicalElementFeatures()` escondia markers pelo critério errado
  (menor ID, ignorando se aquele ID tinha equipamentos/layout reais) —
  removido; a partir de agora cada `NetworkElement` real sempre aparece
  no mapa, e a deduplicação só elimina o mesmo ID repetido na mesma
  resposta da API (nunca por nome/tipo/coordenada).
- O menu de botão direito do marker só cortava a propagação do evento
  DEPOIS de checar modo de edição/disponibilidade do menu — se qualquer
  checagem falhasse, o clique vazava pro menu global "Adicionar ao
  mapa". Corte de propagação agora roda antes de qualquer `return`.

### Corrigido

- único fluxo de abertura de Rack/Torre: `openContainerWorkspace()`
  (map-master-suite.js), chamado direto pelo clique/menu do marker —
  1 chamada `equipment/`, 1 chamada `container-layout-v3/`, dialog só
  abre depois que o Canvas já foi desenhado com dado real;
- `MutationObserver` que disparava carregamento de dado removido —
  carregamento agora é sempre por chamada de função explícita;
- guarda de geração (`openGeneration`) contra resposta atrasada
  sobrescrever o editor de um elemento diferente;
- ao fechar o dialog: geração avança, `dataset.elementId` e estado
  temporário são limpos, sem disparar novo carregamento;
- Rack/Torre abrem direto na aba Canvas 2D (não mais na lista
  "Equipamentos");
- registro central de markers por ID real (`elementMarkers`), nunca
  duas instâncias do mesmo ID na mesma camada;
- `window.mapV0758` criado vazio já na primeira linha do arquivo — um
  erro de inicialização posterior não deixa mais o objeto inteiro
  `undefined` pro resto da sessão da página;
- segunda camada de proteção no menu global: ignora cliques sobre
  `.leaflet-marker-icon`, `.leaflet-interactive`, `.map-element-marker`
  e qualquer elemento com `data-element-id`.

### Preservado

- `PLATFORM_VERSION` em `0.82.0`, intacta;
- `${DOCKER_SOCK_GID:-999}` intacto no `docker-compose.yml`;
- nenhuma migration;
- nenhum dado excluído ou alterado no banco;
- `map-v0757-field-usability.js`/`.css` continuam removidos (não
  reintroduzidos).

## [map-0.75.8] - 2026-08-03

### Hotfix estrutural

- remove o runtime complementar da v0.75.7 que interceptava cliques, notas e workspaces;
- mantém um único renderer para marcadores, Canvas e fusões;
- volta a abrir CTO/CEO/CDO como workspace modal, sem vazamento para o menu global;
- adiciona resolvedor manual de registros sobrepostos, exibindo IDs antes da exclusão;
- preserva notas multilinha, confirmação de movimento, cabos laterais, direção óptica e coordenadas negativas;
- Rack continua com OLT/DIO/Switch/Router/Firewall/PTO/Outros e sem AP/PTP/ONU;
- `PLATFORM_VERSION=0.82.0`, `MAP_VERSION=0.75.8`, sem migration.

## [map-0.75.7] - 2026-08-03

### Adicionado

- confirmação ao mover pontos, com restauração da posição original ao cancelar;
- editor próprio de notas multilinha para Canvas e diagramas de fusão;
- menu contextual por botão direito em Rack, Torre, CTO, CEO e CDO;
- aviso de direção óptica possivelmente invertida ao finalizar um cabo.

### Alterado

- Rack e Torre passam a ter identidade visual e regras de equipamentos distintas;
- CTO, CEO e CDO usam o editor óptico em workspace amplo;
- cabos trocam automaticamente o lado visual ao cruzar o centro do Canvas;
- Canvas e fusões aceitam coordenadas negativas, sem parede invisível;
- auto-fit passa a considerar também as notas.

### Corrigido

- cabeçalho/menu duplicado no editor técnico;
- criação repetida por duplo envio do formulário;
- `Esc` fechando todo o Canvas ao sair de uma janela interna;
- Rack permitindo ONU/ONT e omitindo Router, Firewall, PTO e Outros;
- fundo e título de Torre aparecendo ao abrir um Rack.

### Versionamento

- `PLATFORM_VERSION` preservada em `0.82.0`;
- `MAP_VERSION` atualizada para `0.75.7`;
- nenhuma migration.

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
