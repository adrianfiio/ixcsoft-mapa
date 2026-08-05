# MAP v0.75.40

## Rack físico e roteamento por calhas

- O Rack deixa de ser um Canvas totalmente livre e passa a usar representação física em unidades U.
- Equipamentos são posicionados dentro do gabinete e travados no local calculado por `rack_unit` e `height_units`.
- Equipamentos sem posição cadastrada recebem organização determinística sem gravação automática no banco.
- Calhas laterais passam a conduzir os cordões frontais e o barramento traseiro conduz cabos externos.
- Ligações internas começam exatamente no ponto visual da porta, inclusive nas portas PON da OLT.
- Linhas deixam de atravessar os equipamentos; o trajeto é ortogonal pela calha lateral mais próxima.
- Cabos externos usam um tronco traseiro por cabo e derivações curtas até os DIOs vinculados.

## Correção de duplicações

- Corrigidos três atributos `data-*` inconsistentes do runtime v0.75.38 que recriavam controles a cada renderização.
- Cada cabo passa a exibir somente um resumo agregado.
- Cada DIO passa a exibir somente um alvo `CABOS` e somente um botão `Fusões`.
- Uma segunda proteção remove nós e controles visuais duplicados pelo mesmo ID em Rack e Torre.

## Torre

- A Torre continua com layout livre.
- A normalização de duplicações também é aplicada na Torre, incluindo cartões de DROP.

## Compatibilidade

- Mantida a matriz de fusões e o backend da MAP v0.75.39.
- Nenhuma migration.
- Nenhum endpoint novo.
