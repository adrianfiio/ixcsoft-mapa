# MAP v0.75.49

## Rack vazio
- O cartão inicial e a ilustração da estrutura do Rack passam a usar o mesmo eixo e permanecem alinhados no centro do Canvas.
- O gabinete físico continua oculto enquanto não existir OLT, DIO ou Switch.

## Navegação
- O clique esquerdo segurado movimenta o Canvas mantendo o zoom atual.
- A roda do mouse altera somente o zoom.
- O botão central deixa de iniciar o pan.

## OLT e placas de serviço
- Clique comum em slot de serviço vazio abre a instalação da placa.
- Botão direito em slot instalado abre a edição.
- Depois de instalar uma placa, o editor permanece aberto, mostra as PONs criadas e permite informar potência TX por porta no modo manual.

## Placas de uplink
- Os slots de uplink ficam acima das placas de serviço.
- Cada slot aceita modelo da placa e configuração individual de portas RJ45 1G, SFP 1G ou SFP+ 10G.
- Portas RJ45/SFP 1G ligadas usam destaque verde; SFP+ 10G ligada usa destaque azul.
- Placas de uplink com portas conectadas não podem ser removidas ou remodeladas sem desligar as portas.

## DIO
- Frente e traseira ficam visualmente separadas.
- A frente usa a cor do conector: SC/APC verde e SC/UPC azul.
- Traseira sem fusão usa vermelho; traseira fundida usa laranja.
- As linhas terminam no centro dos pontos.

## Rack físico
- Alterações assíncronas de altura disparam novo cálculo do Rack.
- Sobreposições detectadas acionam a organização automática e o Rack cresce para baixo quando necessário.

## Matriz de fusão
- A matriz passa a usar largura máxima coerente com a última porta existente.
- Fibras deixam de esticar para ocupar toda a tela.
- Botões recebem acabamento visual mais compacto.
- O identificador incorreto do botão Desvincular cabo foi corrigido.

## Compatibilidade
- Nenhuma migration foi adicionada.
- Dados das versões anteriores são preservados.
