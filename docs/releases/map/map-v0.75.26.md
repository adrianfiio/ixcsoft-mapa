# MAP v0.75.26 — CTO/CDO/CEO ganha arquivo próprio (map-cto-suite.js)

## Objetivo

Pedido direto do usuário: "Vamos mudar a arquitetura dela, vamos
copiar da torre e levar para elas mas com outro nome no sistema, pois
elas depois iremos remover umas funções e adicionar." Ou seja: dar à
CTO/CDO/CEO a mesma estrutura arquitetural que o Rack/Torre já tem —
um arquivo próprio, dono do seu Canvas 2D — para que mudanças futuras
nela (adicionar/remover funções) não corram risco de afetar o
Rack/Torre, e vice-versa.

## O que existia antes

O Rack/Torre tem `map-master-suite.js` como dono do seu Canvas 2D
(renderização de equipamento, drag, zoom, portas, links). A CTO/CDO/CEO
não tinha equivalente: toda a lógica do seu Canvas (splitter, cabo,
nota, fusões, zoom, drag) vivia embutida dentro da função gigante
`showUnifilar()` em `map-editor.js`, misturada com o código de outros
tipos de elemento (Rack, fallback simples) e com toda a infraestrutura
geral do editor do mapa.

## O que mudou

- **Novo arquivo**: `static/js/map-cto-suite.js` — dono do Canvas 2D
  da CTO/CDO/CEO, no mesmo espírito que `map-master-suite.js` é do
  Rack/Torre.
- **Extração mecânica, não reescrita**: o bloco `if (element.splice_box)
  { ... }` (602 linhas) foi recortado de dentro de `showUnifilar()` e
  colado nesse novo arquivo, numa função `render(element, content)`.
  Nenhuma lógica foi alterada — mesma renderização de splitter/cabo/nota,
  mesmo sistema de clique-para-ligar fibra, mesmo zoom/pan, mesmos IDs
  e classes DOM.
- **Verificação da extração**: antes de mover o código, foi feito um
  levantamento programático (regex sobre todo o bloco) de todo
  identificador usado como chamada de função ou acesso de propriedade
  que não era declarado dentro do próprio bloco — confirmando a lista
  exata de dependências externas: `api`, `notify`, `escapeHtml`,
  `askValue`, `centerWithin`, `formatBudgetTooltip`,
  `splitterLossLabel`, `openRouteInfoDialog`, `unifilarDialog`.
  Nenhuma outra dependência externa (nem `state`, nem `containerDialog`,
  nem `elementForm` — variáveis exclusivas do fluxo de Rack/Torre/forms
  gerais) é usada dentro do Canvas da CTO/CDO/CEO.
- Essas dependências são expostas via `window.networkMap` (objeto que
  já existia, agora com mais campos), lidas dentro de `render()` no
  momento da chamada — não na hora do carregamento do script — então a
  ordem de `<script>` entre `map-editor.js` e `map-cto-suite.js` não
  importa para o funcionamento.
- `map-editor.js`'s `showUnifilar()` agora só verifica
  `element.splice_box` e delega: `await
  window.mapCtoSuite.render(element, content); return;`.
- `templates/map.html`: `<script src=".../map-cto-suite.js">`
  adicionado logo depois de `map-editor.js` e antes dos 3 scripts
  decoradores (`map-fusion-polish.js`, `map-optical-editor-v2.js`,
  `v3.js`) — mesma ordem relativa que já existia, só com o arquivo
  novo no meio.

## Por que os 3 scripts decoradores continuam funcionando

`map-fusion-polish.js`, `map-optical-editor-v2.js` e
`map-optical-editor-v3.js` procuram elementos por **classe/ID no DOM**
(`.unifilar-zoom`, `#unifilar-feedback`, `.optical-links`,
`.ceo-instructions`/`.ceo-quick-toolbar-v07521`), não por qual arquivo
JavaScript os criou. Como a extração preservou o HTML gerado
exatamente igual, esses 3 scripts continuam encontrando exatamente o
que já esperavam — nenhuma mudança neles foi necessária.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- **Nenhum endpoint de API alterado** — `map-cto-suite.js` chama
  exatamente as mesmas rotas de sempre.
- **Nenhum arquivo do Rack/Torre tocado**
  (`map-master-suite.js`/`map-v0750-tower-workspace.js` intactos).
- Verificação de sintaxe: chaves/parênteses/colchetes balanceados em
  ambos os arquivos JS (`map-editor.js` e `map-cto-suite.js`), contagem
  de crase (template literals) par em ambos.
