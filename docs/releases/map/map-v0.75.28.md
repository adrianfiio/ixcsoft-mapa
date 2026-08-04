# MAP v0.75.28 — CTO abre o motor real do Rack/Torre

## Objetivo

Pedido direto, depois de rodadas anteriores terem só copiado o
**visual** da CTO/CDO/CEO (toolbar, janela, ícones — v0.75.20 a
v0.75.27): "na moral não quero que você pense, só faz... é difícil
copiar tudo da torre, toda função, etc, só pra CTO? Vamos só nela, só
CTO... deixa idêntico, não pensa, só faz, faz 1 cópia geral da torre
pra CTO."

Resposta direta à pergunta ("é difícil?"): sim, uma cópia 100% literal
não faz sentido porque a CTO guarda dado em tabelas diferentes
(`CTOSplitter`/`FiberCable`, não `ContainerEquipment`) — mas dá pra
fazer a CTO abrir o **mesmo motor/janela** que o Rack/Torre usa de
verdade (`openContainerWorkspace`, `map-master-suite.js`), não só uma
imitação visual. Foi isso que foi feito.

## Escopo: só CTO

O pedido foi explicitamente restrito a CTO ("vamos só nela, só CTO").
CDO/CEO (`splice_box`) continuam no editor próprio
(`map-cto-suite.js`, feito na v0.75.26) — não foram tocados.

## O que mudou

### Backend — 5 endpoints liberados pra `cto`

Todos eram restritos a `element_type in (rack, tower)`. Adicionado
`cto` a cada um, sem remover nem alterar o comportamento pra
rack/tower:

- `container_equipment` (`views.py`) — criar/listar equipamento.
- `container_port_links` (`views.py`) — cordões internos (OLT→DIO).
- `container_layout_v3` (`optical_editor_v3.py`) — salva a posição dos
  nós arrastados no Canvas. **Sem isso, arrastar um equipamento numa
  CTO nunca salvaria a posição.**
- `create_passive_endpoint_v3` (`optical_editor_v3.py`) — criar PTO
  pelo Canvas.
- `import_container_device_type_yaml` (`device_type_views.py`) —
  Importar YAML. Também corrigido um `KeyError` real que teria
  derrubado esse endpoint pra CTO:
  `ALLOWED_BY_CONTAINER[container.element_type]` é um dict sem chave
  pra `cto` — adicionada, mapeada pro mesmo conjunto permitido da
  Torre.

### Frontend — CTO abre o motor da Torre, com identidade própria

- `map-editor.js`: clicar numa CTO no mapa agora chama
  `openContainerWorkspace(id)` (o mesmo usado por Rack/Torre) em vez
  de `showUnifilar(id)`.
- `map-v0758-core-ui.js`: a CTO ganhou identidade própria no motor —
  antes, `containerIdentity()` só reconhecia "rack" e caía em "tower"
  pra qualquer outra coisa (o que faria uma CTO aberta por esse motor
  aparecer com título "Editor técnico da Torre" e ícone de Torre).
  Agora reconhece "cto" também: título "Editor técnico da CTO", ícone
  próprio (o mesmo desenho usado no marcador do mapa, do kit de
  ícones da v0.75.25), texto do estado vazio próprio.
- `map-v0750-tower-workspace.js`: o botão **"Fibras"** do toolbar
  (que no Rack/Torre só destaca fibra visualmente) agora, quando o
  container é uma CTO, abre direto o editor de splitter/cabo
  (`map-cto-suite.js`) por cima do Canvas — mesmo padrão que o Rack já
  usa pra abrir a fusão de DIO (clicando na porta traseira): uma
  janela flutuante arrastável, decorada automaticamente por
  `enhanceFusion()` em `map-master-suite.js` (nenhuma mudança nesse
  arquivo foi necessária — a decoração é genérica, baseada em
  `MutationObserver` sobre `#unifilar-dialog`, não em tipo de
  elemento).

## Como a segurança do Rack/Torre foi garantida

Toda mudança em código **compartilhado** com Rack/Torre foi feita como
extensão de uma decisão binária (`tipo === "rack" ? X : Y`) para uma
decisão de 3 vias (`tipo === "rack" ? X : tipo === "cto" ? Y : Z`) —
nunca alterando o `X` (rack) nem o `Z` (resultado padrão, que
continua sendo exatamente o que "tower" já recebia). Isso foi
verificado em cada um dos ~13 pontos de decisão encontrados por busca
sistemática (`grep`) por `"rack"` nos 3 arquivos do motor
(`map-master-suite.js`, `map-v0750-tower-workspace.js`,
`map-v0758-core-ui.js`) e por `element_type__in=[RACK, TOWER]` /
`[container.element_type]` no backend.

## Limitação conhecida (não é bug, é escopo)

Quando a CTO abre o editor de splitter/cabo por cima do Canvas (via
"Fibras"), essa janela flutuante fica sem o cabeçalho nativo visível
— regra herdada da v0.75.27, que esconde esse cabeçalho só pra CTO.
Isso significa que arrastar essa janela flutuante pela barra de
título não funciona nesse fluxo específico (o Rack, que ainda usa o
cabeçalho nativo pra fusão de DIO, não tem esse problema). A janela
abre, funciona e fecha normalmente pelo botão de fechar da barra de
ferramentas — só não é arrastável por aí. Ajustável se incomodar.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations (nenhum campo de model novo).
- 5 endpoints existentes ampliados (aceitam mais um `element_type`),
  nenhum endpoint novo criado, nenhum removido.
- Nenhuma linha de comportamento de Rack/Torre alterada — só
  adicionados branches novos, os existentes ficaram intocados.
