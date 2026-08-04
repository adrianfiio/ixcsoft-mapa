# MAP v0.75.17 — PTP: causa raiz real do erro 500

## Objetivo

Corrigir o erro 500 do enlace PTP com prova (traceback real do servidor,
fornecido pelo usuário), não suposição.

## Causa raiz confirmada

```
File "/app/apps/network_map/api/ptp_links.py", line 185, in ptp_link_candidates
    if not can_view_company(request.user, source.company_id):
AttributeError: 'ContainerEquipmentPort' object has no attribute 'company_id'
```

`ContainerEquipmentPort` (`apps/network_map/models.py`) não herda
`CompanyScopedModel` e não tem campo `company`/`company_id` próprio — só
`ContainerEquipment` (via `equipment`) tem. O mesmo padrão de acesso
direto (`.company_id` numa instância de porta) existia em **3 pontos**
do arquivo `ptp_links.py`, todos corrigidos:

1. `ptp_link_candidates` (GET) — `source.company_id` → `source.equipment.company_id`, nos dois usos (permissão e filtro do queryset, que virou `equipment__company_id=...`).
2. `ptp_links` (POST, criação do enlace) — mesma correção em `source`/`destination`. Esse ponto ainda não tinha sido exercitado nos testes anteriores porque o GET de candidatos já quebrava antes de chegar aqui.
3. `ptp_link_detail` (DELETE) — `link.company_id` → `link.container.company_id` (`ContainerPortLink` também não tem `company` próprio, mas já vinha com `select_related("container")`).

## Por que "mesmo manual, com wireless marcado" não aparecia

Não era um problema de detecção do tipo de porta ou de exigir SNMP — o
endpoint de candidatos simplesmente **nunca respondia com sucesso**,
sempre 500, independente de como a porta foi criada. Corrigida a causa
raiz, o cadastro manual (`provisioning_mode=manual`) já é suficiente —
a consulta de candidatos nunca filtrou por modo de provisionamento.

## DIO — mensagem de conflito mais específica

Não encontrei inconsistência na lógica de conflito de porta em si (frente
e trás do mesmo slot já são tratadas como ocupações independentes no
banco, e o frontend usa `data-port-role` corretamente, não a posição
visual). Sem conseguir reproduzir com mais detalhe, a mensagem genérica
"Uma das portas já está em uso" virou algo específico: qual lado
(frontal/traseira) e qual ligação existente é a conflitante. Isso não
muda nenhum comportamento, só ajuda a diagnosticar sem precisar de acesso
direto ao banco na próxima vez que acontecer.

## Segurança da entrega

- Plataforma permanece em v0.82.0.
- Sem migrations.
- Mudança restrita a `apps/network_map/api/ptp_links.py` (3 correções de
  atributo) e `apps/network_map/api/views.py` (mensagem de erro).
