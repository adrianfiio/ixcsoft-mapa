# Plataforma v0.82.0

Community SNMP padrão por empresa (ISP) — evita pedir a community de
novo em cada equipamento novo ativado pelo mapa.

## Contexto

O Adrian pediu, explicitamente sem tocar em nada do mapa (o ChatGPT
está trabalhando nele agora): "deixa 1 padrão de community para cada
cliente, exemplo cliente provedor ISP pode cadastrar 1 community único
para todos equipamentos que ele configurar, para não ficar pedindo".

O diálogo "Monitoramento SNMP" (campo Community) é renderizado pelo
próprio `static/js/map-master-suite.js` — um arquivo do mapa,
ativamente tocado pelos pacotes do ChatGPT nesta mesma sessão. Por
isso a solução ficou inteiramente no backend: nenhum arquivo do mapa
foi tocado, e a tela de ativação continua com a mesma aparência e o
mesmo campo de sempre.

## Entrega

- **`apps/snmp_monitoring/models.py`**: novo modelo `CompanySNMPDefaults`
  (`OneToOneField` pra `core.Company`, `community_encrypted` — mesmo
  padrão de criptografia/API de `SNMPMonitoringProfile.set_community`/
  `get_community`, que por sua vez segue o mesmo padrão de
  `CompanyEmailConfiguration`).
- **`apps/snmp_monitoring/migrations/0003_companysnmpdefaults.py`**:
  migration nova (não dá pra rodar `makemigrations` neste sandbox sem
  Postgres/GDAL — escrita à mão seguindo exatamente o formato gerado
  pelo Django nas migrations existentes deste app).
- **`apps/snmp_monitoring/api.py`** (`equipment_monitoring_profile`):
  quando o perfil é novo (`profile is None`) e a `community` enviada
  está vazia, busca `CompanySNMPDefaults` da empresa do equipamento
  como reserva antes de recusar com HTTP 400. Se a empresa não tiver
  community padrão configurada, o comportamento é idêntico ao de
  antes (erro pedindo pra informar). Se o usuário digitar uma
  community específica na hora de ativar, ela sempre tem prioridade
  sobre a padrão.
- **`apps/core/forms.py`**: `CompanySNMPDefaultsForm` — campo único
  (`community`, `PasswordInput`, nunca reenvia o valor em texto puro),
  mesmo padrão de `CompanyEmailConfigurationForm`.
- **`apps/core/views.py`**: `company_snmp_defaults` — autoatendimento,
  só membro EDIT ativo da própria empresa (mesma regra de
  `company_email_settings`/`company_team`; nunca superusuário
  genérico).
- **`config/urls.py`**: rota nova `painel/snmp/`
  (`company-snmp-defaults`).
- **`templates/company_snmp_defaults.html`** (novo): formulário +
  indicação se já existe uma community padrão salva (nunca mostra o
  valor em texto puro — só um booleano "configurada"/"não
  configurada", mesmo padrão de `community_set` já usado no perfil
  SNMP por equipamento).
- **`templates/account_panel.html`**: novo atalho "Community SNMP
  padrão" no painel de autoatendimento, ao lado de "Central de
  alertas" (mesma condição — escondido pra empresa `is_designer`, que
  não opera equipamento monitorado).
- **`apps/snmp_monitoring/admin.py`**: `CompanySNMPDefaultsAdmin`
  (mesmo padrão de formulário com campo de senha do
  `SNMPMonitoringProfileForm` já existente).

## Fora de escopo (intencional)

- Nenhum arquivo de `apps/network_map/`, `static/js/map-*`,
  `templates/map.html` ou `templates/network_map/` foi tocado — a
  tela "Monitoramento SNMP" do mapa continua idêntica, byte a byte.
- Sem alteração no comportamento de edição/atualização de um perfil
  já existente — o fallback só entra na criação de um perfil novo.

## Dados e segurança

- Community padrão armazenada criptografada (`SecretCipher`, mesma
  chave `FIELD_ENCRYPTION_KEY` já usada em todo o app) — nunca em
  texto puro no banco, nunca reenviada pro navegador.
- `CASCADE` ao excluir a empresa (`on_delete=models.CASCADE`).

## Validação executada neste sandbox (sem GDAL/Postgres)

- `python -m py_compile apps/snmp_monitoring/models.py apps/snmp_monitoring/api.py apps/snmp_monitoring/admin.py apps/core/forms.py apps/core/views.py config/urls.py`.
- Migration nova revisada manualmente linha a linha contra o formato
  das migrations existentes do mesmo app (não foi possível rodar
  `makemigrations --check`/`migrate` sem Postgres).
- Chaves `{% if %}`/`{% endif %}`/`{% for %}`/`{% endfor %}` balanceadas
  no template novo e em `account_panel.html`.
- Revisão manual: nenhum arquivo da trilha do mapa tocado, `MAP_VERSION`
  inalterada.
- `manage.py check`/`migrate` e o teste real (empresa sem community
  padrão continua pedindo na ativação; empresa com community padrão
  ativa equipamento novo sem pedir; community específica digitada na
  hora ainda tem prioridade) dependem de banco real — feitos no
  servidor, como sempre.
