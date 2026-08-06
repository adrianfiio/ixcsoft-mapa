# MAP v0.75.55

Hotfix: pan, alinhamento visual e criação de equipamento no editor Canvas 2D
do Rack/Torre. Encontrado e corrigido a partir de um relato direto do
Adrian, com reprodução real no navegador (Playwright, ambiente Docker
isolado no servidor — nunca em produção).

## Contexto

Relato original (resumido): "no rack eu não consigo andar no canvas, tipo
eu dou zoom e não consigo movimentar para cima baixo e lados"; "a
ESTRUTURA DO RACK [o quadriculado de fundo] não fica alinhada" atrás do
cartão "Monte o rack..."; "no botão verde de Adicionar tem que tirar o +
servidor"; "na Torre aparece Monte a torre etc, porém adicionei o switch e
não sai esse menu"; "na Torre não pode ter essa opção de adicionar OLT".

Montei um ambiente Docker isolado no servidor (banco/Redis próprios, rede
própria, projeto `ixcsoft-test`, sem tocar em `ixcsoft-mapa-*`), criei
dados sintéticos (empresa, projeto, Rack e Torre de teste) e usei
Playwright com Chromium real para reproduzir cada item exatamente como
descrito, antes de tocar em qualquer código — e de novo depois, pra
confirmar a correção.

## Investigação e correção

### 1. Pan não funcionava em lugar nenhum do Canvas 2D do Rack

**Causa raiz confirmada**: `interactivePanTarget()`
(`map-rack-maintenance-v07552.js`) e `blockedPrimaryTarget()`
(`map-rack-viewport-v07546.js`) — as duas funções que decidem se um
clique deve iniciar o arraste do canvas — tinham `"dialog"` na lista de
seletores bloqueados. A intenção original era não iniciar pan ao clicar
dentro de algum modal aninhado por cima do canvas. O problema: **todo** o
editor técnico do Rack/Torre vive dentro de `#container-dialog` (um
elemento `<dialog>` de verdade), então `target.closest("dialog")` sempre
encontra esse próprio dialog como ancestral — não importa onde o usuário
clique dentro do canvas, o resultado é sempre "bloqueado". Confirmado com
um teste que arrasta o mouse e mede a transformação do canvas antes/depois:
`tx`/`ty` não mudavam nem 1px.

**Correção**: removido `"dialog"` das duas listas de bloqueio. Reconfirmado
com o mesmo teste: arraste de 150×100px resultou em `tx`/`ty` mudando
exatamente 150/100px.

**Extra**: a classe CSS que troca o cursor para "arrastando"
(`cursor: grabbing`) ainda referenciava `.v07549-is-panning`, de uma
versão anterior — o JS atual usa `.v07552-is-panning`. Corrigido também
(`map-rack-maintenance-v07549.css`), cosmético, sem efeito funcional.

### 2. Backdrop "ESTRUTURA DO RACK/DA TORRE" desalinhado

**Causa raiz confirmada**: o desenho de fundo decorativo
(`.tower-structure-backdrop-v0750`) era filho de `.master-canvas` — a
camada que recebe o `transform: translate(...) scale(...)` de pan/zoom, e
que tem largura/altura fixas via CSS (`1250px`/`760px`, ou
`max(100%,720px)`/`470px` conforme breakpoint) sem relação nenhuma com o
tamanho real do viewport visível. O cartão "Monte o rack/a torre..." (
`.tower-empty-v0750`), por outro lado, sempre foi filho de
`.master-canvas-scroll` — a camada que preenche o viewport de verdade
(`inset: 0`) e nunca sofre o transform. Resultado: os dois elementos
centralizavam relativos a caixas *diferentes*, e só ficavam visualmente
alinhados por coincidência de zoom/posição.

Havia inclusive uma tentativa anterior de corrigir isso (v0.75.49,
`#map-master-container.v07549-empty-aligned`) com deslocamentos manuais
(`top: 52%`/`43%` em vez de `50%`/`50%`) — um ajuste de sintoma, não da
causa, que só funcionava por acaso em algumas combinações de zoom.

**Correção**: `ensureStructureBackdrop()`
(`map-v0750-tower-workspace.js`) agora insere o backdrop dentro de
`.master-canvas-scroll` (mesmo nível do cartão vazio), não mais dentro de
`.master-canvas`. Os dois elementos agora centralizam relativos à mesma
caixa, sempre alinhados por construção. Os deslocamentos manuais de
`top`/`left` do v0.75.49 foram removidos (ficaram redundantes/incorretos
com o alinhamento correto); o tamanho maior do desenho de fundo do Rack
foi mantido.

### 3. Criar equipamento na Torre falhava sempre (não é só "o menu não some")

