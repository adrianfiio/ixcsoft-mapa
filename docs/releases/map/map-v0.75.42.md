# MAP v0.75.42

## Rack 19 polegadas mais compacto
- A largura visual do gabinete passa a seguir a face padrão de 620 px dos equipamentos 19".
- OLT, DIO, Switch, Roteador e Firewall usam a mesma largura interna.
- A altura do Rack é calculada pela ocupação real, sem abrir 42U vazias por padrão.
- Equipamentos continuam móveis no eixo vertical com encaixe em U.

## Organizadores e roteamento
- É reservado 1U entre equipamentos para organizadores horizontais.
- Cordões frontais usam calhas laterais e o organizador mais próximo entre origem e destino.
- Cabos externos continuam usando um único tronco traseiro por cabo.
- As derivações para o DIO chegam pela lateral da cavidade correspondente e podem usar ambos os lados.

## DIO no padrão do Rack
- O DIO recebe a mesma largura da OLT.
- As cavidades permanecem separadas em grupos de 12 portas.
- Organizadores ópticos são desenhados entre as cavidades.

## Switch moderno
- O cadastro antigo do Rack é substituído por um modal próprio.
- Switch solicita nome, fabricante, modelo, IP de gerência e quantidade de portas.
- As portas são criadas no backend e desenhadas em até 12 por linha.
- Switches de 12 portas usam uma linha; switches de 24 usam duas linhas de 12.

## Tipos permitidos
- Rack aceita OLT, DIO, Switch, Roteador e Firewall.
- PTO, ONU/ONT, Rádio PTP, Access Point e Outro deixam de aparecer no cadastro do Rack.
- Esses tipos continuam disponíveis onde fizerem sentido, especialmente na Torre.

## Zoom
- No Rack, a roda do mouse controla diretamente o zoom, sem exigir Ctrl.
- Os botões de aumentar, diminuir e ajustar continuam disponíveis.
- O pan pelo botão central fica desativado no Rack.

## Compatibilidade
- Nenhuma migration foi adicionada.
- O endpoint existente da v0.75.39 continua sendo usado.
