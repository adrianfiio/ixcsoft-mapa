# MAP v0.75.22 — CTO/CDO: paridade visual forçada + splitter em grade 2 colunas

## Objetivo

Corrigir o gap visual reportado pelo usuário: a tela de fusões da CTO/CDO
ainda aparecia no "formato antigo" (lista vertical simples de fibras,
splitter sem o visual do Canvas 2D), bem diferente do editor da Torre.

## Investigação

- O dual-classing feito na v0.75.20 (`master-canvas-node` nos nós de
  splitter/cabo) usava propriedades **sem** `!important`. Como
  `map-editor.css` (dono do `.fiber-cable-node`/`.graph-splitter-node`
  antigos) e `map-master-suite.css` (dono do `.master-canvas-node`) têm
  a mesma especificidade de seletor, o resultado final dependia
  inteiramente da ordem de carregamento dos dois arquivos — frágil.
- Confirmado, lendo `apps/network_map/cto_defaults.py`, que o pedido
  "CTO já adicionar direto o splitter com as portas de atendimento aos
  clientes como tem hoje" **já é o comportamento atual**:
  `ensure_cto_default_splitters()` roda tanto na criação manual de uma
  CTO quanto na importação de KMZ, decompondo a capacidade em splitters
  balanceados e já criando as portas de saída.
- Confirmado, lendo `centerWithin()` em `static/js/map-editor.js`, que o
  pedido "o que vem à esquerda, o que sai à direita, se inverter no
  diagrama inverte os cabos" **também já existe** para os nós de cabo:
  a cada redesenho das linhas, cada nó de cabo recebe a classe
  `side-left-v0758` ou `side-right-v0758` conforme sua posição X atual
  em relação ao centro do quadro, e isso já controla de qual borda o
  ponto de fusão sai (usado tanto no desenho das linhas quanto no
  `map-v07512-links-ptp.js`). Não havia nada a construir aqui — só
  precisava do resto do visual acompanhar.

## O que mudou

- `static/css/map-v0758-core-ui.css`: bloco `MAP_V07522_CTO_LEFT_RIGHT`
  reforça com `!important` o fundo/borda/raio/sombra do
  `.master-canvas-node` nos nós de splitter e cabo, garantindo a
  aparência do Rack/Torre independente da ordem de carregamento dos
  CSS.
- Saídas do splitter (`.splitter-output-grid`) passam de uma coluna
  única (lista vertical) para uma grade de 2 colunas — mesma leitura
  visual esquerda=entra (ENT)/direita=sai do DIO, mais compacta.
- **Nenhuma linha de JavaScript mudou** — só CSS. Toda a lógica de
  clique-para-ligar, arraste, criação de fusão e roteamento permanece
  idêntica (confirmado via `tests/test_map_v07522_contract.py`).

## O que NÃO foi feito nesta versão (próxima fatia)

- Uma "caixa" física de CTO/CDO no diagrama — hoje splitter e cabos
  continuam sendo nós independentes ligados por linha, não um chassi
  único hospedando portas à esquerda/direita como o DIO da Torre.
  Construir isso é o próximo passo real de paridade completa, e será
  feito em fatia própria, testável ao vivo (mesmo acordo de "só
  aditivo, devagar" já combinado com o usuário).

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhum endpoint de API alterado.
- Nenhum arquivo JavaScript alterado nesta versão — só CSS puro.
