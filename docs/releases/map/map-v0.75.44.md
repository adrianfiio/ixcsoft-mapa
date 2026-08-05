# MAP v0.75.44

## OLT determinística

- O cadastro da OLT informa a quantidade exata de placas de serviço e de portas PON por placa.
- A face da OLT é reconstruída a partir das placas e portas persistidas, sem transformar cada PON em uma linha genérica.
- Uma OLT com 4 placas e 16 PONs apresenta exatamente quatro placas com dezesseis portas cada.

## Uplinks explícitos

- O cadastro permite informar zero ou mais grupos de uplink.
- Cada grupo possui nome, quantidade de portas e tipo físico RJ45 1G, SFP 1G ou SFP+ 10G.
- Zero grupos cria a OLT sem uplinks.
- Somente IDs registrados em `v07544_uplink_groups` são exibidos como uplinks.
- Portas antigas sem classificação explícita permanecem no banco, mas deixam de ser confundidas com uplinks.

## Navegação do Rack

- A roda do mouse ajusta o zoom ao redor do cursor.
- O arraste na área vazia altera a translação do Canvas, permitindo subir, descer e mover lateralmente mesmo após o zoom.
- O arraste de equipamentos pelo cabeçalho e o encaixe em unidades U permanecem separados da navegação.

## Rotas e organizadores

- Placas PON, grupos de uplink e cavidades do DIO mantêm organizadores locais.
- Cordões frontais e cabos traseiros continuam usando esses organizadores e as calhas laterais.

## Compatibilidade

- Nenhuma migration foi adicionada.
- As rotas da v0.75.43 permanecem disponíveis para compatibilidade, mas o frontend do Rack passa a carregar somente o runtime v0.75.44.
