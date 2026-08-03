# Plataforma v0.81.1

Correção visual: o dropdown "Alertas ativos" (sino no topo, `.topbar-alert-dropdown`)
aparecia parcialmente atrás dos cards da Visão geral — só na tela do
dashboard (GridStack), não na Central de alertas nem em outras páginas.

## Causa

`.app-topbar` não tinha `position`/`z-index` próprios (só
`display: flex`). Sem isso, o `z-index: 60` declarado em
`.topbar-alert-dropdown` não era resolvido contra "o resto do topbar",
e sim contra o contexto de empilhamento raiz da página inteira — o
mesmo em que os widgets do dashboard (posicionados pelo GridStack)
também competem. Em páginas sem GridStack (como Central de alertas) não
havia nada nesse mesmo nível disputando espaço, então o dropdown sempre
aparecia por cima; no dashboard, os widgets acabavam ganhando parte
dessa disputa e desenhando por cima do dropdown.

## Entrega

- `static/css/app.css`: `.app-topbar` ganha `position: relative;
  z-index: 45;`. Isso cria um contexto de empilhamento só do topbar,
  acima do `.dashboard-editor-toolbar` (`z-index: 40`, sticky) e de
  qualquer widget do GridStack — então o dropdown de alertas (e
  qualquer outro conteúdo do topbar) sempre desenha por cima do
  conteúdo da página, em qualquer tela.
- Nenhuma mudança de layout/posição visual do topbar em si (só
  `position: relative` sem deslocamento — visualmente idêntico).

## Dados e segurança

- Só CSS — nenhuma mudança de comportamento, view, model ou template.

## Validação executada neste sandbox (sem GDAL/Postgres)

- Chaves `{`/`}` balanceadas em `app.css` após a edição.
- Revisão manual: nenhum arquivo da trilha do mapa tocado, nenhuma
  migration, `MAP_VERSION` inalterada.
- Renderização real (dropdown de alertas sempre visível por cima dos
  widgets na Visão geral) depende do deploy no servidor.
