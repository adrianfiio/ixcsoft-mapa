# MAP v0.75.43

## Navegação do Rack

- O Canvas do Rack volta a permitir deslocamento pela área vazia usando arraste com o botão esquerdo.
- A roda do mouse continua dedicada ao zoom e os botões de zoom/ajuste permanecem.
- Arrastar equipamentos pelo cabeçalho continua reservado ao encaixe em unidades U.

## Roteamento por organizadores

- As linhas frontais deixam de escolher um organizador global pelo ponto médio.
- Cada equipamento usa seu próprio organizador local antes de entrar na calha lateral.
- OLT e DIO recebem organizadores internos próprios.
- Cada cavidade do DIO passa a possuir um organizador abaixo dela, inclusive a última cavidade.
- Cabos externos chegam ao organizador da cavidade antes de entrar no DIO.

## OLT

- As duas últimas placas de serviço ficam agrupadas à esquerda da área inferior.
- Uma área física separada à direita passa a concentrar os uplinks.
- Uplinks aceitam RJ45 1G, SFP 1G e SFP+ 10G.
- Botão direito sobre um uplink abre o editor moderno da porta.
- Botão direito sobre uma placa de serviço permite registrar nome, modelo e tecnologia GPON, XG-PON ou XGS-PON.

## Barra superior

- Os botões redundantes `Ligar portas` e `Editar linhas` são removidos da interface do Rack.
- A criação de ligações continua sendo feita diretamente pelas portas.

## Compatibilidade

- Nenhuma migration foi adicionada.
- O endpoint novo usa os modelos existentes de equipamentos, placas, portas e ligações.
