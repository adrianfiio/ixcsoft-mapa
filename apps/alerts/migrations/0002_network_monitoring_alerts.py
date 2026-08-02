import django.db.models.deletion
from django.db import migrations, models


def populate_company(apps, schema_editor):
    AlertEvent = apps.get_model("alerts", "AlertEvent")
    for event in AlertEvent.objects.filter(company__isnull=True).iterator(chunk_size=500):
        company_id = None
        if event.cto_id:
            cto = event.cto
            company_id = getattr(cto, "company_id", None)
        if not company_id and event.route_id:
            company_id = getattr(event.route, "company_id", None)
        if not company_id and event.olt_id:
            cpd = getattr(event.olt, "cpd", None)
            company_id = getattr(cpd, "company_id", None)
        if company_id:
            event.company_id = company_id
            event.save(update_fields=["company"])


class Migration(migrations.Migration):
    dependencies = [
        ("alerts", "0001_initial"),
        ("core", "0013_dashboard_widget_layout"),
        ("network_map", "0031_kmz_import_object_related_name"),
        ("snmp_monitoring", "0002_link_monitoring"),
    ]

    operations = [
        migrations.AlterField(
            model_name="alertrule",
            name="scope",
            field=models.CharField(
                choices=[
                    ("onu", "ONU"), ("cto", "CTO"), ("route", "Rota"),
                    ("pon", "Porta PON"), ("olt", "OLT"),
                    ("equipment", "Equipamento"), ("port", "Porta monitorada"),
                    ("link", "Enlace monitorado"), ("system", "Sistema"),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="alertevent",
            name="scope",
            field=models.CharField(
                choices=[
                    ("onu", "ONU"), ("cto", "CTO"), ("route", "Rota"),
                    ("pon", "Porta PON"), ("olt", "OLT"),
                    ("equipment", "Equipamento"), ("port", "Porta monitorada"),
                    ("link", "Enlace monitorado"), ("system", "Sistema"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="alertevent",
            name="company",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="alert_events", to="core.company"),
        ),
        migrations.AddField(
            model_name="alertevent",
            name="network_element",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="monitoring_alerts", to="network_map.networkelement"),
        ),
        migrations.AddField(
            model_name="alertevent",
            name="container_equipment",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="monitoring_alerts", to="network_map.containerequipment"),
        ),
        migrations.AddField(
            model_name="alertevent",
            name="equipment_port",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="monitoring_alerts", to="network_map.containerequipmentport"),
        ),
        migrations.AddField(
            model_name="alertevent",
            name="monitored_link",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="alerts", to="snmp_monitoring.monitorednetworklink"),
        ),
        migrations.AddIndex(
            model_name="alertevent",
            index=models.Index(fields=["company", "state", "-opened_at"], name="alerts_company_state_idx"),
        ),
        migrations.AddIndex(
            model_name="alertevent",
            index=models.Index(fields=["monitored_link", "state"], name="alerts_link_state_idx"),
        ),
        migrations.AddIndex(
            model_name="alertevent",
            index=models.Index(fields=["equipment_port", "state"], name="alerts_port_state_idx"),
        ),
        migrations.RunPython(populate_company, migrations.RunPython.noop),
    ]
