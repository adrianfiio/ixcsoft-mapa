# MAP v0.75.45

## Chassi de OLT por slots

- O cadastro da OLT passa a pedir o modelo do chassi, a orientação física das placas e a quantidade de slots de serviço.
- Chassis verticais exibem os slots lado a lado.
- Chassis horizontais exibem os slots um sobre o outro.
- Os slots nascem vazios e nenhuma porta PON é criada na inclusão do chassi.

## Instalação de placas

- Duplo clique ou botão direito em um slot abre o editor da placa.
- Cada placa registra nome, modelo, tecnologia GPON/XG-PON/XGS-PON e quantidade de portas.
- As portas são criadas somente quando a placa é instalada.
- Alterar a quantidade ou remover uma placa conectada é bloqueado até as portas serem desligadas.

## Navegação

- Zoom continua sendo feito pela roda do mouse.
- O Canvas pode ser arrastado pela área vazia com o botão esquerdo ou pelo botão central.
- O pan usa eventos globais para não parar quando o ponteiro sai da área original.

## Uplinks

- Uplinks não fazem parte desta rodada.
- Novas OLTs são criadas sem grupos de uplink.
- Dados legados não são apagados automaticamente.

## Compatibilidade

- DIO, organizadores, calhas e roteamento traseiro foram preservados.
- Nenhuma migration foi adicionada.
