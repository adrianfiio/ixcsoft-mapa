# MAP v0.75.23 — CTO/CDO/CEO: barra de ferramentas igual ao Rack/Torre

## Objetivo

Pedido direto do usuário, depois de ver a CTO/CDO ainda com um visual
diferente do Rack/Torre mesmo após a v0.75.20/v0.75.22 (que só tinham
restilizado os nós de splitter/cabo, não a barra de ferramentas ao
redor): "CTO,CEO,CDO remove oque existe hoje e copie da torre a mesma
função, porém tire as opções de adicionar equipamentos deixa so botão
de FIBRAS ATUALIZAR, ESTRUTURA (...) NAO PODE ADICIONAR NENHUM
EQUIPAMENTO. A parte de cabo deixa igual não precisa alterar.
FERRAMENTAS tire Importar YAML, Organizar equipamentos."

## Investigação antes de mexer

- O clique num CTO/CDO/CEO no mapa abre `showUnifilar()`
  (`static/js/map-editor.js`) — um editor próprio, **diferente** do
  `openContainerWorkspace()` que o Rack/Torre usa
  (`window.mapMasterSuite.openContainerWorkspace`, definido em
  `map-master-suite.js`).
- O componente do Rack/Torre depende de um endpoint de backend
  (`/api/map/elements/<id>/equipment/`) que hoje filtra
  `element_type in (rack, tower)` (`apps/network_map/api/views.py`,
  linhas 905 e 1623) — CTO/CDO nunca tiveram "equipamento genérico"
  (`ContainerEquipment`), só splitter/cabo, que são modelos
  completamente diferentes (`CTOSplitter`/`CTOSplitterPort`).
- Estender esse endpoint pra aceitar CTO/CDO tocaria o mesmo código que
  atende Rack/Torre em produção hoje — e o próprio pedido do usuário é
  justamente que a CTO/CDO **não tenha** equipamento genérico. Ou seja,
  reusar o endpoint não seria só arriscado, seria a coisa errada a
  fazer.
- Decisão: reconstruir a barra de ferramentas reaproveitando as MESMAS
  classes CSS do Rack/Torre (`.tower-workspace-toolbar-v0750`,
  `.tower-workspace-actions-v0750`, `.tower-popover-v0750`,
  `.tower-drawer-v0750`, `.tower-structure-*` — todas já eram
  reutilizáveis, sem seletor de ID amarrando ao diálogo do Rack/Torre),
  mas manter o conteúdo abaixo dela (splitter/cabo) exatamente como
  está, sem tocar em `openContainerWorkspace`/no endpoint de
  equipamento.

## O que mudou

- **Backup** de `static/js/map-editor.js` e
  `static/css/map-v0758-core-ui.css` em `.map-v074-backup/` antes de
  qualquer edição, a pedido do usuário.
- Barra de ferramentas nova, visualmente igual ao Rack/Torre:
  - **Estrutura**: abre um painel lateral (mesma classe
    `.tower-drawer-v0750` do Rack/Torre) listando os splitters e cabos
    já cadastrados na CTO/CDO — clicar num item rola até ele no
    diagrama e destaca. Não tem opção de adicionar equipamento, porque
    CTO/CDO não tem esse conceito.
  - **Fibras**: alterna um destaque visual (portas livres em amarelo,
    portas usadas esmaecidas) — mesma ideia do botão "Fibras" do
    Rack/Torre, adaptada pro conceito de fibra/porta de splitter.
  - **Atualizar**: recarrega os dados e redesenha (mesmo padrão já
    usado em toda ação desse editor: fechar e reabrir o diálogo).
  - **Ferramentas**: só tem "Estilo de linha" (curva/reta/ortogonal,
    já existia antes, só mudou de lugar). Não tem "Importar YAML" nem
    "Organizar equipamentos" — pedido explícito do usuário, e nenhum
    dos dois faz sentido aqui mesmo.
  - **"+ Splitter" / "+ Nota"** (da v0.75.21) foram mantidos: não são
    "equipamento" no sentido do Rack/Torre, são o próprio conteúdo da
    CTO/CDO, e o pedido foi claro em manter a parte de cabo/splitter
    sem alteração.
- **Nenhuma linha da lógica de clique-para-ligar fibra/splitter foi
  tocada** — só a moldura ao redor (toolbar, drawer de estrutura,
  destaque de fibra). Todo o restante da função (arrastar nó, clicar
  em duas fibras para fundir, editar/excluir splitter, adicionar
  splitter/nota por clique direito, zoom, budget óptico) continua
  idêntico.

## O que NÃO foi feito (e por quê)

- **Não é literalmente o mesmo componente `openContainerWorkspace` do
  Rack/Torre** — pelo motivo explicado acima (endpoint de backend
  restrito a rack/tower, e o próprio pedido é não ter equipamento
  genérico aqui). O resultado visual e funcional pro usuário é o
  mesmo: barra igual, sem opção de adicionar equipamento.
- **Nenhum arquivo do Rack/Torre foi alterado**
  (`map-master-suite.js`, `map-v0750-tower-workspace.js` intactos).
- A sub-barra injetada pelos 3 scripts decoradores
  (`map-fusion-polish.js`, `map-optical-editor-v2.js`, `v3.js` — zoom
  deslizante, "Salvar versão", "Editar linhas" de rota manual,
  "Ortogonal"/"Automático"/"Excluir") continua existindo dentro de
  `.unifilar-zoom` (preservado de propósito, ver nota técnica anterior
  sobre os 5 scripts entrelaçados) e ainda tem visual próprio,
  diferente do Rack/Torre — não foi restilizada nesta versão.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhum endpoint de API alterado ou criado.
- Nenhum arquivo do Rack/Torre tocado.
