"""Registro dos widgets (cartões/painéis) de cada variante do dashboard,
usado tanto pra montar o editor visual quanto pra aplicar a
posição/tamanho/visibilidade salva (`CompanyDashboardLayout`/
`PlatformDashboardLayout`) na renderização normal.

As chaves aqui precisam bater com o `data-widget="..."` de cada
`<article>` em `templates/dashboard.html`, `templates/dashboard_designer.html`
e `templates/platform_overview.html`.

O layout é um grid livre de `GRID_COLUMNS` colunas (arrastar/redimensionar
tipo Zabbix/Grafana, via Gridstack.js no modo de edição) — cada widget tem
posição (x, y) e tamanho (w, h) em células, salvos ou calculados por
auto-flow quando ainda não foram customizados.
"""

GRID_COLUMNS = 12

PROVIDER_WIDGETS = [
    ("metric_access_online", "Cartão · Acessos online"),
    ("metric_access_offline", "Cartão · Acessos offline"),
    ("metric_infra", "Cartão · Infraestrutura"),
    ("metric_alerts", "Cartão · Alertas ativos"),
    ("metric_clients", "Cartão · Clientes"),
    ("metric_cables", "Cartão · Cabos (km)"),
    ("panel_access_status", "Painel · Estado dos acessos"),
    ("panel_shortcuts", "Painel · Atalhos operacionais"),
    ("panel_recent_alerts", "Painel · Alertas recentes"),
    ("panel_sync", "Painel · Sincronização com ERP"),
    ("panel_gpon", "Painel · Resumo GPON"),
    ("panel_infra_breakdown", "Painel · Infraestrutura por tipo"),
]

DESIGNER_WIDGETS = [
    ("metric_cto", "Cartão · CTOs"),
    ("metric_ceo", "Cartão · CEOs / caixas de emenda"),
    ("metric_dio", "Cartão · DIOs"),
    ("metric_olt", "Cartão · OLTs"),
    ("metric_cable_km", "Cartão · Cabos desenhados (km)"),
    ("panel_company_info", "Painel · Dados da empresa"),
    ("panel_shortcuts", "Painel · Atalhos"),
]

PLATFORM_WIDGETS = [
    ("metric_companies", "Cartão · Empresas ativas"),
    ("metric_new_companies", "Cartão · Novas empresas (30 dias)"),
    ("metric_platform_clients", "Cartão · Clientes (total)"),
    ("metric_platform_cables", "Cartão · Cabos (km, total)"),
    ("metric_platform_elements", "Cartão · Elementos de rede (total)"),
    ("metric_platform_alerts", "Cartão · Alertas ativos (total)"),
    ("metric_sync_issues", "Cartão · Empresas com sincronização atrasada"),
    ("metric_platform_received_month", "Cartão · Recebido este mês (todas as empresas)"),
    ("panel_companies_table", "Painel · Empresas"),
    ("panel_attention", "Painel · Precisa de atenção"),
]

WIDGET_REGISTRY = {
    "provider": PROVIDER_WIDGETS,
    "designer": DESIGNER_WIDGETS,
    "platform": PLATFORM_WIDGETS,
}

# Tamanho padrão (em células do grid de GRID_COLUMNS colunas) pra widget
# que ainda não foi posicionado manualmente. Cartões (metric_*) são
# pequenos e uniformes; painéis variam conforme o conteúdo típico.
_DEFAULT_METRIC_SIZE = (3, 2)
_DEFAULT_PANEL_SIZE = (6, 4)
_WIDGET_SIZE_OVERRIDES = {
    "panel_sync": (6, 3),
    "panel_gpon": (6, 3),
    "panel_infra_breakdown": (6, 5),
    "panel_companies_table": (12, 6),
}

# Widget que existe no registro (aparece na lista do editor, pronto pra
# ligar) mas não entra sozinho no layout de quem nunca mexeu nele — só
# passa a aparecer se a empresa marcar "Visível" e salvar.
_DEFAULT_HIDDEN_WIDGETS = {"panel_infra_breakdown"}


