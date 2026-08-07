# Platform v0.84.0

PWA de Técnico de Campo (`/app/`) integrada de verdade, e correção de
uma regressão de acesso que já estava em produção.

## Contexto

O PR anterior (`feat/technician-pwa`, já mergeado) só fez a parte rasa:
papel `TECHNICIAN` no modelo, a migration de compatibilidade
`edit→admin`, e um `TemplateView` solto. O usuário forneceu um pacote
de especificação completo (`AFService_Map_Tecnico_v0.1.0/`, com
`payload/`, `patches/` e um `PROMPT_CLAUDE.md` detalhado — checksums
conferidos com o `verify_checksums.py` do próprio pacote) e pediu a
integração completa.

Investigando antes de implementar, achei dois problemas reais:

1. **`/app/` nem resolvia em produção**: o commit que registrava a rota
   em `apps/network_map/urls.py` foi feito *depois* do merge do PR e
   nunca chegou no `main` — confirmado com HTTP 404 direto no servidor,
   contornando o redirect HTTPS que mascarava isso como 301 num teste
   ingênuo. O template também referenciava `/app/manifest.json` e
   `/app/sw.js`, que nunca existiram como rota — sem PWA instalável,
   sem Service Worker, sem funcionamento offline.
2. **Regressão de acesso ativa em produção**: 10 pontos do código
   checavam literalmente `role == CompanyMembership.Role.EDIT`
   esperando a semântica antiga ("edit" = administrador). A migration
   0014 (já aplicada em produção) promoveu todo `edit` legado para
   `admin` — e esses 10 pontos pararam de reconhecer qualquer um deles.
   Isso incluía gestão de equipe, branding, e-mail SMTP, SNMP padrão,
   onboarding, modo de operação ERP e o painel Financeiro.

## Correção

- `apps/core/access.py`: novos helpers `admin_company_ids`,
  `has_any_admin_access`, `user_can_admin_company`, `is_technician_only`
  — sem alterar os já existentes.
- Os 10 pontos que checavam `role == EDIT` esperando "administrador"
  agora checam `role == ADMIN` de verdade: `company_onboarding`,
  `company_provider_mode`, `company_team`, `company_email_settings`,
  `company_snmp_defaults`, `company_branding`, `_can_edit_dashboard` e
  o seletor interno de `erp_onboarding` (todos em
  `apps/core/views.py`), `onboarding_redirect_name`
  (`apps/core/access.py`), e `_editable_company`
  (`apps/billing/views.py`).
- `templates/company_team.html`: o botão de trocar papel só conhecia
  dois estados (`edit`↔`view`) e rebaixaria silenciosamente qualquer
  ADMIN ou TÉCNICO pra EDIT ao ser clicado. Virou um `<select>` com as
  4 opções reais.
- PWA integrada de verdade: `apps/core/technician_app.py` (view +
  Service Worker), `apps/core/middleware_technician.py`
  (`TechnicianAppOnlyMiddleware`), rotas `/app/` e `/app/sw.js`
  registradas em `apps/network_map/urls.py`, manifest/ícones/CSS/JS/
  offline.html do app técnico copiados do pacote (2 ajustes: a rota de
  logout real deste projeto é `/sair/`, não `/logout/`; e
  `/conta-bloqueada/` precisou entrar na allowlist do middleware pra
  não formar loop de redirect com o bloqueio de assinatura). Os 3
  arquivos rasos e mortos da tentativa anterior foram removidos.
- `TechnicianAppOnlyMiddleware` registrado **depois** de
  `SubscriptionAccessMiddleware` de propósito: se a empresa estiver
  bloqueada por assinatura, esse bloqueio precisa vencer primeiro; só
  depois o middleware do Técnico decide se redireciona pro `/app/`.
- `apps/core/models.py`: `role` sobe de `max_length=10` pra `15`, só
  pra bater com o schema já aplicado pela migration 0014 (sem
  migration nova).

## Validação

- `apps/core/tests/test_technician_access.py` (novo, 16 testes).
- `python manage.py check`, `makemigrations --check` (nenhuma migration
  nova esperada).
- Suíte completa `apps.core apps.network_map apps.billing`.
- Validação real no ambiente Docker isolado do servidor (nunca
  produção): ADMIN volta a gerenciar equipe/branding/SMTP/financeiro;
  TÉCNICO logando cai direto em `/app/` mesmo tentando `?next=/mapa/`;
  Manifest + Service Worker registrados de verdade em DevTools, Cache
  Storage sem `/api/` nem `/media/`; POST na API do mapa como TÉCNICO
  devolve 403.
- `MAP_VERSION` inalterada (`0.75.64`) — este release é só da trilha
  Plataforma.
