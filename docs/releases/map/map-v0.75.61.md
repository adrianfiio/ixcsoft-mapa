# MAP v0.75.61

Hotfix no Rack: cabo vinculado sumindo da matriz de fusão, "Auto
fusão" quebrada, e só 10-11 das 12 fibras aparecendo. Os três eram, na
prática, dois bugs de backend + um de CSS que se disfarçavam de
problema único ao usuário.

## Cabo vinculado sumia da matriz de fusão

`+ Vincular` grava o cabo só em `dio.metadata` (chave
`dio_fusion_cable_ids_v07537`) — nenhum `ContainerPortLink` existe
ainda nesse momento (é a fusão em si, feita depois, que cria isso), e
o cabo pode perfeitamente não ter `origin`/`destination` apontando pra
este Rack específico: ele só está sendo **fundido** ali, não nasce nem
termina fisicamente ali (cenário comum: um cabo de distribuição que
passa por um DIO intermediário pra cross-connect).

A consulta `_candidate_cables()` (que monta a lista "CABOS
VINCULADOS") filtrava só por `origin=container OU
destination=container OU já existe algum ContainerPortLink nesse
container` — um cabo vinculado só por metadata, sem nenhuma dessas
três condições, era descartado silenciosamente da lista, mesmo estando
genuinamente "vinculado".

**Correção**: `_candidate_cables()` ganhou um parâmetro `extra_ids`,
incluindo também qualquer cabo cujo ID esteja na lista de vinculados
(metadata). Corrigido em dois pontos que faziam essa consulta
separadamente — `_payload()` (usado pela listagem/GET) e o dispatcher
de ações no topo de `dio_fusion_matrix_v07537` (usado por
`attach_cable`, `detach_cable`, `auto_fuse`, `create_fusion`) — os
dois tinham a mesma query restrita demais, cada um com sua própria
cópia.

## "Auto fusão" não funcionava

Era exatamente o mesmo bug acima, só que mais visível: sem o cabo
aparecendo na lista "CABOS VINCULADOS", não tinha como selecioná-lo, e
`autoFuse()` sempre respondia "Selecione um cabo para a auto fusão."
Mesmo simulando a seleção diretamente, a ação em si batia em "No
FiberCable matches the given query." — porque o dispatcher de ações
tinha a mesma consulta restrita que a listagem, só que numa cópia
separada do código, então corrigir só a listagem não bastava.

Confirmado ao vivo: depois da correção, "Auto fusão" criou as 12
fusões corretamente a partir de um cabo vinculado só por metadata (sem
origin/destination apontando pro Rack) — o cenário exato do bug.

## Só 10-11 das 12 fibras apareciam na matriz

`repeat(12, 30px) !important` — regra que **parecia** estar num
arquivo, mas na verdade a que vencia de verdade estava em
`map-rack-maintenance-v07549.css` (carrega depois de
`map-dio-fusion-v07538.css`, mesmo seletor + `!important`, mesmo
padrão de cascata que já apareceu nesta série de hotfixes do DIO).
Largura fixa nunca encolhe — numa coluna "CABOS VINCULADOS" com só
~370px reais disponíveis (12×30px + 11 gaps de 5px passa de 410px), as
últimas 1-2 fibras ficavam cortadas por baixo do `overflow: hidden` do
card, embora existissem normalmente no DOM.

**Correção**: `repeat(12, 1fr)` sem nenhum mínimo fixo — sempre cabe,
encolhendo cada fibra o quanto precisar. Confirmado ao vivo:
`getBoundingClientRect` do último botão antes/depois (borda direita em
586px, além do card que termina em 516px → agora em 505px, dentro do
card) e screenshot com as 12 fibras numeradas visíveis numa linha só.

## Validação

- `tests/test_map_v07561_contract.py` (novo, 4 testes).
- Suíte histórica completa — zero regressões novas.
- Validação real no navegador (Playwright, ambiente Docker isolado):
  cenário reproduzido exatamente como o bug real (cabo sem
  origin/destination, vinculado só por metadata) — cabo aparece na
  lista, Auto fusão cria as 12 fusões, todas as 12 fibras visíveis
  numa linha, testado de ponta a ponta depois de cada correção
  individual e no fluxo completo junto.
- Nenhuma migration, `PLATFORM_VERSION` inalterada.

## Ainda pendente (fora desta rodada)

- Duplo clique numa porta fundida da matriz pra "Remover fusão" —
  já existe no código (`handleWorkspaceDoubleClick`), não
  revalidado ao vivo nesta rodada.
- Organizador de cabo entre as portas de uplink e de serviço no
  Switch.
- Portas do Switch empilhadas na Torre e "risco azul" Rack→Torre —
  aguardando inspeção via DevTools do usuário (não reproduzidos com
  dados sintéticos nem com os dados reais checados, só leitura).
