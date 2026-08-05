# MAP v0.75.38

## Ajustes desta atualização

### Rack e DIO
- O ponto agregado do cabo no Rack foi reposicionado para a esquerda do cartão do cabo.
- O traçado temporário de arraste e o redesenho das associações Rack → DIO usam `requestAnimationFrame`.
- O DIO continua com matriz própria de fusões, mantendo a frente livre para a topologia com OLT.

### OLT compacta
- A OLT compacta ganhou largura alternável para facilitar a leitura dos números das portas.
- O layout mantém slots em linha e até 16 portas por slot.

### CEO, CDO e CTO
- Caixas de distribuição passam a desenhar um divisor central pontilhado para indicar entrada à esquerda e saída à direita.
- Cabos verticais respeitam o lado do bloco: à esquerda recebem legenda de entrada, à direita recebem legenda de saída.
- Splitters permanecem centralizados e as conexões continuam separadas entre fusões cabo ↔ cabo e ligações de splitter.

### UX do editor
- O painel de cabos próximos explicita a captura máxima de 5 metros.
- O editor continua sem `alert`, `prompt` ou `confirm` nativos.

## Sem migração
- Nenhuma migration foi adicionada.
- O endpoint de matriz do DIO permanece o mesmo da v0.75.37.
