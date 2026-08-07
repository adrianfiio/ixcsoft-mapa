# MAP v0.75.63

Hotfix: duplo clique numa porta fundida da Matriz de Fusão pra
"Remover fusão" (`Romper fusão`) agora funciona de verdade — o código
já existia (`handleWorkspaceDoubleClick`), mas nunca disparava.

## Causa raiz

`handleWorkspaceClick` (o handler de clique simples) tratava clique em
QUALQUER porta, fundida ou não, da mesma forma: setava
`state.selectedPortId` e chamava `renderWorkspace()` — uma
reconstrução completa do DOM da matriz (`innerHTML`). Pra uma porta já
fundida isso não mudava nada de visível, era pura perda de trabalho.

O problema real: um duplo clique físico dispara, na ordem, `click`
(1º), `click` (2º), `dblclick`. Como o `click` do 1º disparo já
reconstruía o DOM inteiro no meio do caminho, o navegador deixava de
reconhecer os dois cliques como um duplo clique de verdade — o evento
`dblclick` simplesmente não chegava a disparar.

Confirmado ao vivo com um listener de diagnóstico direto no
`dblclick`/`click` do workspace: **0 de 2** eventos `dblclick`
registrados antes da correção (mesmo com 2 cliques reais físicos
acontecendo no mesmo ponto), **1 de 2** depois.

## Correção

`handleWorkspaceClick`: clique simples numa porta **já fundida** agora
não faz nada (`return` direto) — só o duplo clique
(`handleWorkspaceDoubleClick`, que já existia e já chamava
`deleteFusion`) trata essa porta. Porta livre continua com o
comportamento de sempre (seleciona a porta, ou cria a fusão se já
tinha uma fibra selecionada).

## Validação

- `tests/test_map_v07563_contract.py` (novo, 2 testes).
- Suíte histórica completa — zero regressões novas.
- Validação real no navegador (Playwright, ambiente Docker isolado):
  contagem de eventos `dblclick` capturados (0→1) e fluxo completo
  ponta a ponta — duplo clique na porta fundida, diálogo "Romper
  fusão" aparece, confirma, status vira "Fusão rompida.", porta volta
  a ficar livre (0 portas fundidas).
- Nenhuma migration, `PLATFORM_VERSION` inalterada.

## Ainda pendente (fora desta rodada)

- Organizador de cabo entre as portas de uplink e de serviço no
  Switch.
- Portas do Switch empilhadas na Torre e "risco azul" Rack→Torre —
  aguardando inspeção via DevTools do usuário.
