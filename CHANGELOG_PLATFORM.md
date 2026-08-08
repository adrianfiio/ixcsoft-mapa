# Changelog — Plataforma

Cobre Dashboard, Visão geral, Financeiro, Superadmin, empresas,
usuários e integrações administrativas — tudo que **não** pertence ao
mapa. Tags `platform-vX.Y.Z`. Releases em `docs/releases/platform/`.

Para o mapa (editor cartográfico, Rack/Torre, Canvas 2D, fusões, popups,
SNMP, enlaces), ver [CHANGELOG_MAP.md](CHANGELOG_MAP.md).

Histórico anterior a esta separação (quando plataforma e mapa ainda
compartilhavam uma única numeração `vX.Y.Z` global) está em
[CHANGELOG.md](CHANGELOG.md) — as entradas que correspondem ao que hoje
é a trilha de plataforma são `[0.76.0]`, `[0.75.1]`, `[0.75.0]` e
`[0.74.0]` (módulo financeiro, ACL, painel Superadmin, correção de
arquitetura do financeiro — construídos nesta ordem, do zero, nesta
sessão).

## [platform-0.85.0] - 2026-08-08

Modernização visual de Minha equipe/Alertas/Financeiro do Superadmin/
edição de empresa, ciclo de vida real dos Alertas, escopo de projeto
por técnico e correção do 500 no Financeiro do Superadmin.

- **Minha equipe**: `.dashboard-grid`/`.dashboard-column` (layout de 2
  colunas) não existiam em nenhum CSS — os cards empilhavam sem grid
  nenhum. Adicionadas em `app.css`.
- **Alertas**: só mostra o que ainda está `OPEN`/`ACKNOWLEDGED`/
  `RECOVERING` — fechado (manual ou automático) some da lista. Novo
  botão "Limpar" por alerta e "Limpar todos" (fecha, não apaga —
  mantém histórico). Excluir o equipamento/porta/link/CTO/rota/OLT/
  PON/ONU referenciado por um alerta ainda ativo agora fecha esse
  alerta automaticamente (`apps/alerts/signals.py`, `pre_delete`) — a
  FK sempre foi `SET_NULL`, então o alerta ficava órfão e ativo pra
  sempre. Template trocou classes inventadas (`.alert-row`,
  `.monitoring-alert-list`) pelas reais (`.alert-item`, `.alert-list`).
- **`company_email_settings.html`**: `.secondary-action` não tinha
  estilo — adicionada em `app.css`.
- **Superadmin · editar empresa**: mesmo bug do toggle binário de
  papel que eu já tinha corrigido em `company_team.html` (rebaixava
  ADMIN/TÉCNICO pra EDIT silenciosamente) — agora um `<select>` com os
  4 papéis. Formulário ganhou `logo`/`brand_color` (whitelabel) — antes
  só editável pela própria empresa, o Superadmin não conseguia nem ver.
- **Financeiro do Superadmin — HTTP 500 corrigido**: causa raiz
  confirmada no log de produção —
  `templates/billing/platform_financial_overview.html` encadeava
  `release.requested_by.username` como argumento do filtro `default`
  mesmo quando `requested_by` é `None` (`SET_NULL`, usuário que pediu a
  liberação de confiança foi excluído depois) — `AttributeError:
  'NoneType' object has no attribute 'username'`. Trocado por um
  `{% if %}` guardando o acesso.
- **App do Técnico**: puxa `brand_color`/`logo` da empresa (mesmo
  mecanismo whitelabel de `base.html`). Camadas viram exatamente CTO,
  Rack, Torre, POP/CPD, Cabos, Rotas — "Clientes" removida por
  completo (info demais pro campo; elementos desse tipo nem entram
  mais no estado do app, não é só uma camada desmarcada). Rotas
  (`NetworkRoute`) é capacidade nova — o endpoint já existia
  (`/api/map/routes/`) mas o app nunca chamava.
- **Técnico só vê os projetos liberados pra ele**: novo campo
  `CompanyMembership.technician_projects` (M2M com `NetworkProject`) —
  vazio = nenhum projeto aparece no app até o admin liberar
  explicitamente em Minha equipe (comportamento combinado
  explicitamente com o usuário; afeta técnicos que já existiam antes
  desta versão). `/api/map/projects/` filtra por isso quando
  `is_technician_only(user)`; papel misto (técnico numa empresa, outro
  papel em outra) não é afetado.
