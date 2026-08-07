# MAP v0.75.62

Hotfix no Rack: o cabo deixa de aparecer como um card/widget separado
no Canvas 2D — passa a existir só dentro da Matriz de Fusão, a pedido
direto do usuário.

## O que mudou

`renderContainerCanvas()` (`map-master-suite.js`) renderizava, pra
qualquer container (Rack ou Torre), um `<article class="master-cable-node">`
por cabo associado — um card com as fibras coloridas individuais e um
ponto arrastável até um DIO. No Rack, isso duplicava o que a Matriz de
Fusão já resolve sozinha (botão "+ Vincular", direto na matriz).

**Correção**: quando `state.container.data.container.type === "rack"`,
a lista de cabos passada pro render vira vazia — nenhum
`.master-cable-node` é criado. A Torre continua exatamente igual (o
pedido foi só sobre o Rack). O resumo compacto "CABOS · X
vinculado(s)" que já existia dentro do próprio card do DIO continua
aparecendo normalmente — não é a mesma coisa que o widget removido, e
o usuário não pediu pra tirar isso.

## Agrupamento por tubo de 12 (já funcionava, só confirmado)

O usuário pediu: "todo cabo é de 12 em 12 — se adicionei 12, tem que
aparecer as 12; se for 24, aparecer 12 e embaixo mais 12, relacionado
ao cabo". Essa lógica (`fiberGroups`, agrupando por `FiberTube`) já
existia no código — cada tubo de 12 fibras vira sua própria linha
("T1", "T2", ...) dentro do card do cabo na matriz. O que faltava era
só o fix da v0.75.61 (que garantia as 12 fibras de cada tubo visíveis
numa linha, sem cortar). Testado ao vivo com um cabo de 24F: T1 com
fibras 1-12, T2 embaixo com 13-24, os dois dentro do mesmo card do
cabo certo.

## Validação

- `tests/test_map_v07562_contract.py` (novo, 2 testes).
- Suíte histórica completa — zero regressões novas.
- Validação real no navegador (Playwright, ambiente Docker isolado):
  Rack com 2 cabos vinculados (12F e 24F) — nenhum widget no canvas
  (0 `.master-cable-node`), os 2 cabos aparecem normalmente na matriz,
  o cabo de 24F mostra exatamente T1 (1-12) + T2 (13-24).
- Nenhuma migration, `PLATFORM_VERSION` inalterada.

## Ainda pendente (fora desta rodada)

- Duplo clique numa porta fundida da matriz pra "Remover fusão" — já
  existe no código, não revalidado ao vivo nesta rodada.
- Organizador de cabo entre as portas de uplink e de serviço no
  Switch.
- Portas do Switch empilhadas na Torre e "risco azul" Rack→Torre —
  aguardando inspeção via DevTools do usuário.
