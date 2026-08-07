# MAP v0.75.60

Hotfix: bolinha do DIO (OLT/PON) maior e realmente centralizada dentro
do quadrado — a pedido direto do usuário ("tem que clicar bem na
bolinha, deixa ela maior e mais no meio").

## Tamanho

Bolinha: 20px → 28px. Quadrado: 44px → 52px. Mantém margem visível ao
redor, mais fácil de acertar o clique.

## Causa raiz da má centralização

Medindo de verdade no navegador (`getBoundingClientRect`, não só lendo
CSS), a bolinha ficava ~10px abaixo do centro do quadrado mesmo com
`place-items: center` no grid do quadrado — o que deveria bastar
sozinho.

Achado: `.master-node-port i` (`map-master-suite.css:669-677`) é a
regra genérica que estiliza a bolinha de status de **qualquer** porta
do sistema (Switch, OLT, etc.) — usa o truque clássico de centralização
via `position: absolute; top: 50%; transform: translateY(-50%)`.

A bolinha do DIO virou `position: relative` na v0.75.58, pra resolver
o bug onde o `::before` de área-de-clique do quadrado roubava todo
clique nela. Só que `top`/`transform` daquela regra antiga não foram
zerados junto — e pra `position: relative`, `top` deixa de ser "âncora
absoluta" e vira um deslocamento relativo de verdade a partir da
posição normal. O resultado: a bolinha continuava sendo empurrada pra
baixo por um cálculo que só fazia sentido pra `position: absolute`.

**Correção**: `top: auto !important; transform: none !important;` na
`.v07558-dio-dot`, deixando o `place-items: center` do quadrado
centralizar sozinho, sem interferência.

## Validação

- `tests/test_map_v07560_contract.py` (novo, 2 testes).
- Suíte histórica completa — zero regressões novas.
- Validação real no navegador (Playwright, ambiente Docker isolado):
  `getBoundingClientRect` confirma `centered: true` (antes: `false`,
  offset de 10px); screenshot de zoom confirma visualmente; reteste do
  clique independente bolinha/quadrado (desligar só a frente, sem
  afetar a fusão) continua funcionando com o novo tamanho.
- Nenhuma migration, `PLATFORM_VERSION` inalterada.
