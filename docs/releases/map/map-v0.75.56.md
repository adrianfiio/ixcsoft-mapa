# MAP v0.75.56

Hotfix: ordem de equipamento no Rack, cores das portas do DIO, edição de
rota de cabo e corte de cabo em passagem nas caixas CTO/CDO/CEO. A
partir de duas telas que o Adrian mostrou (um switch montado no Rack e o
editor de um DIO 36F) e uma lista de comportamentos desejados.

## 1. Equipamento adicionado depois pulava pro topo do Rack

**Causa raiz**: `priority()` (`static/js/map-rack-physical-v07542.js`)
dava prioridade fixa por tipo (`olt: 1, dio: 2, switch: 3, router: 4,
firewall: 5`), usada por `buildAssignments()` pra ordenar equipamento
sem posição explícita antes de preencher o rack de cima pra baixo. Como
OLT sempre vencia esse critério, ela sempre caía no topo — os outros
tipos só empilhavam na ordem certa porque empatavam na prioridade e
caíam no desempate por ordem de criação (`a.id - b.id`).

**Correção**: `priority()` agora devolve o mesmo valor pra todo mundo,
deixando a ordem de criação decidir sempre, pra qualquer tipo.

**Reposicionar manualmente**: já existia (arrastar um equipamento pra um
slot vazio reposiciona livre; arrastar pra cima de outro troca os dois
de posição) — não precisou de nada novo, só confirmado que continua
funcionando.

## 2. Portas do DIO: borda = fusão, bolinha = PON

O backend já mandava exatamente o dado certo por par de porta (`front` =
ligação PON, `rear` = fusão) — nenhuma mudança de backend. O lado de
trás já colorava certo (vermelho sem fusão, laranja com fusão). Só a
frente estava errada: a bolinha seguia a cor do tipo de conector, não o
estado da PON.

**Correção**: a bolinha da frente agora é vermelha sem PON ligada e
verde com PON ligada; a borda da frente continua pela cor do conector
(informativo, não removido). Formato quadrado não mudou — já estava
correto.

## 3. Cabo: clique esquerdo não faz nada, botão direito com "Editar rota"

Antes, todo cabo tinha um popup vinculado que o Leaflet abria em
qualquer clique esquerdo. A edição de rota completa (arrastar qualquer
ponto do traçado, não só inserir um vértice) já existia
(`startGeometryEdit`), só estava enterrada 3 cliques atrás (popup →
Editar/conectar → diálogo → botão "editar geometria"), e o traçado em
edição era uma linha sólida.

**Correção**: popup removido — clique esquerdo simples não abre mais
nada (os fluxos de "+ Reserva"/"+ CTO/CEO" com ferramenta armada
continuam reagindo ao clique esquerdo normalmente, não dependiam do
popup). Botão direito agora mostra um menu com "Editar rota" no topo
(cai direto no modo de edição, sem passar pelo diálogo) mais as ações
que já existiam (Editar/conectar, +Reserva, +CTO/CEO, Excluir) — nada
foi removido, só mudou de lugar. O traçado em edição agora fica
tracejado.

## 4. CTO/CDO/CEO: "Realizar corte" pra cabo em passagem

Já existia quase tudo: endpoint de corte seguro
(`cut_cable_at_element`), detecção de proximidade (já uma consulta por
caixa, filtrada por empresa/projeto, raio de 5m — não varre todas as
caixas, então já atende à exigência de performance com dezenas de
milhares de caixas sem trabalho extra), e o painel "Cabos" da própria
caixa já mostrava a etiqueta "corte necessário". Só faltava o botão que
realmente dispara o corte.

**Correção**: botão "Realizar corte" adicionado no painel de cabos da
caixa (ao lado da etiqueta já existente) e no menu de botão direito do
canvas (os cabos já eram hit-testáveis lá, não precisou de geometria
nova). Mesmo padrão de confirmação já usado nas outras ações
destrutivas da tela. Erros do backend (cabo já com fusão, etc.) já
chegam prontos pro usuário pelo tratamento de erro existente.

## Validação

- `python -m py_compile` — nenhum arquivo Python tocado neste hotfix
  (só JS/CSS).
- Balanceamento de chaves/parênteses/colchetes nos 8 arquivos JS/CSS
  tocados.
- `tests/test_map_v07556_contract.py` (novo, 8 testes).
- Suíte histórica completa, rolling-bump dos testes que travam "versão
  atual".
- Validação real no navegador (Playwright, ambiente Docker isolado no
  servidor, produção nunca tocada) cobrindo os 4 itens, ver seção
  própria no relatório desta rodada.

## Fora de escopo

- Layout de portas fiel ao desenho real de cada modelo de equipamento
  (ex.: 12 RJ45 numa linha + 1 RJ45 + 4 SFP+ na linha de baixo, como um
  Mikrotik CCR2116) — fica pra uma rodada futura, quando tivermos um
  catálogo de modelos conhecidos. Hoje o sistema só tem 1 grid único por
  equipamento, sem conceito de linha/grupo de porta.
- Nenhuma migration, `PLATFORM_VERSION` inalterada.