- Migration nova: `core.0015_companymembership_technician_projects`
  (só o campo M2M — sem alterações de índice/campo não relacionadas
  que o `makemigrations` automático também detectou como drift
  pré-existente e que eu deixei de fora de propósito).
- Mapa fica de fora desta rodada — `MAP_VERSION` inalterada.

## [platform-0.84.0] - 2026-08-07

PWA de Técnico de Campo (`/app/`) integrada de verdade, e correção de
uma regressão de acesso que já estava em produção.

**O PR anterior (`feat/technician-pwa`) só fez a parte rasa**: papel
`TECHNICIAN`, a migration de compatibilidade `edit→admin`, e um
`TemplateView` solto. Comparando com o pacote de especificação completo
(`AFService_Map_Tecnico_v0.1.0/`, fornecido à parte, checksums
conferidos), achei dois problemas reais:

1. **`/app/` nem resolvia**: o commit que registrava a rota
   (`apps/network_map/urls.py`) foi feito *depois* do merge do PR e
   nunca chegou no `main` — confirmado com HTTP 404 direto no servidor
   de produção (contornando o redirect HTTPS que mascarava isso como
   301). O template também referenciava `/app/manifest.json` e
   `/app/sw.js`, que nunca existiram como rota — sem PWA instalável,
   sem Service Worker, sem funcionamento offline.
2. **Regressão de acesso ativa em produção**: 10 pontos do código
   (`apps/core/views.py`, `apps/core/access.py`,
   `apps/billing/views.py`) checavam literalmente
   `role == CompanyMembership.Role.EDIT` esperando a semântica antiga
   ("edit" = administrador). A migration 0014 (já aplicada em
   produção) promoveu todo `edit` legado para `admin` — e esses 10
   pontos pararam de reconhecer qualquer um deles. Isso incluía gestão
   de equipe (`company_team`), branding, e-mail SMTP, SNMP padrão,
   onboarding, modo de operação ERP e o painel Financeiro
   (`_editable_company`, `apps/billing/views.py`). Também achei um bug
   correlato no template `company_team.html`: o botão de trocar papel
   só conhecia dois estados (`edit`↔`view`) e rebaixaria silenciosamente
   qualquer ADMIN ou TÉCNICO pra EDIT ao ser clicado.

## Correção

- `apps/core/access.py`: novos helpers `admin_company_ids`,
  `has_any_admin_access`, `user_can_admin_company`, `is_technician_only`
  — sem alterar os já existentes (`editable_company_ids`,
  `can_edit_company`, `has_any_edit_access` continuam ADMIN+EDIT).
- Os 10 pontos que checavam `role == EDIT` esperando "administrador"
  agora checam `role == ADMIN` de verdade (7 em `apps/core/views.py`,
  1 em `apps/core/access.py::onboarding_redirect_name`, 1 no seletor
  interno de `erp_onboarding`, 1 em `apps/billing/views.py`).
- `templates/company_team.html`: botão de papel vira um `<select>` com
  as 4 opções reais (`CompanyMembership.Role.choices`), não mais um
  toggle binário.
- PWA integrada de verdade: `apps/core/technician_app.py` (view +
  Service Worker), `apps/core/middleware_technician.py`
  (`TechnicianAppOnlyMiddleware`, registrado depois do
  `SubscriptionAccessMiddleware` de propósito, pra não gerar loop de
  redirect com empresa bloqueada), rotas `/app/` e `/app/sw.js`
  registradas em `apps/network_map/urls.py`, manifest/ícones/CSS/JS/
  offline.html do app técnico. Os 3 arquivos rasos e mortos
  (`templates/network_map/technician_app.py.html`,
  `manifest.json.html`, `sw.js.html`) foram removidos.
- `apps/core/models.py`: `role` sobe de `max_length=10` pra `15`, só
  pra bater com o schema já aplicado pela migration 0014 (sem
  migration nova).

## Validação

- `apps/core/tests/test_technician_access.py` (novo, 16 testes:
  ADMIN/EDIT/VIEW/TÉCNICO cobrindo gestão de equipe, escrita/leitura no
  mapa, isolamento de tenant, redirecionamento do Técnico, papel misto
  entre empresas, Service Worker, exigência de login).
- `python manage.py check`, `makemigrations --check` (nenhuma migration
  nova esperada).
