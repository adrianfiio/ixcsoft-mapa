# MAP v0.75.47

## Navegação do Rack

- O botão esquerdo passa a mover a visualização do Rack ao ser segurado e arrastado em áreas não interativas.
- O pan mantém exatamente o zoom atual; a escala só muda pela roda ou pelos botões de zoom.
- O novo controlador intercepta os handlers antigos antes que eles disputem os mesmos eventos.

## Chassi da OLT

- O cadastro inicial da OLT pede somente disposição física, slots de placas de serviço e slots de uplink.
- O campo PONs por slot foi removido do cadastro inicial.
- Os slots de serviço nascem vazios; as portas PON só são criadas ao instalar uma placa pelo slot.
- Os slots de uplink são apenas reservas vazias nesta versão. A instalação das placas de uplink ficará para uma etapa posterior.

## Portas PON

- O número da PON aparece acima do ponto visual de conexão.
- O ponto deixa de encobrir o número, especialmente nas portas de dois dígitos.

## Rack

- PTO e Outro deixam de aparecer no menu de inclusão do Rack.
- Nenhum equipamento existente é apagado.

## Compatibilidade

- Placas GPON, XG-PON e XGS-PON continuam sendo instaladas por duplo clique ou botão direito nos slots de serviço.
- DIO, fusões, cabos, organizadores e topologia permanecem inalterados.
- Nenhuma migration foi adicionada.
