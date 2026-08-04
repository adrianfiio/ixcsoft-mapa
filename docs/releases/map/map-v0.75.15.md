# MAP v0.75.15 — alça do fio, cordão OLT→DIO, OLT redimensionável

## Objetivo

Corrigir problemas concretos reportados após teste real da v0.75.14, com
prints de DevTools reais anexados pelo usuário.

## Alça do fio

`fill: transparent` num `<circle>` SVG depende do valor computado de
`pointer-events` (padrão `visiblePainted`) pra decidir se conta como
"pintado" — em alguns motores de renderização um preenchimento com alpha 0
não conta, deixando o centro exato sem resposta ao clique mesmo com uma
área de clique maior por cima da bolinha. Corrigido forçando
`pointer-events: all` explicitamente no elemento de clique, removendo
qualquer dependência da cor de preenchimento.

## Cordão OLT → DIO

O trecho vertical que desce da porta de origem até abaixo da placa inteira
usava sempre a coordenada X da própria porta — se houvesse outra porta na
mesma coluna numa linha abaixo dentro da mesma placa (ex.: PON 13/1 na
linha 1 e PON 13/9 na linha 2, mesma coluna), a descida reta passava por
cima dela. Corrigido: antes de descer, o roteador procura uma coluna livre
de portas irmãs da mesma placa (usando o mesmo mecanismo de desvio de
obstáculo já usado no roteamento genérico desde a v0.75.13), então desce
por ali.

## OLT

- Removidos os slots utilitários do chassi (módulos vazios "MÓDULO",
  fontes "PWR") importados do YAML do fabricante — só as placas de serviço
  (PON/uplink) aparecem no Canvas agora.
- Grade de portas de cada placa deixa de ser fixa em 2 colunas
  (`grid-template-columns: repeat(2, ...)`) e passa a ser fluida
  (`repeat(auto-fill, minmax(140px, 1fr))`) — quantas portas cabem lado a
  lado depende só da largura disponível do card.
- Nova alça de redimensionar na lateral direita do card da OLT: arrastar
  aumenta ou diminui a largura (420px–2200px), persistida por equipamento
  em `container_layout_v3` (chave nova `nodeWidths`, mesmo endpoint já
  existente, sem migration).

## Investigado, não resolvido nesta versão

### PTP — erro 500 em `/api/map/ptp-links/candidates/`

Print do usuário mostra `GET .../ptp-links/candidates/?source_port_id=...`
retornando HTTP 500 ao confirmar "Ligar PTP?". Revisei linha a linha
`ptp_link_candidates`, `_busy_port_ids`, `can_view_company`, os campos do
model `ContainerEquipment`/`ContainerEquipmentPort` e os imports do
arquivo — nada indica a causa por leitura estática. Encontrei e descartei
uma falsa pista (uma leitura de grep exibiu barras invertidas numa URL que
na verdade estão corretas no arquivo real, confirmado com leitura direta).

**Preciso do traceback real do servidor** para prosseguir com segurança —
rodar no Debian, no momento do erro ou logo depois:

```bash
docker logs ixcsoft-mapa-web-1 --tail 100
```

e me mandar a saída (ou pelo menos o traceback Python do erro 500).

### CTO/CDO/CEO — ainda no editor antigo

A modernização visual (CSS) da v0.75.14 não resolveu o pedido: o usuário
quer o mesmo Canvas 2D do Rack/Torre reaproveitado para CTO/CDO/CEO, não
uma repintura do editor de fusões (`#unifilar-dialog` /
`.optical-graph`) que já existe. Investigação confirmou que o editor atual
já é funcional (nós arrastáveis, clique-para-ligar cabo/splitter/porta),
mas sua renderização está inteiramente dentro de `showUnifilar()`
(`map-editor.js`), com seletores dependentes espalhados por mais 4
arquivos (`map-optical-editor-v2.js`, `map-optical-editor-v3.js`,
`map-fusion-polish.js`, `map-v0750-tower-workspace.js`). Substituir isso
pelo Canvas real é do tamanho de uma versão inteira, não uma correção —
fica para uma entrega própria, como já combinado para o item da
"Organização Rack" 44U.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations. `nodeWidths` é só uma chave nova dentro do JSON já livre
  de `container_layout_v3` (`NetworkElement.metadata`).
- Nenhum endpoint de API alterado nesta versão.
