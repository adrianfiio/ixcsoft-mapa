# MAP v0.75.35 — ligações diretas e Rack/DIO revisado

Base: MAP v0.75.34, merge commit `82371ad4463663ac59380246b1751af12ebbab18`.

## Editor da caixa óptica

- Interface ocupa a mesma área útil do workspace de Rack/Torre, à direita da barra lateral.
- Identidade visual unificada como **Caixa óptica**; CTO, CEO e CDO continuam existindo no modelo de dados, mas não condicionam a operação do Canvas.
- Conceito de bandeja removido da experiência do usuário. O backend legado continua recebendo um agrupamento interno criado automaticamente quando necessário.
- Cabos organizados em colunas verticais, com entrada à esquerda e saída à direita quando a topologia permite identificar o sentido.
- Ligações criadas de duas formas: clique em uma ponta e depois na outra, ou arraste uma linha diretamente entre as pontas.
- O mesmo fluxo cobre fusão fibra-fibra, entrada de splitter, saída de splitter e cascata entre splitters.
- Notas livres do projetista, com criação e edição por modal próprio.

## Diálogos

- Novo runtime `IXCMapDialog`, com confirmação, entrada de texto, seleção e formulários reutilizáveis.
- O editor óptico não usa `alert`, `prompt` ou `confirm` nativos do navegador.

## Rack e DIO

- DIO apresenta orientação explícita: lado esquerdo para OLT/equipamento e lado direito para cabos/rede externa.
- Widgets de cabo podem ser ampliados, reduzidos ou alternados entre larguras compacta e expandida.
- A largura é persistida por elemento e cabo no navegador, sem migration e sem alterar os dados de rede.
- A grade de fibras do widget acompanha a largura disponível e deixa de ficar espremida em doze colunas fixas.

## Arquitetura

- O editor óptico continua sem acessar o DOM ou o estado interno do Rack/Torre.
- O polimento do Rack é um runtime complementar carregado após o workspace existente e usa os eventos públicos `map:container-opening` e `map:container-rendered`.
- Nenhum `MutationObserver` novo.
- Nenhuma migration.