- Suíte completa `apps.core apps.network_map apps.billing`.
- Validação real no ambiente Docker isolado do servidor (nunca
  produção): ADMIN volta a gerenciar equipe/branding/SMTP/financeiro;
  TÉCNICO logando cai direto em `/app/` mesmo tentando `?next=/mapa/`;
  Manifest + Service Worker registrados de verdade em DevTools;
  POST na API do mapa como TÉCNICO devolve 403.
- `MAP_VERSION` inalterada (`0.75.64`) — este release é só da trilha
  Plataforma.

## [platform-0.83.1] - 2026-08-06

Hotfix crítico da v0.83.0: `templates/dashboard.html` e
`templates/dashboard_designer.html` quebravam com HTTP 500 para
**qualquer** usuário (não só VIEW) ao renderizar a "Visão geral" — a
tag `{% if %}` do Django não aceita parênteses para agrupar
`and`/`or` (`{% if not is_view_only_member and (edit_mode or ...) %}`
lançava `TemplateSyntaxError` em tempo de render). Corrigido trocando
por dois `{% if %}` aninhados, sem parênteses. Validado desta vez
compilando os templates de verdade com o motor de template do Django
(não só contagem de chaves), e varrendo todo `templates/` atrás do
mesmo padrão — nenhuma outra ocorrência encontrada.

## [platform-0.83.0] - 2026-08-06

Menu lateral e atalhos do dashboard restritos para usuário VIEW —
antes ficavam idênticos aos de um usuário EDIT, mesmo sem acesso real
às telas.

- Novo `is_view_only_member` no contexto global (`company_navigation`),
  calculado a partir do `role` da membership ativa na empresa atual.
- `templates/base.html`: menu lateral do usuário VIEW mostra só "Visão
  geral" e "Mapa operacional" — Equipamentos, Alertas, Financeiro e
  Minha administração ficam ocultos (Financeiro já era bloqueado no
  servidor pra VIEW; o link só não refletia isso).
- `templates/dashboard.html` e `templates/dashboard_designer.html`: o
  painel de atalhos operacionais (Equipamentos, OLTs/ONUs, Central de
  alertas, Minha equipe) some inteiro para VIEW. O botão "Abrir mapa
  operacional" continua visível — VIEW pode navegar o mapa, só não
  edita (bloqueio já existente em `can_edit_map`/`can_edit_company`).

## [platform-0.82.0] - 2026-08-03

Community SNMP padrão por empresa — evita pedir a community de novo em
cada equipamento novo. Ver
[docs/releases/platform/platform-v0.82.0.md](docs/releases/platform/platform-v0.82.0.md).

Resumo: novo modelo `CompanySNMPDefaults` (criptografado, mesmo padrão
de `CompanyEmailConfiguration`) e uma tela de autoatendimento
("Community SNMP padrão", em `/painel/snmp/`, só pra membros EDIT).
Quando o formulário de ativação do mapa é enviado sem community pra um
equipamento novo, o backend (`apps/snmp_monitoring/api.py`) busca a
community padrão da empresa como reserva antes de recusar — se a
empresa já tiver uma configurada, o equipamento ativa sem pedir de
novo; se digitar uma community específica na hora, essa continua tendo
prioridade. Nenhum arquivo do mapa foi tocado (nem
`apps/network_map/`, nem `static/js/map-*`, nem `templates/map.html`)
— a tela de ativação continua exatamente igual, só o comportamento por
trás dela muda quando o campo fica em branco.

## [platform-0.81.3] - 2026-08-03

Corrige o GID cravado do socket do Docker no `worker`, que fazia o
recarregamento do Telegraf falhar silenciosamente. Ver
[docs/releases/platform/platform-v0.81.3.md](docs/releases/platform/platform-v0.81.3.md).

Resumo: `docker-compose.yml` assumia GID `999` pro grupo dono de
`/var/run/docker.sock` (`group_add`), mas no servidor de produção o GID
real é `989` — então o worker nunca conseguia falar com o Docker pra
mandar o SIGHUP no Telegraf depois de criar/editar/remover um
monitoramento SNMP. O `.conf` era escrito/apagado certinho, só o aviso
pro Telegraf recarregar é que nunca chegava (erro só visível no log do
worker, nunca no site). Agora o GID é configurável via `DOCKER_SOCK_GID`
no `.env` (com `999` como default, mantendo compatibilidade).

## [platform-0.81.2] - 2026-08-03

Nova tela "Escolha um cliente" antes de abrir o mapa operacional, pro
Superadmin. Ver
[docs/releases/platform/platform-v0.81.2.md](docs/releases/platform/platform-v0.81.2.md).

