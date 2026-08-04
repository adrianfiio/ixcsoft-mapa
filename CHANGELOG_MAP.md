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
