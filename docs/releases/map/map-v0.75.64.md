# MAP v0.75.64

Hotfix: barra visual organizadora na grade de portas do Switch,
dividindo-a ao meio (entre a área de uplinks e a de serviço) — mesma
ideia visual que a OLT já tinha pros uplinks, agora também no Switch.

## Contexto

Pedido original do usuário: "entre as portas uplink e das serviços
criar 1 organizador tbm para passar cabo". Como o Switch, diferente da
OLT, não tem hoje nenhum tipo de porta "uplink" vs "serviço" no modelo
de dados (é um grid único, todas as portas iguais), perguntei ao
usuário o que ele queria dizer com "organizador" nesse caso —
resposta: **"Só uma barra visual dividindo a grade ao meio"**. Ou
seja: puramente cosmético, sem criar um tipo de porta novo nem mexer
no formulário/modelo de criação do Switch.

## Correção

`static/js/map-rack-switch-v07552.js`, `renderSwitchFace()`: depois de
montar todos os botões de porta reais, adiciona um `<div
class="v07564-switch-half-divider">` como último filho da grade
(`.v07552-switch-ports`), só quando há mais de 1 porta.

`static/css/map-rack-runtime-v07552.css`: a divider fica com
`position: absolute; left: 50%` e `pointer-events: none` — fora do
fluxo do CSS Grid, então não desloca, reordena nem redimensiona
nenhuma porta real (o grid continua contando só com os itens de porta
de verdade). `.v07552-switch-ports` ganhou `position: relative` pra
servir de referência de posicionamento pra essa barra.

## Validação

- `tests/test_map_v07564_contract.py` (novo).
- Suíte histórica completa — zero regressões novas.
- Validação real no navegador (Playwright, ambiente Docker isolado):
  Switch com portas renderizadas, barra tracejada visível dividindo a
  grade ao meio, nenhuma porta perdeu posição/numeração/link.
- Nenhuma migration, `PLATFORM_VERSION` inalterada.

## Ainda pendente (fora desta rodada)

- Portas do Switch empilhadas na Torre e "risco azul" Rack→Torre —
  aguardando inspeção via DevTools do usuário.
