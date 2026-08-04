# MAP v0.75.24 — CTO/CDO: fibras do cabo em grade, igual às portas do splitter

## Objetivo

Usuário mandou 2 prints lado a lado (CDO vs. Torre) mostrando que,
mesmo depois da v0.75.23 (barra de ferramentas igual ao Rack/Torre),
o conteúdo do cabo dentro do editor de fusões ainda parecia uma lista
antiga: fibras em linhas verticais simples, sem borda, bem diferente
das portas em pílula que o Rack/Torre mostra pros equipamentos.

## Causa

A v0.75.22 já tinha dado o visual do Canvas 2D (`master-canvas-node`)
para o **contorno** do nó de cabo e para as **portas do splitter**
(`.master-node-port`), mas esqueceu de dar o mesmo tratamento às
**fibras dentro do cabo** (`.fiber-port`) — essas continuaram usando o
CSS antigo de `map-editor.css`, que é uma lista de linhas com borda
inferior, sem fundo, pensada como lista de seleção, não como grade de
portas.

## O que mudou

- `static/css/map-v0758-core-ui.css`: novo bloco
  `MAP_V07524_CTO_FIBER_PORT_GRID` — `.fiber-port-list` dentro de um nó
  de cabo (`.master-cable-node-v07519`) vira grade de 2 colunas;
  `.fiber-port` ganha borda, fundo e cantos arredondados iguais às
  portas do splitter (`#22c55e` quando em uso, `#38bdf8` no hover).
- **Só CSS.** Nenhuma linha de JavaScript mudou nesta versão — a lógica
  de arrastar/clicar fibra pra criar fusão é exatamente a mesma.
- Escopado precisamente a `.master-cable-node-v07519 .fiber-port`, então
  **não afeta** o card de fusão do Rack (função
  `renderRackFusionDiagram`, usada pelo botão "Fusões" do Rack), que
  reaproveita a mesma classe `.fiber-port` só que sem
  `master-cable-node-v07519` — esse card continua com o visual que já
  tinha, de propósito (não foi pedido mudar).

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhum endpoint de API alterado.
- Nenhum arquivo JavaScript alterado.
- Nenhum arquivo do Rack/Torre tocado.
