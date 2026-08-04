# MAP v0.75.30 — Canvas da CTO embutido de verdade (fim da janela dupla)

## Objetivo

Usuário mandou print mostrando o bug: clicar em "+ Nota" (ou "Fusões")
abria o **"Editor técnico" antigo** como uma janela flutuante pequena,
por cima do Canvas novo da CTO — duas janelas visíveis ao mesmo tempo.
Mensagem literal: "isso ficou burro na moral, clico fusões abre o
EDITOR TÉCNICO antigo não pode... vou te dar mais 1 chance."

## Causa raiz

A v0.75.28/29 fez os botões "+ Splitter"/"+ Nota"/"Fusões" chamarem
`window.networkMap.showUnifilar(id)` — que abre `#unifilar-dialog`,
um elemento `<dialog>` **completamente separado** do `#container-dialog`
que a Torre usa. Quando `#unifilar-dialog` abre enquanto o Canvas da
Torre já está na tela, `map-master-suite.js`'s `enhanceFusion()`
(mecanismo já existente, usado pelo Rack pra abrir a fusão de DIO)
transforma esse dialog numa janela flutuante arrastável por cima —
funcional pro Rack (que só usa isso ocasionalmente, clicando na porta
traseira de um DIO), mas errado pra CTO, cujo "conteúdo principal"
deveria ser esse Canvas o tempo todo, não um popup incidental.

## O que mudou

### O Canvas da CTO agora é embutido, não aberto como janela

`map-cto-suite.js` — `render(element, content)` virou
`render(element, content, options = {})`:

- `options.embedded` — quando `true`, pula
  `unifilarDialog.classList.add(...)`/`showModal()` (não faz mais
  sentido, não estamos numa janela própria) e marca `content` com a
  classe `cto-embedded-canvas-v07530`.
- `options.onRefresh` — callback chamado no lugar do antigo padrão
  `unifilarDialog.close(); await showUnifilar(element.id);`, repetido
  em **15 lugares** diferentes dentro da função (criar fusão, ligar
  splitter, excluir nota, editar splitter, etc.). Uma variável
  compartilhada, `refreshCtoView`, decide qual comportamento usar —
  sem essa troca, qualquer ação dentro do Canvas embutido reabriria a
  janela antiga de novo, reproduzindo o mesmo bug.
- Efeito colateral corrigido: sem o evento `"close"` do dialog pra
  limpar o listener de `resize`, o modo embutido vazaria um listener
  novo a cada refresh. Agora existe `activeResizeHandler` (módulo,
  compartilhado entre chamadas), removido no início de cada `render()`
  antes de registrar o próximo.

### `map-v0758-core-ui.js` — quem monta e mantém o Canvas embutido

- `ensureCtoEmbeddedCanvas(root, dialog)`: cria (uma vez, idempotente)
  uma `<div class="cto-embedded-canvas-v07530">` dentro do MESMO
  painel `[data-panel="canvas"]` que o Rack/Torre usaria pro Canvas de
  equipamento, e chama `window.mapCtoSuite.render(...)` com
  `embedded: true` e um `onRefresh` que re-busca os dados e
  re-renderiza no mesmo lugar (recursivo, sem nunca abrir
  `#unifilar-dialog`).
- `triggerCtoAction(root, action)`: os botões "+ Splitter"/"+ Nota"/
  "Estrutura" da barra de ferramentas da Torre agora clicam
  **diretamente** nos botões que já existem dentro do Canvas embutido
  (`[data-ceo-quick-add="..."]`, `[data-cto-structure-v07523]`) — eles
  ficam escondidos visualmente (a barra interna de
  `map-cto-suite.js` não aparece mais, redundante com a barra externa
  da Torre), mas continuam clicáveis via JavaScript. Reaproveita a
  lógica que já existia, não duplica nada.
- Botão **"Fibras"/"Fusões" removido da CTO** — só o Rack continua
  com ele (`toolbarFibersButton.hidden = identity.type !== "rack"`),
  onde ainda faz sentido (destaque de fibra pra fusão de DIO). Pra
  CTO, a fusão já acontece direto no Canvas, sem precisar de um botão
  "abrir".

### CSS — troca de camada, forçada

```css
#container-dialog.map-v0758-cto .tower-empty-v0750,
#container-dialog.map-v0758-cto .master-canvas-scroll {
    display: none !important;
}
```

Forçado com `!important` porque `.tower-empty-v0750` é escondido/
mostrado por `decorateNodes()` (`map-v0750-tower-workspace.js`) no
mesmo evento (`map:container-rendered`) que dispara
`updateContainerIdentity()` — a ordem de execução entre os dois
arquivos não é garantida, então depender só de `element.hidden` via
JavaScript teria risco de corrida. CSS `!important` resolve isso sem
ambiguidade, independente de quem rodou por último.

## Por que o Rack/Torre não foi afetado

`map-master-suite.js` (o motor que desenha equipamento — OLT, DIO,
switch — em `.master-canvas-nodes`) **não foi tocado**. O Canvas
embutido da CTO vive como um elemento **irmão novo**
(`.cto-embedded-canvas-v07530`) dentro do mesmo painel
`[data-panel="canvas"]`, nunca escrevendo em `.master-canvas-nodes`
nem em `.master-canvas-scroll` — por isso não compete com nada que
esse arquivo gerencia. Confirmado lendo `renderContainerCanvas()`
linha por linha: só mexe em `.master-canvas-nodes.innerHTML`.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhum endpoint de API novo ou alterado.
- `map-master-suite.js` intocado.
