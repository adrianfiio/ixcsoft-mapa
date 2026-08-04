# MAP v0.75.19 — PTP: status dos dois lados, distância, cor da porta

## Objetivo

Corrigir o ponto 1 do feedback mais recente: PTP conecta e desenha a linha
corretamente, mas a torre de destino não mostrava a informação da
ligação, faltava distância, e a porta não mudava de cor.

## Causa raiz do status assimétrico

Um enlace PTP é um `ContainerPortLink` criado com `container=source_tower`
(só a torre de ORIGEM). O endpoint `/equipment/` de uma torre só retorna
os links do PRÓPRIO container (`container.internal_port_links`) — então a
torre de DESTINO nunca via esse link nos seus próprios dados, e a porta
aparecia como "Status: Livre" mesmo estando ligada.

**Corrigido**: antes de decorar as portas, o código agora também consulta
`state.ptpLinks` (a lista de enlaces PTP do projeto inteiro, já buscada
para desenhar a linha no mapa) — essa lista tem as duas pontas
independente de qual torre "é dona" do registro no banco.

## Adicionado

- **Distância real** (fórmula de Haversine, a partir da latitude/longitude
  já disponíveis) exibida:
  - No tooltip e popup da linha tracejada no mapa.
  - No tooltip da porta wireless, junto com a informação de "ligado a".
- **Cor da porta wireless**: amarela quando livre, verde quando tem enlace
  PTP configurado.

## O que não foi feito, e por quê

O pedido original incluía um terceiro estado ("vermelho, porque caiu") —
isso exigiria monitoramento real de status do enlace (SNMP/telemetria),
que não existe hoje para ligações PTP neste sistema. Implementar uma cor
"vermelha" sem nenhuma medição por trás seria inventar informação, não
corrigir um bug. Fica registrado como pendência real de uma feature de
monitoramento, não uma correção visual.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Nenhum endpoint de API alterado — tudo calculado no frontend a partir de
  dados já existentes (`state.ptpLinks`, latitude/longitude).
