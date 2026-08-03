# MAP v0.75.7 — Usabilidade de campo, Rack e fusões

**Data:** 2026-08-03
**Base validada:** `2516bb0d8f55ff1afc526e89df248d4127e82f73`
**Plataforma preservada:** `0.82.0`
**Mapa:** `0.75.7`

## Objetivo

Consolidar em uma única rodada os problemas encontrados na homologação real da MAP v0.75.6: identidade incorreta entre Rack e Torre, menus duplicados, movimentação acidental de pontos, notas limitadas, direção visual dos cabos, regras de equipamentos por estrutura, editor de fusões antigo e limites invisíveis no Canvas.

## Entregas

- evita submissão dupla no frontend e usa criação idempotente no backend para não gerar dois pontos sobrepostos;
- ao arrastar um ponto no mapa, pede confirmação antes de gravar e restaura a posição original quando cancelado;
- Rack e Torre passam a ter título, ícone, fundo e texto próprios no editor técnico;
- o cabeçalho legado duplicado é ocultado e o novo toolbar recebe botão de fechar;
- `Esc` fecha primeiro a janela interna aberta, sem encerrar todo o Canvas;
- notas usam editor próprio com `textarea`, texto multilinha, edição, exclusão e movimentação no Canvas;
- cabos mudam automaticamente o lado visual ao cruzar o centro da estrutura e as linhas acompanham o conector voltado para dentro;
- rotas possivelmente invertidas perguntam se o usuário deseja trocar origem/destino e reverter o traçado;
- Rack permite OLT, DIO, Switch, Router, Firewall, PTO e Outros; bloqueia AP, PTP e ONU/ONT no frontend e backend;
- Torre mantém os equipamentos de campo compatíveis;
- CTO, CEO e CDO usam o editor óptico em workspace amplo, com cabos, fibras, splitters, portas e notas;
- botão direito sobre Rack, Torre, CTO, CEO ou CDO abre ações de editar, abrir editor técnico/fusões e excluir;
- posições negativas passam a ser aceitas no Canvas e no diagrama óptico, removendo a parede invisível;
- auto-fit considera equipamentos, cabos e notas;
- nenhuma migration criada ou alterada por esta entrega do MAPA; a migration SNMP já existente na base da Plataforma v0.82.0 é preservada.

## Homologação obrigatória

1. criar uma Torre com clique único e confirmar que apenas um registro aparece;
2. arrastar um ponto, cancelar e confirmar retorno exato; repetir salvando;
3. abrir Rack e Torre e conferir identidade, toolbar único e botão de fechar;
4. abrir editor interno, pressionar `Esc` e confirmar que somente ele fecha;
5. criar nota longa com várias linhas, mover, editar e excluir;
6. arrastar cabo da esquerda para direita e conferir inversão visual e linha;
7. desenhar CTO → CEO e testar as opções de inverter ou manter;
8. no Rack, conferir OLT e ausência de AP/PTP/ONU; validar rejeição HTTP 400 por chamada direta;
9. abrir CTO, CEO e CDO, adicionar splitter e realizar/remover fusões;
10. usar botão direito nos ícones para editar, abrir fusões e excluir;
11. mover cards e notas para coordenadas negativas e usar Ajustar;
12. observar Console e Network por 60 segundos, sem exceções ou loops.

## Tag futura

A tag será criada somente após a homologação no Debian:

```text
map-v0.75.7
```
