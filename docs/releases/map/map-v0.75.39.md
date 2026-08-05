# MAP v0.75.39

Atualização integrada dos 16 tópicos de Rack, DIO, OLT, PTO, ONU/ONT, DROP, CTO, CEO, CDO e cabos.

## DIO de dupla face

- A traseira recebe fusão de fibra ou terminação DROP.
- A frente recebe o cordão vindo da OLT ou de outro equipamento óptico.
- A mesma posição física pode ter traseira e frente ocupadas ao mesmo tempo.
- Traseira ocupada aparece em laranja; frente ocupada aparece em roxo.
- Romper um lado não remove o outro.

## Rack e OLT

- DIO organizado em cavidades de 12 posições.
- OLT compacta com largura persistente pequena, média, grande ou automática.
- Números continuam leves e tooltips preservam o nome completo da porta.

## PTO, ONU/ONT e DROP

- PTO apresenta entrada de fibra e saída SC/APC ou SC/UPC.
- ONU/ONT apresenta PON óptica, portas LAN e potência RX opcional.
- DROP pode terminar diretamente em DIO, PTO ou porta PON de ONU/ONT.

## Editor moderno de equipamentos

- Edição interceptada dentro do Canvas, sem reabrir o formulário legado.
- Campos diretos para nome, fabricante, modelo, serial, IP, SNMP, potência, conector, capacidades, LAN e observações.
- Novo equipamento também pode ser criado pelo botão do workspace.

## CTO, CEO e CDO

- Divisor central de entrada e saída.
- Cabos verticais em ambos os lados.
- Fibras em uma coluna vertical.
- Splitters no centro.
- Portas de atendimento da CTO permanecem separadas no painel lateral.

## Menu e painel dos cabos

- Informações, edição, inversão de sentido, associação/desassociação, CTO, CEO, CDO, reservas e exclusão.
- Painel reúne fibras, reservas, conexões, caixas, rota, comprimento, ocupação e orçamento óptico estimado.
- Reservas registram tipo, posição, responsável e observação.

## Persistência

- Layout óptico permanece no backend existente.
- Preferências adicionais usam `NetworkElement.metadata.map_v07539_layout`.
- Nenhuma migration foi adicionada.
