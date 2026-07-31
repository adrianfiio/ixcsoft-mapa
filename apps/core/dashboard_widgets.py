"""Registro dos widgets (cartões/painéis) de cada variante do dashboard,
usado tanto pra montar o editor visual admin-only quanto pra aplicar a
ordem/visibilidade salva em `CompanyDashboardLayout` na renderização normal.

As chaves aqui precisam bater com o `data-widget="..."` de cada
`<article>` em `templates/dashboard.html` e `templates/dashboard_designer.html`.
"""

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
    ("panel_sync", "Painel · Sincronização IXCSoft"),
    ("panel_gpon", "Painel · Resumo GPON"),
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

WIDGET_REGISTRY = {"provider": PROVIDER_WIDGETS, "designer": DESIGNER_WIDGETS}


def widgets_for(company):
    return DESIGNER_WIDGETS if company and company.is_designer else PROVIDER_WIDGETS


def widget_meta_for(company, layout):
    """Monta ``{chave: {"order": N, "hidden": bool}}`` pro template a partir
    do `CompanyDashboardLayout` salvo. Sem layout (ou pra widgets novos que
    ainda não foram salvos), cai na ordem padrão do registro e fica visível."""
    widgets = widgets_for(company)
    if not layout:
        return {key: {"order": index, "hidden": False} for index, (key, _label) in enumerate(widgets)}

    saved_order = [key for key in (layout.widget_order or []) if isinstance(key, str)]
    order_map = {key: index for index, key in enumerate(saved_order)}
    hidden = set(layout.hidden_widgets or [])

    result = {}
    next_index = len(saved_order)
    for key, _label in widgets:
        if key in order_map:
            order = order_map[key]
        else:
            order = next_index
            next_index += 1
        result[key] = {"order": order, "hidden": key in hidden}
    return result
