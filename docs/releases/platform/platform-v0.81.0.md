# Plataforma v0.81.0

Página de Equipamentos modernizada — sai do shell HTML/CSS próprio e
antigo (sem menu lateral) e passa a usar o layout compartilhado do
site, igual todas as outras páginas.

## Entrega

- `templates/network_map/equipment/list.html`, `detail.html`,
  `form.html` e `delete.html` passam a `{% extends "base.html" %}` em
  vez do shell próprio `network_map/equipment/base.html` (apagado —
  não era mais usado por nada). O menu lateral (sidebar) agora aparece
  normalmente nessas 4 telas, igual no resto do app.
- Todo o visual reaproveita componentes já estabelecidos, sem inventar
  nada novo: `.page-heading`, `.panel`, `.overview-table`/
  `.overview-table-wrap`, `.sync-pill` (status operacional), `.info-list`/
  `.info-row` (detalhe do equipamento), `.platform-form-grid` (form de
  editar), `.team-actions` (barra de exclusão em massa e paginação),
  `.primary-action`/`.panel-link`/`.cancel-link`/`.danger-action`
  (botões e links).
- Ações por linha da tabela (Ver/Editar/Excluir) viram 3 `.icon-action`
  com tooltip no hover — mesmo componente construído na v0.79.0.
- Único componente novo: `.filter-bar` (barra de busca + 3 selects sem
  rótulo, reaproveitando as mesmas cores já usadas em
  `.platform-form-grid`/`.billing-search`).
- `apps/network_map/forms.py` (`NetworkElementForm`): removidas as
  classes `"form-control"`/`"checkbox-input"` cravadas nos widgets —
  só existiam pro CSS do shell antigo; os campos agora usam o
  estilo padrão de `input`/`select`/`textarea` dentro de
  `.platform-form-grid`, já embutido no CSS global.

## Dados e segurança

- **Nenhuma mudança de comportamento** — só visual. Filtro, paginação,
  exclusão em massa (`bulk_action=delete`) e exclusão individual
  continuam funcionando exatamente como antes; a exclusão de
  equipamento já era física (`DeleteView` padrão do Django,
  pré-existente, fora do escopo desta entrega).
- Nenhuma migration, nenhuma mudança em `apps/network_map/views.py`.

## Validação executada neste sandbox (sem GDAL/Postgres)

- `python -m py_compile apps/network_map/forms.py` → OK.
- Chaves `{% if %}`/`{% endif %}`/`{% for %}`/`{% endfor %}` e tags
  `<table>`/`<section>`/`<article>` balanceadas nos 4 templates
  reescritos.
- Chaves `{`/`}` balanceadas em `app.css`.
- Confirmado por busca que nenhum outro template referenciava
  `network_map/equipment/base.html` antes de apagá-lo.
- Renderização real (sidebar aparecendo, filtro, seleção em massa,
  tooltips dos ícones) depende do deploy no servidor.
