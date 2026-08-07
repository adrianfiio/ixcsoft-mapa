# MAP v0.75.58

Hotfix: redesenho da porta do D.I.O pra 1 elemento só, a pedido direto
do Adrian com um mockup exato ("Painel D.I.O"). A v0.75.57 tinha
corrigido o CSS pra empilhar frente/trás (não mais lado a lado), mas
isso ainda lia como "2 portas" — o pedido real sempre foi 1 elemento
por porta física, com 2 funções dentro dele.

## Causa raiz das duas rodadas anteriores não resolverem

A v0.75.56/v0.75.57 mantiveram o modelo de 2 `<button>` por porta
(frente + trás), só mudando como eles se posicionavam um em relação ao
outro (lado a lado → empilhado). Isso nunca ia satisfazer "aparecer
como 1 porta só" — o problema não era posição, era ter 2 elementos.

## O que mudou

Cada porta física do D.I.O agora é **1 `<button>` só**:

- **O quadrado** (o `<button>` em si, `data-port-role="rear"`): clique
  liga/desliga a fusão com o cabo da rua. Vermelho = desconectado,
  laranja = fundido.
- **A bolinha central** (uma `<i>` aninhada dentro do quadrado,
  `data-port-role="front"`): clique liga/desliga a porta da OLT/PON.
  Preta = desconectada, azul = conectada.

Essas são as MESMAS duas ligações de sempre (front = cordão pra
equipamento/OLT, rear = fusão/terminação do cabo da rua) — só a
apresentação visual mudou, de "2 quadrados" pra "1 quadrado com 1
bolinha dentro".

**Cor por tipo de conector removida**: a v0.75.56 tinha corrigido a
bolinha da frente pra refletir estado de PON (verde/vermelho) mantendo
a borda colorida por tipo de conector (SC/APC verde, SC/UPC azul). O
novo mockup não previa isso — o quadrado agora é só sobre fusão, a
bolinha só sobre OLT/PON, sem uma terceira dimensão de cor pro
conector.

## Cliques independentes dentro do mesmo elemento

Como a bolinha vive DENTRO do quadrado no DOM, um clique nela também
"borbulha" pro quadrado por padrão — sem cuidado, isso dispararia as
duas ações no mesmo clique. Dois ajustes garantiram que continuassem
independentes:

1. O handler de clique em `data-port-id` (que finaliza a
   ligação/seleção de porta) agora corta a propagação do evento depois
   de tratar o alvo certo, então um clique na bolinha não repete a
   ação no quadrado ancestral.
2. O handler de "desligar porta já ligada" (que roda antes, na fase de
   captura do clique) achava o ancestral mais próximo com link-id
   preenchido — isso fazia um clique na bolinha *livre* "vazar" pro
   link do quadrado, se o quadrado já tivesse fusão feita. Corrigido
   pra achar sempre o elemento mais próximo do clique (bolinha ou
   quadrado, o que foi clicado de verdade) e checar o link-id dele
   mesmo, não do ancestral.

## Limpeza

`.v07539-dio-pair` e todo o CSS que só existia pra empilhar/posicionar
o par antigo (em `map-rack-runtime-v07552.css`,
`map-rack-maintenance-v07549.css` e `map-v07539-suite.css`) foi
removido por completo — não só esvaziado. As três rodadas anteriores
deixaram regra CSS morta espalhada por vários arquivos brigando entre
si; dessa vez a limpeza foi até o fim.

## Validação

- `tests/test_map_v07558_contract.py` (novo, 8 testes).
- Suíte histórica completa, rolling-bump dos testes que travam "versão
  atual" + 8 testes que testavam o markup antigo de 2 elementos
  atualizados pra refletir o novo desenho.
- Zero regressões novas (comparação via `git stash`, mesmo processo de
  sempre).
- Validação real no navegador (Playwright, ambiente Docker isolado no
  servidor, produção só recebe depois do merge): clique na bolinha liga
  porta da OLT sem afetar o quadrado; clique no quadrado liga fusão sem
  afetar a bolinha; nenhum duplo disparo ao clicar na bolinha; cores
  conferidas contra a especificação exata do mockup.
- Nenhuma migration, `PLATFORM_VERSION` inalterada.
