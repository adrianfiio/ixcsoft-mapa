# Plataforma v0.79.1

Polimento visual do Financeiro por empresa e do Gateway de pagamento —
sem nenhuma mudança de comportamento, só CSS/template.

## Entrega

- **Financeiro por empresa** (`platform_company_billing.html`): os 5
  painéis (Assinatura, Status de acesso, Lançar cobrança manual,
  Faturas, Registrar pagamento) estavam todos numa única fileira de
  até 4 colunas, tão estreita que forçava barra de rolagem horizontal
  em formulário e tabela mesmo sem precisar. Reagrupados em fileiras
  de 2 (`Assinatura + Status de acesso`, `Lançar cobrança manual +
  Faturas`, `Registrar pagamento` por fatura pendente/atrasada),
  reaproveitando o mesmo `.billing-detail-grid` já usado no resto do
  app.
- Botões de cabeçalho "Editar empresa →"/"Financeiro →"/"Gateway →"
  (em `platform_company_billing.html`, `gateway_settings.html` e
  `platform_company_edit.html`) trocaram de botão sólido grande
  (`.primary-action`) por link discreto (`.panel-link`) — mesmo padrão
  visual mais contido já usado em `platform_financial_overview.html`/
  `platform_companies.html`.
- Checkboxes (`Gerar mensalidade automaticamente`, `Ambiente de testes`,
  `Integração ativa`) ganharam `accent-color: var(--primary)` — param
  de aparecer com o azul padrão do navegador, destoando do tema escuro
  do site.

## Dados e segurança

- Nenhuma mudança de model, view ou lógica de negócio — só
  `static/css/app.css` e 3 templates.
- Nenhuma migration.

## Validação executada neste sandbox (sem GDAL/Postgres)

- Chaves `{% if %}`/`{% endif %}`/`{% for %}`/`{% endfor %}` e tags
  `<section>`/`<article>` balanceadas nos 3 templates tocados.
- Chaves `{`/`}` balanceadas em `app.css`.
- `git diff --check` sem conflitos/espaço em branco.
- Renderização real (o quanto o reagrupamento elimina mesmo a barra de
  rolagem, o visual dos links compactos e dos checkboxes) depende do
  deploy no servidor — não é possível validar aqui.