Resumo: o botão "Abrir mapa" da Visão da plataforma agora leva primeiro
pra uma lista de clientes cadastrados (`/mapa/clientes/`), em vez de
abrir o mapa direto. É um primeiro passo de organização — o mapa em si
ainda não filtra por cliente pra Superadmin (continua mostrando todos
os projetos juntos, com permissão de edição), isso fica pra uma etapa
futura, quando não houver risco de colidir com trabalho em andamento
no mapa. Nenhum arquivo de `apps/network_map/` ou `templates/map.html`
foi tocado.

## [platform-0.81.1] - 2026-08-03

Correção visual: o dropdown "Alertas ativos" (sino no topo) ficava
parcialmente atrás dos cards da Visão geral (dashboard com GridStack).
Ver [docs/releases/platform/platform-v0.81.1.md](docs/releases/platform/platform-v0.81.1.md).

Resumo: `.app-topbar` não tinha `position`/`z-index` próprios, então o
`z-index: 60` do dropdown era resolvido contra o contexto de
empilhamento errado (o do `body`), e os widgets do dashboard (que o
GridStack posiciona de forma própria) acabavam desenhando por cima de
parte do dropdown. `.app-topbar` agora tem `position: relative; z-index: 45`,
criando um contexto de empilhamento só dela — daí o dropdown sempre
desenha por cima de qualquer conteúdo da página, em qualquer tela.
Nenhuma mudança de comportamento, só CSS.

## [platform-0.81.0] - 2026-08-02

Página de Equipamentos modernizada — sai do shell próprio e antigo,
entra no layout compartilhado do site. Ver
[docs/releases/platform/platform-v0.81.0.md](docs/releases/platform/platform-v0.81.0.md).

Resumo: as 4 telas de Equipamentos (listar, ver, editar, excluir)
tinham HTML/CSS totalmente separados do resto do app, herdados de uma
geração visual anterior — sem o menu lateral, com sua própria paleta e
componentes (`.button`, `.card`, `.badge`, `.form-control`). Passaram a
estender `templates/base.html`, reaproveitando 100% dos componentes já
estabelecidos (`.page-heading`, `.panel`, `.overview-table`,
`.sync-pill`, `.platform-form-grid`, `.info-list`, `.icon-action` com
tooltip para Ver/Editar/Excluir por linha). Nenhuma mudança de
comportamento — filtro, paginação, exclusão em massa e exclusão
individual continuam iguais, só o visual mudou. `templates/network_map/equipment/base.html`
(o shell antigo) foi apagado — não era mais usado por nada.

## [platform-0.80.0] - 2026-08-02

Cancelar fatura manual (com purga automática em 90 dias) + página de
fatura imprimível/PDF pro cliente. Ver
[docs/releases/platform/platform-v0.80.0.md](docs/releases/platform/platform-v0.80.0.md).

Resumo: Superadmin agora cancela uma cobrança manual lançada por
engano (`Invoice.Status.CANCELED`, já existia no enum, nunca tinha
sido usado); uma task diária nova (`purge_old_canceled_invoices`)
apaga de verdade do banco toda fatura cancelada há mais de 90 dias
(único caso de exclusão física no módulo financeiro, igual ao já feito
pra membro de equipe na v0.78.0). Cliente ganha uma página de fatura
(`/painel/financeiro/faturas/<id>/`) com dados estruturados e histórico
de pagamento, com "Imprimir/Salvar PDF" usando a impressão nativa do
navegador — 3 botões-ícone com tooltip (ver/imprimir/salvar PDF) na
tabela de faturas do Financeiro. Setinhas nativas de `<input type=number>`
removidas em favor do visual flat do tema escuro. Nenhum model novo,
nenhuma migration.

## [platform-0.79.1] - 2026-08-02

Polimento visual do Financeiro por empresa e do Gateway de pagamento.
Ver [docs/releases/platform/platform-v0.79.1.md](docs/releases/platform/platform-v0.79.1.md).

Resumo: os painéis do Financeiro por empresa (Assinatura, Status de
acesso, Lançar cobrança manual, Faturas, Registrar pagamento) estavam
todos espremidos numa única fileira de 4 colunas, forçando barra de
rolagem horizontal em formulário e tabela sem necessidade real —
reagrupados em fileiras de 2. Botões de cabeçalho "Editar empresa"/
"Financeiro"/"Gateway" trocaram de botão sólido grande (`.primary-action`)
por link discreto (`.panel-link`), removendo o exagero visual repetido
em 3 telas. Checkboxes ganharam `accent-color` no tema escuro do site
em vez do azul padrão do navegador. Nenhuma mudança de comportamento,
só CSS/template.

