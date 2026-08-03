# MAP v0.75.6 — Cabos e fibras no Canvas unificado

**Data:** 2026-08-03
**Base validada:** `8746bf6a6767a63c630f36e3804b7746787603e0`
**Plataforma preservada:** `0.81.3`
**Mapa:** `0.75.6`

## Objetivo

Integrar os cabos ópticos e suas fibras ao mesmo Canvas 2D usado pelos equipamentos internos de Rack e Torre, eliminando a troca para painéis antigos durante a terminação no DIO e preservando o traçado após zoom, organização ou inclusão de novos ativos.

## Entregas

- cabos conectados aparecem como cards técnicos dentro do Canvas;
- cabos de entrada são organizados à esquerda e cabos de saída à direita;
- cada fibra é exibida individualmente com a cor real do catálogo óptico;
- uma fibra livre pode ser selecionada e terminada diretamente na porta traseira do DIO;
- uma fibra já utilizada pode ter sua terminação removida mediante confirmação;
- DIOs de alta capacidade são apresentados em páginas/bandejas de 24 portas;
- novos DIOs instalados em Torre ficam limitados a 12 ou 24 portas;
- Racks continuam aceitando DIOs maiores, com paginação visual;
- auto-fit e organização passam a considerar equipamentos, notas e cabos;
- pontos, linhas e entradas externas usam coordenadas corrigidas sob zoom;
- cards de cabos e fibras passam a fazer parte da exportação PNG/PDF;
- o botão **Fibras** apenas destaca cabos e DIOs no Canvas atual;
- Rack, Torre, CTO e CEO abrem diretamente seus editores técnicos, sem popup intermediário.

## Compatibilidade e dados

- nenhuma migration;
- nenhum equipamento, cabo, fibra, fusão ou histórico é excluído pelo deploy;
- posições antigas de equipamentos e rotas são preservadas;
- novos campos do layout (`cablePositions` e `dioPages`) ficam no JSON de layout já existente;
- `PLATFORM_VERSION=0.81.3` permanece intacta;
- `APP_VERSION` continua como alias da versão da plataforma.

## Homologação obrigatória

Após o merge e o deploy no Debian:

1. abrir Rack e Torre e confirmar que os cabos aparecem no Canvas;
2. confirmar entrada à esquerda e saída à direita;
3. selecionar uma fibra e clicar na porta **TRÁS** do DIO;
4. remover uma terminação já existente;
5. testar DIO com mais de 24 portas em Rack e alternar as bandejas;
6. confirmar que Torre rejeita DIO acima de 24 portas com HTTP 400 e mensagem clara;
7. mover equipamentos e cabos em diferentes níveis de zoom;
8. organizar e ajustar o Canvas;
9. exportar PNG e PDF e conferir cabos/fibras;
10. observar o DevTools por 60 segundos e confirmar ausência de loops de requisições.

## Tag futura

A tag será criada somente depois da homologação:

```text
map-v0.75.6
```