def default_widget_size(key):
    if key in _WIDGET_SIZE_OVERRIDES:
        return _WIDGET_SIZE_OVERRIDES[key]
    return _DEFAULT_METRIC_SIZE if key.startswith("metric_") else _DEFAULT_PANEL_SIZE


def widgets_for(company):
    return DESIGNER_WIDGETS if company and company.is_designer else PROVIDER_WIDGETS


def _auto_flow(widgets, start_y=0):
    """Posiciona widgets em sequência (esquerda pra direita, quebrando
    linha ao passar de GRID_COLUMNS) — usado pra widget sem posição salva
    ainda, na ordem em que aparecem no registro."""
    cursor_x = 0
    cursor_y = start_y
    row_height = 0
    result = {}
    for key, w, h in widgets:
        if cursor_x and cursor_x + w > GRID_COLUMNS:
            cursor_x = 0
            cursor_y += row_height
            row_height = 0
        result[key] = {"x": cursor_x, "y": cursor_y, "w": w, "h": h}
        cursor_x += w
        row_height = max(row_height, h)
    return result


def widget_meta(widgets, layout):
    """Monta ``{chave: {"x","y","w","h","hidden","x1","y1"}}`` pro template
    a partir de um layout salvo (`CompanyDashboardLayout` ou
    `PlatformDashboardLayout`). ``x1``/``y1`` já vêm em base 1 (linhas de
    grid do CSS), prontos pra usar em ``grid-column``/``grid-row``.

    Widget sem posição salva (layout novo, ou widget que apareceu depois
    da última edição) cai em auto-flow, continuando depois do maior ``y``
    já ocupado pelos widgets salvos."""
    saved = {}
    if layout:
        for key, entry in (layout.widget_layout or {}).items():
            if isinstance(entry, dict):
                saved[key] = entry

    result = {}
    unpositioned = []
    max_y = 0
    for key, _label in widgets:
        entry = saved.get(key)
        has_position = entry and all(
            isinstance(entry.get(field), int) for field in ("x", "y", "w", "h")
        )
        if has_position:
            w_default, h_default = default_widget_size(key)
            x, y, w, h = entry["x"], entry["y"], entry.get("w") or w_default, entry.get("h") or h_default
            result[key] = {
                "x": x, "y": y, "w": w, "h": h,
                "hidden": bool(entry.get("hidden")),
                "x1": x + 1, "y1": y + 1,
            }
            max_y = max(max_y, y + h)
        else:
            w_default, h_default = default_widget_size(key)
            unpositioned.append((key, w_default, h_default))

    if unpositioned:
        for key, pos in _auto_flow(unpositioned, start_y=max_y).items():
            saved_entry = saved.get(key)
            if saved_entry is not None:
                hidden = bool(saved_entry.get("hidden"))
            else:
                hidden = key in _DEFAULT_HIDDEN_WIDGETS
            result[key] = {**pos, "hidden": hidden, "x1": pos["x"] + 1, "y1": pos["y"] + 1}
    return result


def widget_meta_for(company, layout):
    return widget_meta(widgets_for(company), layout)


def clean_layout_payload(widgets, payload):
    """Valida o corpo JSON enviado pelo editor visual
    (`dashboard-layout-editor.js`, via `GridStack.save()`) contra as
    chaves conhecidas de `widgets`, descartando qualquer coisa que não
    bata ou tenha valor fora da faixa. Retorna ``(widget_layout, banner_text)``."""
    valid_keys = {key for key, _label in widgets}
    raw_layout = payload.get("widget_layout")
    widget_layout = {}
    if isinstance(raw_layout, dict):
        for key, entry in raw_layout.items():
            if key not in valid_keys or not isinstance(entry, dict):
                continue
            try:
                w = max(1, min(GRID_COLUMNS, int(entry.get("w", 1))))
                h = max(1, min(40, int(entry.get("h", 1))))
                x = max(0, min(GRID_COLUMNS - w, int(entry.get("x", 0))))
                y = max(0, min(200, int(entry.get("y", 0))))
            except (TypeError, ValueError):
                continue
            widget_layout[key] = {"x": x, "y": y, "w": w, "h": h, "hidden": bool(entry.get("hidden"))}
    banner_text = str(payload.get("banner_text") or "")[:280]
    return widget_layout, banner_text
