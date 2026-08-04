# MAP v0.75.10 — Canvas, DIO, OLT modular e YAML

## Base

- Commit obrigatório: `48ad1b74611f35795f6e7a000f1aa4eec24ef436`
- Plataforma preservada: `0.82.0`
- Mapa: `0.75.10`
- Sem migrations.

## Correções

- Corrige o colapso do Canvas de Rack/Torre: o header nativo estava oculto, mas o grid ainda reservava uma linha `auto`; o workspace ficava com 52 px e o painel visual com altura zero.
- Bloqueia o menu global quando o botão direito ocorre sobre o rótulo permanente de um marker.
- Após importação YAML, recarrega a estrutura pelo ponto de entrada único `mapMasterSuite.openContainerWorkspace`.

## DIO

- DIOs com mais de 24 portas deixam de paginar em blocos de 24.
- Todas as portas ficam visíveis em bandejas de 12 posições.
- Cada bandeja possui corredor vertical para traçar ligações sem sobrepor a bandeja seguinte.
- As faces traseira e dianteira continuam sendo conectores distintos.

## Cabos

- Cards de cabo passam para formato vertical no Canvas de Rack/Torre.
- O workspace óptico aplica o mesmo formato vertical aos cabos.
- Entrada/saída, cores e estado das fibras são preservados.

## YAML e OLT

- Expande intervalos como `PON 13/[1-16]` e `ETH 19/[1-5]`.
- Preserva `manufacturer`, `model`, `slug`, `u_height`, `is_full_depth`, `comments`, `power-ports`, `module-bays` e agrupamento por slot/placa.
- Detecta OLT quando há conjunto de portas PON/chassi OLT.
- A OLT importada é desenhada como chassi modular, com módulos, alimentação, slots e grupos de portas.
- O Rack continua bloqueando AP, PTP e ONU/ONT no importador.

## Editor óptico

O motor de fusões existente é preservado para não arriscar dados. A interface passa a ocupar o workspace amplo e recebe cards verticais de cabo. A entrega não cria um segundo motor de fusões nem duplica chamadas de API.

## Homologação

1. Torre 9102: 5 equipamentos, 2 cabos e 2 notas visíveis.
2. Rack 9106: DIO 01 e cabo visíveis.
3. Criar DIO 48/72/96/144 no Rack e conferir bandejas de 12.
4. Importar `reference/fiberhome-an5516-06-imbau.yaml` e conferir 49 portas expandidas e agrupadas.
5. Botão direito no ícone e no rótulo não pode abrir dois menus.
6. CTO 9103 e CDO 9105 devem abrir fusões em workspace amplo.
7. Console sem exceções e Network sem loops.