## [platform-0.79.0] - 2026-08-02

Página "Clientes" dedicada no menu do Superadmin — a tabela de
empresas sai da "Visão da plataforma" e ganha página própria, com
link no menu lateral (substitui o item "Nova empresa", que passa a
viver como botão dentro da página). Ver
[docs/releases/platform/platform-v0.79.0.md](docs/releases/platform/platform-v0.79.0.md).

Resumo: item de menu novo "Clientes" → lista de empresas cadastradas +
botão "Nova empresa" → em cada linha, as ações Editar/Financeiro/
Gateway viram botão-ícone com o nome aparecendo em tooltip no hover
(componente CSS novo, reutilizável, sem lib externa). Também corrige
um espaçamento pendente entre painéis empilhados no Financeiro da
plataforma e na tela de Editar empresa (a "barreira" pedida entre
widgets). Nenhum model novo, nenhuma migration.

## [platform-0.78.0] - 2026-08-02

Gestão de empresa e equipe pelo Superadmin — página nova "Editar
empresa" (`painel/plataforma/empresas/<id>/editar/`), ao lado do
Financeiro e do Gateway que já existiam por empresa. Ver
[docs/releases/platform/platform-v0.78.0.md](docs/releases/platform/platform-v0.78.0.md).

Resumo: Superadmin agora edita o cadastro de qualquer empresa (nome,
contato, documento, tipo — inclusive mudar o tipo depois de definido,
coisa que não tinha nenhuma tela funcional até agora) e gerencia a
equipe/acessos dela — adicionar membro, trocar papel (VIEW/EDIT),
ativar/desativar, redefinir senha (novidade: não existia em lugar
nenhum do sistema) e excluir de vez (novidade, com guarda de segurança
pra não apagar acesso do usuário numa empresa diferente por engano).
Nenhum model novo, nenhuma migration.

## [platform-0.77.0] - 2026-08-02

Sistema de financeiro completo do Superadmin — página dedicada nova em
"Financeiro" (menu do Superadmin), consolidando dados de todas as
empresas num só lugar. Ver
[docs/releases/platform/platform-v0.77.0.md](docs/releases/platform/platform-v0.77.0.md).

Resumo: MRR ativo, recebido/pendente/atrasado (valores), taxa de atraso,
gráfico de receita dos últimos 6 meses (CSS puro, sem lib nova), relatório
de faturas em atraso por empresa, lista de empresas com acesso bloqueado,
pagamentos recentes e liberações de confiança recentes — tudo agregado em
`apps/billing/services.py:platform_financial_summary()`, sem nenhum model
ou migration nova. Também corrigida uma barra de rolagem horizontal que
aparecia sempre (mesmo vazia) na tabela de faturas do financeiro do
cliente.

## [platform-0.76.0] - 2026-08-02

Ponto de partida desta trilha separada. Corresponde exatamente ao que
já estava publicado como `v0.76.0` no changelog global (commit
`cf1e118`) — ver a entrada completa em
[CHANGELOG.md#0760---2026-08-02](CHANGELOG.md) e
[docs/releases/v0.76.0.md](docs/releases/v0.76.0.md) pro detalhe
técnico completo. Resumo: correção de arquitetura do financeiro (quem é
cobrado é a empresa cliente — Provedor ISP ou Projetista —, não os
assinantes de internet de cada provedor), painel Superadmin exclusivo
pra cadastro/gestão de empresa e cobrança, liberação de confiança
(+2 dias de acesso, 1x por mês), bloqueio de acesso por assinatura com
fail-safe (empresa sem assinatura cadastrada nunca é bloqueada).

### Infraestrutura de versionamento (nesta mesma trilha)

- `PLATFORM_VERSION`/`MAP_VERSION` separados em `config/settings.py` e
  `docker-compose.yml` — `APP_VERSION` continua existindo só como alias
  de `PLATFORM_VERSION`, pra compatibilidade com código legado.
- Templates passam a ter `platform_version`/`map_version` disponíveis
  (além do `app_version` já existente, agora alias).
- `README.md` — "Versão atual" virou uma tabela com as duas trilhas.
- `docs/releases/platform/` e `docs/releases/map/` criados pra separar
  os releases detalhados de cada trilha daqui pra frente.
