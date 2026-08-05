# MAP v0.75.48

## Rack vazio
- O gabinete físico, calhas e cartões de cabos ficam ocultos enquanto não houver OLT, DIO ou Switch no Rack.
- O estado vazio permanece com os atalhos para criar os três equipamentos principais.

## Cadastro e edição da OLT
- O formulário inicial pede apenas identidade do chassi, disposição, slots de serviço e slots de uplink.
- PONs deixam de ser criadas no cadastro do chassi; cada placa define sua própria quantidade.
- O editor da OLT permite ampliar a quantidade de slots sem recriar o equipamento.
- Placas podem ser instaladas ou editadas por slot.
- Em modo manual, cada PON pode receber potência TX individual.

## DIO e cabos
- As portas do DIO deixam de exibir textos apertados; detalhes permanecem em tooltip e no botão direito.
- A linha do cabo traseiro termina no centro da porta do DIO.
- A topologia persistida passa a alimentar o desenho do cabo no Rack.

## Caminho óptico
- Cada PON possui ação para destacar o caminho conhecido OLT → DIO → cabo.
- O painel mostra potência TX, perdas conhecidas e potência estimada após o DIO.
- O evento `map:optical-path-highlight` permite que o mapa e outros módulos acompanhem o mesmo caminho.

## Estabilidade
- O módulo `map-v0758-core-ui.js` passa a tolerar raízes DOM ausentes.
- Chamadas herdadas de fusões em Rack são ignoradas localmente, evitando HTTP 400, e POSTs idênticos de ligação em voo são deduplicados para não gerar HTTP 409.
- PTO e Outro deixam de aparecer no menu de inclusão do Rack.
- Nenhuma migration foi adicionada.
