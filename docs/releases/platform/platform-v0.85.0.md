# Platform v0.85.0

Modernização visual (Minha equipe, Alertas, e-mail, edição de empresa no
Superadmin), ciclo de vida real dos Alertas, escopo de projeto por técnico
no app de campo, e correção de um HTTP 500 no Financeiro do Superadmin.

## Contexto

O usuário reportou várias páginas administrativas com aparência quebrada
("horrível"), Alertas que nunca somem mesmo resolvidos, Superadmin sem
acesso ao whitelabel de uma empresa nem forma real de trocar papel de
membro, o Financeiro do Superadmin dando erro 500, e pediu que o app do
Técnico ganhe visual moderno + puxe o whitelabel + mostre só as camadas
relevantes pro campo (sem Clientes) + só os projetos liberados por
técnico. O mapa em si ficou de fora — segue sendo trabalhado
separadamente.

## O que mudou

### Minha equipe
`templates/company_team.html` já usava as classes certas do design
system, mas `.dashboard-grid`/`.dashboard-column` (o wrapper de 2
colunas) não existiam em nenhum CSS — os painéis empilhavam sem grid
nenhum. Adicionadas em `static/css/app.css`.

### Alertas
Causa raiz dupla: `company_alerts` mostrava todo `AlertEvent` sem
filtrar por `state` (inclusive os já `CLOSED`, pra sempre), e toda FK de
`AlertEvent` pro equipamento/link/porta é `SET_NULL` (não `CASCADE`) —
excluir o objeto monitorado deixava o alerta órfão e ainda ativo pra
sempre, já que nada nunca ia "voltar a normal" pra fechá-lo.

- View filtra por padrão só `OPEN`/`ACKNOWLEDGED`/`RECOVERING`.
- Novo `apps/alerts/signals.py`, conectado via `pre_delete` em `OLT`,
  `PONPort`, `ONU`, `CTO`, `NetworkRoute`, `NetworkElement`,
  `ContainerEquipment`, `ContainerEquipmentPort` e
  `MonitoredNetworkLink` — fecha (`state=CLOSED`) qualquer alerta ainda
  ativo referenciando o objeto antes dele ser excluído.
- Botões "Limpar" (por alerta) e "Limpar todos" — fecham, não apagam
  (mantém histórico/auditoria). Exigem EDIT+ (VIEW não consegue).
- Template trocou classes inventadas (`.alert-row`,
  `.monitoring-alert-list`) pelas reais do design system (`.alert-item`,
  `.alert-list`, `.legend-dot`).

### Superadmin · editar empresa
- Mesmo bug do toggle binário de papel já corrigido em
  `company_team.html` numa rodada anterior (platform-v0.84.0) — aqui
  ainda existia, rebaixando ADMIN/TÉCNICO pra EDIT silenciosamente ao
  clicar. Agora um `<select>` com os 4 papéis.
- Formulário ganhou `logo`/`brand_color` (whitelabel) — antes só
  editável pela própria empresa em "Marca"; o Superadmin não tinha
  acesso nenhum a isso.

### Financeiro do Superadmin — HTTP 500
Causa raiz confirmada direto no log de produção
(`docker logs ixcsoft-mapa-web-1`):
`templates/billing/platform_financial_overview.html` encadeava
`release.requested_by.username` como argumento do filtro `default`
mesmo quando `requested_by` é `None` (campo `SET_NULL` — usuário que
pediu a liberação de confiança foi excluído depois) —
`AttributeError: 'NoneType' object has no attribute 'username'`.
Trocado por `{% if release.requested_by %}` guardando o acesso.

### App do Técnico
- Puxa `brand_color`/`logo` da empresa (mesmo mecanismo whitelabel de
  `base.html`) — `--accent` de `technician-app.css` agora deriva de
  `var(--primary, #43b8ff)`.
- Camadas viram exatamente **CTO, Rack, Torre, POP/CPD, Cabos, Rotas**
  — "Clientes" removida por completo (elementos desse tipo nem entram
  mais em `state.elements`, não é só uma camada desmarcada). Rack/Torre
  ganham categoria própria (antes caíam juntas em "infraestrutura"
  genérica). Rotas é capacidade nova — o endpoint já existia
  (`/api/map/routes/`, GeoJSON `MultiLineString`) mas o app nunca
  chamava; agora desenha como linha tracejada no Leaflet.

### Técnico só vê os projetos liberados pra ele
- Novo campo `CompanyMembership.technician_projects` (M2M com
  `NetworkProject`, migration `core.0015`).
- **Vazio = nenhum projeto aparece no app até o admin liberar
  explicitamente** — combinado de propósito com o usuário antes de
  implementar; afeta técnicos que já existiam antes desta versão (vão
  ver a lista de projetos vazia até alguém liberar pra eles).
- `/api/map/projects/` filtra por `technician_projects` quando
  `is_technician_only(request.user)` — usuário com papel misto (técnico
  numa empresa, outro papel em outra) não é afetado, continua vendo
  tudo normalmente.
- Nova ação `set_technician_projects` em `company_team` — checklist de
  projetos da empresa, só aparece pra membros com papel TÉCNICO.

## Validação

- `apps/core/tests/test_platform_v085.py` (novo, 13 testes): alerta
  fechado some da lista; alerta aberto aparece; excluir elemento com
  alerta ativo fecha o alerta; "Limpar"/"Limpar todos" funcionam; VIEW
  não consegue limpar; Superadmin troca papel pelos 4 valores; página
  de edição expõe os campos de whitelabel; liberação de confiança órfã
  não quebra mais o Financeiro; técnico sem projeto liberado recebe
  lista vazia; técnico com projeto liberado só vê esse; papel misto não
  é afetado; admin consegue liberar projetos pelo Minha equipe.
- `manage.py check` e `makemigrations --check` (Docker isolado, GDAL) —
  minha migration não introduziu nenhum drift novo (só o
  pré-existente, já visto em rodadas anteriores, não relacionado:
  `billing.monthly_amount`, `core.erp_provider`, renomeações de índice
  em `network_map`/`snmp_monitoring`).
- Suíte completa `apps.core apps.billing apps.network_map apps.alerts`
  (94 testes) — só as 2 falhas antigas e não relacionadas já
  conhecidas (ordenação de scripts em `map.html`).
- Validação real no navegador (Playwright, Docker isolado, nunca
  produção).
- `MAP_VERSION` inalterada — este release é só da trilha Plataforma.
