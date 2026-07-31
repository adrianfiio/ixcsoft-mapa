"""Registro dos widgets (cartões/painéis) de cada variante do dashboard,
usado tanto pra montar o editor visual admin-only quanto pra aplicar a
ordem/visibilidade salva (`CompanyDashboardLayout`/`PlatformDashboardLayout`)
na renderização normal.

As chaves aqui precisam bater com o `data-widget="..."` de cada
`<article>` em `templates/dashboard.html`, `templates/dashboard_designer.html`
e `templates/platform_overview.html`.
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
    ("panel_sync", "Painel · Sincronização com ERP"),
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

PLATFORM_WIDGETS = [
    ("metric_companies", "Cartão · Empresas ativas"),
    ("metric_new_companies", "Cartão · Novas empresas (30 dias)"),
    ("metric_platform_clients", "Cartão · Clientes (total)"),
    ("metric_platform_cables", "Cartão · Cabos (km, total)"),
    ("metric_platform_elements", "Cartão · Elementos de rede (total)"),
    ("metric_platform_alerts", "Cartão · Alertas ativos (total)"),
    ("metric_sync_issues", "Cartão · Empresas com sincronização atrasada"),
    ("panel_companies_table", "Painel · Empresas"),
    ("panel_attention", "Painel · Precisa de atenção"),
]

WIDGET_REGISTRY = {
    "provider": PROVIDER_WIDGETS,
    "designer": DESIGNER_WIDGETS,
    "platform": PLATFORM_WIDGETS,
}


def widgets_for(company):
    return DESIGNER_WIDGETS if company and company.is_designer else PROVIDER_WIDGETS


def widget_meta(widgets, layout):
    """Monta ``{chave: {"order": N, "hidden": bool}}`` pro template a partir
    de um layout salvo (`CompanyDashboardLayout` ou `PlatformDashboardLayout`).
    Sem layout (ou pra widgets novos que ainda não foram salvos), cai na
    ordem padrão do registro e fica visível."""
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


def widget_meta_for(company, layout):
    return widget_meta(widgets_for(company), layout)


def clean_layout_payload(widgets, payload):
    """Valida o corpo JSON enviado pelo editor visual (`dashboard-layout-editor.js`)
    contra as chaves conhecidas de `widgets`, descartando qualquer coisa que
    não bata. Retorna ``(order, hidden, banner_text)``."""
    valid_keys = {key for key, _label in widgets}
    order = [key for key in payload.get("widget_order") or [] if key in valid_keys]
    hidden = [key for key in payload.get("hidden_widgets") or [] if key in valid_keys]
    banner_text = str(payload.get("banner_text") or "")[:280]
    return order, hidden, banner_text
