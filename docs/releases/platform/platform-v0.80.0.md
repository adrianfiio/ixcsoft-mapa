# Plataforma v0.80.0

Cancelar fatura lançada manualmente (com purga automática em 90 dias) +
página de fatura imprimível/PDF para o cliente + limpeza visual das
setinhas de campo numérico.

## Entrega

- **Cancelar fatura (Superadmin)**: na tabela de Faturas do Financeiro
  por empresa, faturas `pending`/`overdue` ganham um botão-ícone
  "Cancelar fatura" (com confirmação). Usa `Invoice.Status.CANCELED`,
  que já existia no enum mas nunca tinha sido usado por nenhuma view.
- **Purga automática em 90 dias**: task Celery diária nova
  (`purge_old_canceled_invoices`, `apps/billing/tasks.py`) apaga de
  verdade (`Invoice.objects.filter(status=CANCELED, updated_at__date__lte=cutoff).delete()`)
  toda fatura cancelada há mais de `CANCELED_INVOICE_RETENTION_DAYS = 90`
  dias. Único caso de exclusão física no módulo financeiro (mesmo
  espírito da exclusão de membro de equipe na v0.78.0) — se a fatura
  cancelada tinha pagamento parcial registrado, o `Payment` some
  junto (`on_delete=CASCADE`), aceito e documentado.
- **Página de fatura do cliente** (`painel/financeiro/faturas/<id>/`):
  resumo estruturado (empresa, mês, valor, vencimento, status, saldo,
  histórico de pagamentos) com botão "Imprimir / Salvar PDF" — usa a
  impressão nativa do navegador (que já oferece "Salvar como PDF" como
  destino), sem biblioteca de geração de PDF nova. Ainda não é boleto
  bancário real (sem código de barras/linha digitável).
- Tabela de Faturas do cliente (`company_overview.html`) ganha 3
  botões-ícone por linha — Ver / Imprimir / Salvar PDF — com o nome
  aparecendo em tooltip no hover (reaproveita o componente `.icon-action`
  da v0.79.0).
- Setinhas nativas de `<input type="number">` (ex.: campo "Mensalidade")
  removidas — visual flat, consistente com o resto do tema escuro.

## Dados e segurança

- Nenhum model novo, nenhuma migration.
- `company_invoice_detail` é escopado por empresa
  (`get_object_or_404(Invoice, pk=invoice_id, company=company)`) — não
  dá para ver fatura de outra empresa trocando o número na URL.
- Só EDIT vê/cancela/imprime fatura da própria empresa (mesma regra de
  sempre); só Superadmin cancela fatura de qualquer empresa.

## Validação executada neste sandbox (sem GDAL/Postgres)

- `python -m py_compile` em todos os arquivos Python tocados → OK.
- Lógica pura de corte de data (`today - 90 dias`) testada isolada, sem
  Django, com casos de borda.
- Chaves `{% if %}`/`{% endif %}`/`{% for %}`/`{% endfor %}` balanceadas
  nos templates tocados/novos.
- Chaves `{`/`}` balanceadas em `app.css`.
- `git diff --check` sem conflitos/espaço em branco.
- Renderização real, o cancelamento afetando o banco de verdade, e a
  task de purga rodando contra dados reais dependem do deploy no
  servidor — não é possível validar aqui.
