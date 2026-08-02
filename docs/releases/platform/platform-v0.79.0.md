# Plataforma v0.79.0

Página "Clientes" dedicada no menu do Superadmin, com ações em ícone e
tooltip, e correção de espaçamento entre painéis empilhados.

## Entrega

- Item de menu novo "Clientes" (substitui "Nova empresa" — a criação
  de empresa passa a ser um botão dentro da própria página).
- Página `painel/plataforma/empresas/` lista todas as empresas
  cadastradas (mesma tabela que antes vivia na Visão da plataforma),
  com botão "Nova empresa →" e link "Financeiro completo →"/"Exportar
  financeiro →".
- Em cada linha, as ações Editar/Financeiro/Gateway viram botão-ícone:
  o nome só aparece como tooltip quando passa o mouse. Componente CSS
  novo (`.icon-action`/`.icon-actions`), sem biblioteca externa —
  reutilizável em qualquer botão-ícone futuro do app.
- A tabela de empresas saiu do sistema de widgets arrastáveis (GridStack)
  da Visão da plataforma — removida de `PLATFORM_WIDGETS`. O painel
  "Precisa de atenção" continua exatamente onde estava.
- Os links "← Voltar" das telas Editar empresa/Financeiro por empresa/
  Gateway/Nova empresa agora apontam pra "Clientes" (novo lar lógico
  dessas telas), não mais pra "Visão da plataforma".
- Corrigido um espaçamento pendente: painéis empilhados no Financeiro
  da plataforma e na tela de Editar empresa ficavam colados um no
  outro (bordas se tocando) por falta de `margin-bottom` em
  `.billing-detail-grid`. Corrigido de forma reutilizável (afeta as
  duas telas automaticamente).

## Dados e segurança

- Nenhum model novo, nenhuma migration.
- Remover `panel_companies_table` do registro de widgets é seguro:
  qualquer posição salva antiga desse widget (`PlatformDashboardLayout.widget_layout`)
  fica órfã e é ignorada na leitura, sendo limpa sozinha na próxima vez
  que alguém salvar o editor de layout — sem erro, sem migration.
- Só Superadmin acessa (mesma guarda de todas as páginas
  `painel/plataforma/...`).

## Validação executada neste sandbox (sem GDAL/Postgres)

- `python -m py_compile apps/core/views.py apps/core/dashboard_widgets.py config/urls.py`.
- Chaves `{% if %}`/`{% endif %}`/`{% for %}`/`{% endfor %}` balanceadas
  nos templates tocados.
- `git diff --check` sem conflitos/espaço em branco.
- Renderização real da página, os 3 tooltips aparecendo certo no hover
  e a navegação completa dependem do deploy no servidor — não é
  possível validar aqui.