**Causa raiz confirmada, mais profunda que o sintoma relatado**: o
`<select>` de tipo de equipamento no diálogo "+ Equipamento"
(`map-master-suite.js`) é populado a partir de `state.bootstrap`. Esse
estado só é preenchido depois que `init()` espera `window.networkMap`
existir — mas `window.networkMap` fica `truthy` **antes** de
`loadProjects()` (em `map-editor.js`) terminar de selecionar o projeto no
`<select id="project-select">` (são duas linhas de código separadas: uma
dispara a promise de carregar projetos e não espera por ela, a próxima já
expõe `window.networkMap`). Se o primeiro `refreshBootstrap()` rodar
exatamente nessa janela, `projectId()` lê `""` do select ainda vazio,
`state.bootstrap` vira `null` e a função retorna sem buscar nada — e
**nunca mais tenta de novo**, porque o único outro gatilho é o evento
`"change"` do select, que não dispara quando o valor é setado por código
(`projectSelect.value = ...`).

Resultado prático: o `<select>` de tipo ficava permanentemente vazio,
`quickAdd()` não conseguia selecionar nenhum tipo, e o submit falhava com
`400 Tipo de equipamento inválido para esta estrutura.` — confirmado
capturando a resposta de rede real. Como nada foi criado de fato, o
cartão vazio continuava aparecendo — não porque a lógica de
esconder/mostrar estivesse quebrada, mas porque não havia o que mostrar.

**Correção**: `openEquipmentCreateDialog()` agora aguarda
`refreshBootstrap()` se `state.bootstrap` ainda não foi carregado — mesmo
padrão de guarda já usado em outros dois pontos do mesmo arquivo. Testado
de novo: `<select>` populado corretamente, `POST
/api/map/elements/2/equipment/` retornou `201`, equipamento criado, cartão
vazio corretamente escondido.

### 4. "Servidor" fora do menu Adicionar do Rack / "OLT" fora da Torre

Removidos:
- `["server", "Servidor", ...]` da lista `extraTypes`
  (`map-v0758-core-ui.js`) que popula o menu "Adicionar" do topo, e
  `"server"` do conjunto `rackAllowed`.
- `"olt"` do conjunto `towerAllowed` (mesmo arquivo) e do `allowed` da
  Torre em `openEquipmentCreateDialog()` (`map-master-suite.js`) — cobre
  tanto o menu do topo quanto o diálogo completo "+ Equipamento".

### 5. Achado extra durante a validação: botões do cartão vazio ficavam presos

Ao testar a sequência completa (abrir Rack → fechar → abrir Torre vazia,
na mesma sessão de página, sem recarregar), os botões do cartão vazio da
Torre continuavam mostrando "Adicionar OLT" — sobra do Rack aberto antes.
Causa: o bloco que escreve os botões do cartão vazio só existia para
`identity.type === "rack"`; ao trocar para Torre, nada reescrevia esses
botões, então ficavam com o conteúdo antigo. Corrigido escrevendo os
botões corretos nos dois casos (Rack: OLT/DIO/Switch; Torre: DIO/PTO/
Switch).

## Validação

- Ambiente Docker isolado no servidor (`ixcsoft-test`), banco/Redis
  próprios, produção (`ixcsoft-mapa-*`) nunca tocada.
- Playwright + Chromium real, sequência completa: login → mapa → modo
  edição → abrir Rack vazio → testar pan (confirmado, com medição exata
  de deslocamento) → conferir menu Adicionar (sem Servidor) → fechar →
  abrir Torre vazia → conferir menu Adicionar (sem OLT) → adicionar Switch
  pelo cartão vazio (equipamento criado de verdade, `201`, cartão
  escondido corretamente) → reabrir Rack (idempotência) → screenshots do
  alinhamento do backdrop antes/depois.
- `python -m py_compile` nos arquivos Python (nenhum tocado neste
  hotfix — só JS/CSS).
- Balanceamento de chaves/parênteses/colchetes nos 5 arquivos JS tocados.
- `tests/test_map_v07555_contract.py` (novo).
- Suíte histórica completa, rolling-bump dos arquivos que travam a
  "versão atual" nos testes.
- Ambiente de teste isolado derrubado por completo ao final (containers,
  volumes, imagens, pasta) — nada ficou para trás.

## Fora de escopo

- Nenhuma migration, nenhuma mudança de `PLATFORM_VERSION`.
- Não investiguei se o mesmo padrão de corrida (`state.bootstrap`) afeta
  outros pontos do código que também leem `state.bootstrap` sem guarda —
  só corrigi o ponto que causava o bug relatado
  (`openEquipmentCreateDialog`). Os outros dois usos existentes já tinham
  a guarda (`if (!state.bootstrap) await refreshBootstrap();`).
