# MAP v0.75.25 — Ícones novos + bug de ícone duplicado + Organizar removido da CTO/CDO

## Objetivo

Pedido do usuário em texto (depois de tentar por imagens sem sucesso),
com um arquivo `icones.html` anexado contendo um kit de ícones SVG
pronto para CTO, PTO, CDO, CEO, RACK, TORRE, POSTE, RESERVA técnica e
POP/CPD. Pediu também para: identificar e corrigir um bug de "2 ícones
sobrepostos", garantir 1 ícone correto por elemento, e remover
"Organizar Automaticamente" da CTO/CEO/CDO (mantendo o resto do pedido
de Canvas 2D/tipos permitidos, que já estava resolvido nas versões
anteriores — ver nota abaixo).

## Bugs encontrados e corrigidos

### 1. Dois sistemas de ícone competindo no mesmo marcador (CTO/CEO/RACK)

`static/css/map-optical-editor-v3.css` escondia o SVG normal do
marcador (`display: none !important`) só para os tipos `cto`,
`splice_box` e `rack`, e desenhava OUTRO ícone por cima usando
`::before` com `mask-image` (um SVG diferente, hardcoded em data-URI,
sem nenhuma relação com `networkIcon()` em `map-editor.js`). Ou seja,
pra esses 3 tipos havia literalmente dois desenhos de ícone
definidos ao mesmo tempo pro mesmo marcador — um escondido, um visível
— e qualquer inconsistência de aplicação da classe `network-marker-v3`
(ordem de carregamento, timing de re-render) podia deixar os dois
visíveis simultaneamente. Para os outros tipos (pole, cdo, tower, cpd,
pto, olt) só existia o SVG normal — inconsistência confirmada entre
tipos.

**Correção**: removido o sistema `::before`/mask por completo. Agora
todo tipo usa exclusivamente o SVG de `networkIcon()` — 1 fonte de
ícone, sempre.

### 2. Texto "CDO" duplicado

`static/css/map-v092.css` tinha `.network-marker.splice_box.cdo
small::after { content: "CDO"; }`, que acrescentava um segundo "CDO"
depois do rótulo que o próprio ícone já mostra (`<small>CDO</small>`,
definido em `networkIcon()`). Antes disso ser notado, só não aparecia
duplicado porque `map-optical-editor-v3.css` tinha uma regra
cancelando esse `::after` — mas só nesse arquivo específico, e só se
carregado depois. Corrigido na raiz: removida a duplicação em
`map-v092.css`.

## Ícones substituídos

`networkIcon()` (`static/js/map-editor.js`) e o marcador de reserva
técnica (usa seu próprio `L.divIcon`, função separada) agora usam os
desenhos do kit fornecido: CTO, PTO, CDO, CEO (mesmo desenho do CDO,
só muda cor/rótulo — já era assim antes), RACK, TORRE, POSTE, RESERVA
(espiral) e POP/CPD. OLT e DIO não tinham ícone novo no kit — mantidos
como estavam (são exibidos dentro do Rack/Torre, não como marcador
avulso no mapa).

`.network-marker svg` (CSS) ajustado de 21×17px pra 22×22px — os
ícones novos usam viewBox quadrado (32×32) e ficavam distorcidos no
tamanho retangular antigo.

## "Organizar Automaticamente" removido da CTO/CDO/CEO

`map-fusion-polish.js` injeta um botão "Organizar" na barra de linhas
de qualquer editor de fusões (CTO/CDO/CEO E Rack, que reaproveita o
mesmo painel pra fusão de DIO/cabo). Faz sentido pro Rack (pode ter
muitos nós), mas não pra CTO/CDO/CEO — removido especificamente nesse
contexto, detectado pela presença da barra `.ceo-quick-toolbar-v07521`
(feita na v0.75.23, só existe nessa tela). O Rack continua com o botão.

## O que já estava resolvido (não é novo nesta versão)

- **CTO/CDO/CEO só aceitam cabo, splitter e nota** — nunca existiu
  opção de adicionar equipamento genérico nessas seções (v0.75.23 já
  confirmou isso ao reescrever a barra de ferramentas sem nenhum botão
  de "Adicionar equipamento").
- **Editar/desenhar fusões e linhas** — já existe (botões "Editar
  linhas", "Salvar versão", estilo de linha curva/reta/ortogonal,
  clique numa linha pra excluir), herdado dos decoradores
  `map-optical-editor-v2.js`/`v3.js`/`map-fusion-polish.js`. Não foi
  reescrito nesta versão (ver nota abaixo).
- **Zoom/pan, grid de fundo, tooltip, seleção** — já existentes desde
  v0.75.18 (zoom com Ctrl+roda, arrastar fundo) e anteriores.

## O que NÃO foi feito nesta versão

- A sub-barra de edição de linha (zoom deslizante, "Salvar versão",
  "Editar linhas", "Ortogonal"/"Automático"/"Excluir", injetada pelos 3
  scripts decoradores) continua com visual próprio, diferente do
  Rack/Torre — restilizá-la exige mexer nesses 3 scripts mais a fundo
  (área já identificada como frágil em versões anteriores). Fica pra
  uma fatia própria, testável ao vivo.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhum endpoint de API alterado.
- Nenhum arquivo do Rack/Torre (`map-master-suite.js`,
  `map-v0750-tower-workspace.js`) alterado — o botão "Organizar"
  continua existindo lá normalmente.
