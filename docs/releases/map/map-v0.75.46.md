# MAP v0.75.46

## Navegação do Rack

- Um único runtime passa a controlar o zoom, o pan e os botões de ajuste do Canvas do Rack.
- Depois do zoom, o usuário pode arrastar o Rack para cima, para baixo e para os lados.
- O pan pode começar no gabinete, nos organizadores, nas áreas vazias dos equipamentos ou no fundo do Canvas.
- Portas, botões, campos e cabeçalhos de equipamento continuam reservados às suas ações próprias.
- O botão esquerdo usa um limiar de movimento para não transformar cliques normais em pan.
- O botão central inicia o pan imediatamente.

## Correção de conflito

Os handlers de navegação das versões v0.75.42 e v0.75.45 estavam ativos ao mesmo tempo. O primeiro capturava o `wheel` com `stopImmediatePropagation()`, impedindo o controlador mais novo de receber o evento. Além disso, o pan pelo botão esquerdo só começava fora de qualquer equipamento, embora o gabinete ocupasse praticamente toda a área visível.

A v0.75.46 carrega seu controlador antes dos runtimes antigos e desativa os dois handlers legados.

## Compatibilidade

- A movimentação dos equipamentos por unidades U foi preservada.
- O chassi, as placas, o DIO, as calhas e as conexões não foram alterados.
- Nenhuma migration ou endpoint foi adicionado.
