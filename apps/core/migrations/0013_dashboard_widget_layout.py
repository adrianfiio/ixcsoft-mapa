from django.db import migrations, models

GRID_COLUMNS = 12
DEFAULT_METRIC_SIZE = (3, 2)
DEFAULT_PANEL_SIZE = (6, 4)
SIZE_OVERRIDES = {
    "panel_sync": (6, 3),
    "panel_gpon": (6, 3),
    "panel_companies_table": (12, 6),
}


def _default_size(key):
    if key in SIZE_OVERRIDES:
        return SIZE_OVERRIDES[key]
    return DEFAULT_METRIC_SIZE if key.startswith("metric_") else DEFAULT_PANEL_SIZE


def _auto_flow(keys):
    cursor_x = 0
    cursor_y = 0
    row_height = 0
    result = {}
    for key in keys:
        w, h = _default_size(key)
        if cursor_x and cursor_x + w > GRID_COLUMNS:
            cursor_x = 0
            cursor_y += row_height
            row_height = 0
        result[key] = {"x": cursor_x, "y": cursor_y, "w": w, "h": h}
        cursor_x += w
        row_height = max(row_height, h)
    return result


def _convert(order, hidden):
    """Reconstroi um `widget_layout` a partir do antigo `widget_order` +
    `hidden_widgets`, com auto-flow (mesmo algoritmo do app) usando o
    tamanho padrão de cada widget — preserva ordem relativa e visibilidade
    de qualquer layout já customizado antes desta versão."""
    order = [key for key in (order or []) if isinstance(key, str)]
    hidden = set(hidden or [])
    positions = _auto_flow(order)
    return {
        key: {**pos, "hidden": key in hidden}
        for key, pos in positions.items()
    }


def forwards(apps, schema_editor):
    CompanyDashboardLayout = apps.get_model("core", "CompanyDashboardLayout")
    PlatformDashboardLayout = apps.get_model("core", "PlatformDashboardLayout")
    for model in (CompanyDashboardLayout, PlatformDashboardLayout):
        for row in model.objects.all():
            row.widget_layout = _convert(row.widget_order, row.hidden_widgets)
            row.save(update_fields=["widget_layout"])


def backwards(apps, schema_editor):
    CompanyDashboardLayout = apps.get_model("core", "CompanyDashboardLayout")
    PlatformDashboardLayout = apps.get_model("core", "PlatformDashboardLayout")
    for model in (CompanyDashboardLayout, PlatformDashboardLayout):
        for row in model.objects.all():
            layout = row.widget_layout or {}
            order = sorted(layout, key=lambda key: (layout[key].get("y", 0), layout[key].get("x", 0)))
            hidden = [key for key, entry in layout.items() if entry.get("hidden")]
            row.widget_order = order
            row.hidden_widgets = hidden
            row.save(update_fields=["widget_order", "hidden_widgets"])


class Migration(migrations.Migration):
    dependencies = [("core", "0012_company_logo_company_brand_color")]

    operations = [
        migrations.AddField(
            model_name="companydashboardlayout",
            name="widget_layout",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    'Posição/tamanho/visibilidade de cada widget do dashboard '
                    'dessa empresa: {"chave": {"x": 0, "y": 0, "w": 3, "h": 2, "hidden": false}}.'
                ),
            ),
        ),
        migrations.AddField(
            model_name="platformdashboardlayout",
            name="widget_layout",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text=(
                    'Posição/tamanho/visibilidade de cada widget da visão da '
                    'plataforma: {"chave": {"x": 0, "y": 0, "w": 3, "h": 2, "hidden": false}}.'
                ),
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.RemoveField(model_name="companydashboardlayout", name="widget_order"),
        migrations.RemoveField(model_name="companydashboardlayout", name="hidden_widgets"),
        migrations.RemoveField(model_name="platformdashboardlayout", name="widget_order"),
        migrations.RemoveField(model_name="platformdashboardlayout", name="hidden_widgets"),
    ]
