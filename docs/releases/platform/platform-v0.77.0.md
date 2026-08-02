# Plataforma v0.77.0

Sistema de financeiro completo do Superadmin: uma página dedicada nova
que consolida os dados financeiros de todas as empresas num só lugar,
em vez de precisar abrir empresa por empresa.

## Entrega

- Página nova "Financeiro" (`painel/plataforma/financeiro/`), só
  Superadmin, com link próprio no menu lateral.
- 6 indicadores: MRR ativo, recebido este mês, pendente (valor),
  atrasado (valor), taxa de atraso (faturas abertas) e empresas
  bloqueadas.
- Gráfico de receita dos últimos 6 meses — CSS puro (mesma técnica do
  donut já existente no dashboard do provedor), sem biblioteca de
  gráfico nova.
- Relatório de faturas em atraso de todas as empresas, ordenado por
  vencimento, com dias em atraso e atalho direto pro financeiro da
  empresa.
- Lista de empresas com acesso bloqueado/cancelado.
- Histórico de pagamentos recentes e de liberações de confiança
  recentes, de todas as empresas.
- Atalho "Financeiro completo →" também na "Visão da plataforma".
- Corrigida uma barra de rolagem horizontal que aparecia sempre (mesmo
  com a tabela vazia) no financeiro do cliente — nova classe
  `.overview-table--compact`.

## Dados e segurança

- Nenhum model novo, nenhuma migration — reaproveita `CompanySubscription`,
  `Invoice`, `Payment`, `TrustRelease`, já existentes desde a v0.76.0.
- Só Superadmin acessa (`_require_superuser`, mesma guarda já usada em
  todo o painel Superadmin do financeiro).
- Nenhum dado é apagado nem alterado por esta tela — é só leitura.

## Validação executada neste sandbox (sem GDAL/Postgres)

- `python -m py_compile apps/billing/services.py apps/billing/views.py config/urls.py`.
- `_shift_month` (deslocamento de mês, usado no gráfico de receita)
  testado manualmente fora do Django, inclusive virada de ano/década.
- Chaves `{% if %}`/`{% endif %}`/`{% for %}`/`{% endfor %}` balanceadas
  nos templates tocados; chaves `{`/`}` balanceadas em `app.css`.
- `git diff --check` sem conflitos/espaço em branco.
- Renderização real da página e números batendo com o banco de produção
  dependem do deploy no servidor — não é possível validar aqui.
