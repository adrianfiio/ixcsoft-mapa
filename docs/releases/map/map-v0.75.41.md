# MAP v0.75.41

## Correção do Rack físico

- Corrige o erro `Failed to execute 'closest'` causado pelo uso de um elemento DOM como seletor CSS.
- Equipamentos voltam a ser movimentáveis dentro do Rack pelo cabeçalho.
- O movimento é limitado ao eixo vertical e encaixa automaticamente em unidades U.
- Posições escolhidas são persistidas no layout existente do elemento.

## Prevenção de sobreposição

- Equipamentos com a mesma unidade U cadastrada deixam de ser desenhados um sobre o outro.
- O alocador procura a posição livre mais próxima.
- A altura visual é medida depois que a largura final do Rack é aplicada.
- O Rack usa 42U por padrão e cresce automaticamente até 96U quando o conteúdo exige.

## Operação

- Adicionado botão **Auto organizar** para descartar posições manuais e recalcular o encaixe.
- Calhas laterais, troncos traseiros e deduplicação de cabos/DROPs permanecem ativos.
- Torre continua no Canvas livre.

## Compatibilidade

- Nenhuma migration.
- Nenhum endpoint novo.
- Persistência reutiliza o endpoint de layout introduzido na MAP v0.75.39.
