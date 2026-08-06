# Plataforma v0.83.0

Menu lateral e atalhos do dashboard restritos para usuário com papel
VIEW.

## Contexto

O Adrian trocou um cliente dele para o papel VIEW ("só visualizar") e
percebeu que o usuário continuava vendo tudo — menu lateral completo e
todos os atalhos do dashboard, como se fosse EDIT. Pedido dele: "o
view pode só ver o dashboard dele sem atalhos, no menu à esquerda só
Visão geral e Mapa operacional, pois ele só pode ver os números e ir
para o mapa, mais nada — mas ir ao mapa como view, se precisar editar
algo então espera, se não precisar pode navegar".

Investigação (agente de pesquisa dedicado, leitura completa antes de
qualquer edição) confirmou que:

- `CompanyMembership.Role` só tem `VIEW` e `EDIT` (`apps/core/models.py`).
- `can_edit_company`/`can_edit_map` já existem e já são usados
  corretamente em praticamente todo endpoint de escrita do
  `apps/network_map` — o mapa em si **já bloqueia edição** para VIEW no
  backend; o botão de alternar para modo edição em `templates/map.html`
  já só aparece para quem tem EDIT.
- Financeiro já era bloqueado no servidor para VIEW
  (`apps/billing/views.py::_editable_company` devolve `None` e
  redireciona) — só o link do menu aparecia sem necessidade.
- O bug real estava inteiramente na camada de menu/dashboard: nenhum
  item do menu lateral (`templates/base.html`) e nenhum atalho do
  painel "Atalhos operacionais" do dashboard tinha qualquer checagem de
  `role` — só checagens de tipo de empresa (`is_designer`) ou de
  superusuário.
- `templates/account_panel.html` já não expõe nenhuma ação de edição
  para quem não tem `can_manage_assets` (todo o bloco "Configurações da
  empresa" já é condicional) — o conteúdo em si nunca foi um risco, só
  precisava sair do menu por pedido explícito.

## Entrega

- **`apps/core/context_processors.py`** (`company_navigation`): novo
  `is_view_only_member` no contexto global, `True` quando a membership
  ativa do usuário na empresa atual tem `role=CompanyMembership.Role.VIEW`
  (calculado a partir da mesma `membership`/`current_company` que o
  context processor já resolve, sem query nova).
- **`templates/base.html`**: os links "Equipamentos", "Alertas",
  "Financeiro" e "Minha administração" do menu lateral passam a ficar
  dentro de `{% if not is_view_only_member %}`. "Visão geral" e "Mapa
  operacional" continuam sempre visíveis.
- **`templates/dashboard.html`** e **`templates/dashboard_designer.html`**:
  a condição do widget `panel_shortcuts` ("Atalhos operacionais"/
  "Atalhos" — Equipamentos, OLTs/ONUs, Central de alertas, Minha
  equipe) passa de `{% if edit_mode or not widget_meta.panel_shortcuts.hidden %}`
  para `{% if not is_view_only_member and (edit_mode or not widget_meta.panel_shortcuts.hidden) %}`,
  escondendo o painel inteiro para VIEW independentemente do layout
  salvo pela empresa. O botão "Abrir mapa operacional"/"Abrir mapa" no
  topo do dashboard **não foi tocado** — continua visível, é o caminho
  que o Adrian pediu para manter.

## Fora de escopo (intencional)

- Nenhuma mudança no bloqueio de edição do mapa em si — já estava
  correto (`can_edit_map`, `can_edit_company` em cada endpoint de
  escrita do `apps/network_map`).
- Nenhum bloqueio novo de URL/backend para Equipamentos, Alertas ou
  Minha administração — essas telas já são somente-leitura para quem
  não tem `can_edit_equipment`/`can_manage_assets`; o pedido era só de
  navegação (esconder do menu), não de bloqueio adicional de rota.
- Nenhum arquivo de `apps/network_map/`, `static/js/map-*` ou
  `templates/map.html` tocado — trilha do mapa intacta, `MAP_VERSION`
  inalterada.

## Dados e segurança

- Mudança é puramente de apresentação (context processor + templates);
  nenhum model, migration ou endpoint novo.
- Nenhum dado ou permissão de escrita mudou — o que já era bloqueado
  no servidor continua bloqueado; o que já era somente-leitura
  continua somente-leitura. Só a navegação ficou consistente com o que
  o backend já impunha.

## Validação executada neste sandbox (sem GDAL/Postgres)

- `python -m py_compile apps/core/context_processors.py`.
- Contagem de chaves `{% if %}`/`{% endif %}`/`{% for %}`/`{% endfor %}`
  balanceadas em `templates/base.html`, `templates/dashboard.html` e
  `templates/dashboard_designer.html` após a edição.
- `git diff --check` limpo nos arquivos tocados.
- Revisão manual do diff: só as 4 mudanças pretendidas, nenhum arquivo
  da trilha do mapa tocado, `MAP_VERSION` inalterada, nenhuma migration
  criada.
- `manage.py check` e o teste real (logar como o cliente VIEW e
  confirmar visualmente o menu reduzido, ausência de atalhos no
  dashboard, e navegação normal — porém sem edição — dentro do mapa)
  dependem de servidor real — combinado com o Adrian para testar no
  servidor antes do merge.
