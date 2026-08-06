# Plataforma v0.83.1

Hotfix crítico da v0.83.0 — Server Error (500) na "Visão geral".

## Contexto

Minutos depois do merge/deploy da v0.83.0, o Adrian testou logando com
um cliente VIEW e caiu em **HTTP 500** ao abrir o dashboard.

Causa raiz: a tag `{% if %}` do Django **não aceita parênteses** para
agrupar `and`/`or`. `templates/dashboard.html` e
`templates/dashboard_designer.html` tinham:

```django
{% if not is_view_only_member and (edit_mode or not widget_meta.panel_shortcuts.hidden) %}
```

Isso lança `TemplateSyntaxError: Could not parse the remainder: '(edit_mode'`
**em tempo de compilação do template** — ou seja, quebra a renderização
da "Visão geral" para **qualquer usuário** que abrisse a página depois
do deploy (não só VIEW), já que o template nunca chega a compilar.
Reproduzido isoladamente antes de mexer em qualquer arquivo:

```python
>>> Template("{% if not a and (b or not c) %}YES{% endif %}")
TemplateSyntaxError: Could not parse the remainder: '(b' from '(b'
```

A verificação usada na v0.83.0 (contagem de `{% if %}`/`{% endif %}`)
não pega esse tipo de erro — conta as tags, não valida a gramática
interna de cada uma.

## Correção

- `templates/dashboard.html` e `templates/dashboard_designer.html`:
  a condição com parênteses virou dois `{% if %}` aninhados —
  `{% if not is_view_only_member %}{% if edit_mode or not widget_meta.panel_shortcuts.hidden %}...{% endif %}{% endif %}` —
  semanticamente idêntico, sintaxe válida.
- Nenhuma outra mudança de comportamento: mesmo `is_view_only_member`
  introduzido na v0.83.0, mesmo alvo (painel "Atalhos operacionais").

## Validação executada neste sandbox (sem GDAL/Postgres)

Desta vez com o **motor de template real do Django**, não só contagem
de chaves:

```python
from django.template import engines
engines["django"].get_template("dashboard.html")       # antes: TemplateSyntaxError | agora: OK
engines["django"].get_template("dashboard_designer.html")  # antes: TemplateSyntaxError | agora: OK
engines["django"].get_template("base.html")             # OK (não tinha o bug)
```

- Varredura de **todo** `templates/**/*.html` com o mesmo motor —
  nenhum outro `{% if %}` com parênteses encontrado no projeto (nem
  introduzido por mim, nem pré-existente).
- `grep` por `{% if ... (` em `templates/` — zero ocorrências restantes.
- `git diff --check` limpo.

## Dados e segurança

- Puramente correção de sintaxe de template — nenhum model, migration,
  endpoint ou regra de permissão mudou desde a v0.83.0.

## Pendente

- Confirmar no servidor, após o deploy desta versão, que: (1) a Visão
  geral abre normalmente para um usuário EDIT/admin comum, e (2) o
  cliente VIEW consegue logar e vê o menu reduzido sem erro 500.
