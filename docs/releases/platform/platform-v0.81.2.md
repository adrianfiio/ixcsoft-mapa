# Plataforma v0.81.2

Nova tela "Escolha um cliente" antes de abrir o mapa operacional, pro
Superadmin — primeiro passo de um pedido maior (ver "Fora de escopo"
abaixo pro que ainda falta).

## Contexto

Hoje, quando o Superadmin clica em "Abrir mapa" na Visão da
plataforma, ele cai direto no mapa operacional sem nenhuma tela
intermediária. Como o Superadmin não tem uma empresa própria
(`accessible_company_ids` retorna `None` pra superusuário — "sem
filtro"), o mapa carrega todos os clientes/projetos juntos, e
`has_any_edit_access` também retorna `True` pra superusuário — ou
seja, hoje o Superadmin não só vê tudo misturado como tem permissão
de editar qualquer coisa lá dentro. Isso é o que causava a sensação de
"falha" relatada.

Resolver isso de verdade (escolher 1 cliente → ver só o mapa dele →
sem poder editar nada) exige mexer nos próprios endpoints do mapa
(`apps/network_map/`), que é onde outra frente de trabalho está ativa
agora. Pra não correr risco de colidir com esse trabalho, esta entrega
fica só no lado da plataforma: uma tela de escolha de cliente antes do
link pro mapa, deixando a navegação mais organizada sem tocar em nada
do mapa em si.

## Entrega

- Nova view `map_client_picker` (`apps/core/views.py`), só-superadmin,
  reaproveitando o mesmo padrão de `DashboardLayoutListView` (lista de
  `Company.objects.filter(active=True)`).
- Nova rota `mapa/clientes/` (`map-client-picker`).
- Novo template `templates/map_client_picker.html`: lista de clientes
  em `.overview-table--compact`, cada linha com um `.icon-action` "Abrir
  mapa" (mesmo componente de tooltip da v0.79.0). Nota explícita na
  página avisando que o mapa ainda abre com todos os clientes juntos.
- `templates/platform_overview.html`: o botão "Abrir mapa" agora aponta
  pra `map-client-picker` em vez de `map` diretamente.

## Fora de escopo (propositalmente, por segurança)

- O mapa em si **não foi tocado**: nenhum arquivo em
  `apps/network_map/`, nenhuma mudança em `templates/map.html`, nenhuma
  alteração em `accessible_company_ids`/`has_any_edit_access`
  (`apps/core/access.py`). Por enquanto, clicar em "Abrir mapa" em
  qualquer linha da lista nova leva pro mesmo mapa (ainda sem filtro
  por empresa, ainda com permissão de edição pro Superadmin).
- Filtragem de verdade por cliente + modo só-visualização pro
  Superadmin ficam pra uma etapa futura, quando o mapa estiver estável
  o bastante pra mexer nesses endpoints sem risco de conflito.

## Validação executada neste sandbox (sem GDAL/Postgres)

- `python -m py_compile apps/core/views.py config/urls.py`.
- Chaves `{% if %}`/`{% endif %}`/`{% for %}`/`{% endfor %}` balanceadas
  no template novo.
- Revisão manual: nenhum arquivo da trilha do mapa tocado, `MAP_VERSION`
  inalterada, nenhuma migration.
- Renderização real (tela de escolha aparecendo certo, tooltip do
  ícone, superusuário-only) depende do deploy no servidor.
