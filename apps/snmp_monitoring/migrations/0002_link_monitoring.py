import django.core.validators
import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


def preserve_legacy_profile_policy(apps, schema_editor):
    Profile = apps.get_model("snmp_monitoring", "SNMPMonitoringProfile")
    Profile.objects.filter(element__isnull=False, equipment__isnull=True).update(
        aggregate_policy="all_interfaces"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0013_dashboard_widget_layout"),
        ("network_map", "0031_kmz_import_object_related_name"),
        ("snmp_monitoring", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="snmpmonitoringprofile",
            name="element",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="snmp_monitoring",
                to="network_map.networkelement",
            ),
        ),
        migrations.AlterField(
            model_name="snmpmonitoringprofile",
            name="polling_interval_seconds",
            field=models.PositiveIntegerField(
                default=30,
                validators=[
                    django.core.validators.MinValueValidator(5),
                    django.core.validators.MaxValueValidator(3600),
                ],
            ),
        ),
        migrations.AddField(
            model_name="snmpmonitoringprofile",
            name="equipment",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="snmp_monitoring",
                to="network_map.containerequipment",
            ),
        ),
        migrations.AddField(
            model_name="snmpmonitoringprofile",
            name="aggregate_policy",
            field=models.CharField(
                choices=[
                    ("bound_ports", "Somente portas vinculadas"),
                    ("all_interfaces", "Todas as interfaces detectadas"),
                    ("no_aggregate", "Não alterar status agregado"),
                ],
                default="bound_ports",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="snmpmonitoringprofile",
            name="last_success_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="snmpmonitoringprofile",
            name="last_status",
            field=models.CharField(
                choices=[
                    ("normal", "Normal"),
                    ("warning", "Atenção"),
                    ("degraded", "Degradado"),
                    ("offline", "Offline"),
                    ("recovering", "Recuperando"),
                    ("no_data", "Sem dados"),
                ],
                default="no_data",
                max_length=20,
            ),
        ),
        migrations.RunPython(preserve_legacy_profile_policy, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="snmpmonitoringprofile",
            index=models.Index(fields=["company", "last_status"], name="snmp_prof_company_status_idx"),
        ),
        migrations.AddConstraint(
            model_name="snmpmonitoringprofile",
            constraint=models.CheckConstraint(
                condition=(
                    Q(element__isnull=False, equipment__isnull=True)
                    | Q(element__isnull=True, equipment__isnull=False)
                ),
                name="snmp_profile_exactly_one_target",
            ),
        ),
        migrations.CreateModel(
            name="SNMPInterfaceState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("interface_key", models.CharField(max_length=260)),
                ("if_name", models.CharField(max_length=255)),
                ("if_index", models.PositiveIntegerField(blank=True, null=True)),
                ("if_alias", models.CharField(blank=True, max_length=255)),
                ("status", models.CharField(choices=[("up", "UP"), ("down", "DOWN"), ("testing", "Testando"), ("unknown", "Desconhecido"), ("dormant", "Dormente"), ("not_present", "Não presente"), ("lower_layer_down", "Camada inferior DOWN"), ("other", "Outro")], default="unknown", max_length=24)),
                ("raw_status", models.IntegerField(blank=True, null=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("status_changed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="+", to="core.company")),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interface_states", to="snmp_monitoring.snmpmonitoringprofile")),
            ],
            options={
                "verbose_name": "Estado de interface SNMP",
                "verbose_name_plural": "Estados de interfaces SNMP",
                "ordering": ("profile", "if_index", "if_name"),
            },
        ),
        migrations.CreateModel(
            name="SNMPPortBinding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("label", models.CharField(blank=True, max_length=160)),
                ("if_name", models.CharField(max_length=255)),
                ("if_index", models.PositiveIntegerField(blank=True, null=True)),
                ("role", models.CharField(choices=[("backbone", "Backbone"), ("uplink", "Uplink"), ("access", "Acesso"), ("wireless", "Wireless/PTP"), ("management", "Gerência"), ("other", "Outro")], default="other", max_length=24)),
                ("enabled", models.BooleanField(default=True)),
                ("expected_up", models.BooleanField(default=True)),
                ("alert_enabled", models.BooleanField(default=True)),
                ("severity", models.CharField(choices=[("info", "Informação"), ("warning", "Aviso"), ("average", "Média"), ("high", "Alta"), ("disaster", "Desastre")], default="high", max_length=20)),
                ("outage_persistence_seconds", models.PositiveIntegerField(default=30)),
                ("recovery_seconds", models.PositiveIntegerField(default=30)),
                ("last_status", models.CharField(choices=[("up", "UP"), ("down", "DOWN"), ("unknown", "Sem dados"), ("other", "Outro")], default="unknown", max_length=20)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("status_changed_at", models.DateTimeField(blank=True, null=True)),
                ("down_since", models.DateTimeField(blank=True, null=True)),
                ("up_since", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="+", to="core.company")),
                ("equipment_port", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="snmp_binding", to="network_map.containerequipmentport")),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="port_bindings", to="snmp_monitoring.snmpmonitoringprofile")),
            ],
            options={
                "verbose_name": "Vínculo de porta SNMP",
                "verbose_name_plural": "Vínculos de portas SNMP",
                "ordering": ("profile", "role", "if_index", "if_name"),
            },
        ),
        migrations.CreateModel(
            name="MonitoredNetworkLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=180)),
                ("code", models.CharField(blank=True, max_length=100)),
                ("link_type", models.CharField(choices=[("backbone", "Backbone óptico"), ("fiber", "Fibra óptica"), ("copper", "Cobre"), ("wireless", "PTP wireless")], max_length=20)),
                ("enabled", models.BooleanField(default=True)),
                ("require_both_endpoints", models.BooleanField(default=True)),
                ("alert_enabled", models.BooleanField(default=True)),
                ("severity", models.CharField(choices=[("info", "Informação"), ("warning", "Aviso"), ("average", "Média"), ("high", "Alta"), ("disaster", "Desastre")], default="high", max_length=20)),
                ("normal_color", models.CharField(default="#38bdf8", max_length=7, validators=[django.core.validators.RegexValidator(message="Informe uma cor hexadecimal no formato #RRGGBB.", regex="^#[0-9A-Fa-f]{6}$")])),
                ("down_color", models.CharField(default="#ef4444", max_length=7, validators=[django.core.validators.RegexValidator(message="Informe uma cor hexadecimal no formato #RRGGBB.", regex="^#[0-9A-Fa-f]{6}$")])),
                ("dash_array", models.CharField(blank=True, max_length=40)),
                ("weight", models.PositiveSmallIntegerField(default=5, validators=[django.core.validators.MinValueValidator(2), django.core.validators.MaxValueValidator(12)])),
                ("outage_persistence_seconds", models.PositiveIntegerField(default=30)),
                ("recovery_seconds", models.PositiveIntegerField(default=30)),
                ("status", models.CharField(choices=[("normal", "Normal"), ("warning", "Atenção"), ("degraded", "Degradado"), ("offline", "Offline"), ("recovering", "Recuperando"), ("no_data", "Sem dados")], default="no_data", max_length=20)),
                ("candidate_status", models.CharField(blank=True, choices=[("normal", "Normal"), ("warning", "Atenção"), ("degraded", "Degradado"), ("offline", "Offline"), ("recovering", "Recuperando"), ("no_data", "Sem dados")], max_length=20)),
                ("candidate_since", models.DateTimeField(blank=True, null=True)),
                ("status_changed_at", models.DateTimeField(blank=True, null=True)),
                ("last_evaluated_at", models.DateTimeField(blank=True, null=True)),
                ("last_message", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="+", to="core.company")),
                ("cable", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="monitored_link", to="network_map.fibercable")),
                ("destination_binding", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="destination_links", to="snmp_monitoring.snmpportbinding")),
                ("destination_element", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="monitored_links_as_destination", to="network_map.networkelement")),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="monitored_links", to="network_map.networkproject")),
                ("source_binding", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="source_links", to="snmp_monitoring.snmpportbinding")),
                ("source_element", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="monitored_links_as_source", to="network_map.networkelement")),
            ],
            options={
                "verbose_name": "Enlace monitorado",
                "verbose_name_plural": "Enlaces monitorados",
                "ordering": ("project", "name"),
            },
        ),
        migrations.AddConstraint(
            model_name="snmpinterfacestate",
            constraint=models.UniqueConstraint(fields=("profile", "interface_key"), name="unique_snmp_interface_state_per_profile"),
        ),
        migrations.AddIndex(
            model_name="snmpinterfacestate",
            index=models.Index(fields=["profile", "status"], name="snmp_state_profile_status_idx"),
        ),
        migrations.AddIndex(
            model_name="snmpinterfacestate",
            index=models.Index(fields=["company", "last_seen_at"], name="snmp_state_company_seen_idx"),
        ),
        migrations.AddConstraint(
            model_name="snmpportbinding",
            constraint=models.UniqueConstraint(fields=("profile", "if_name"), name="unique_snmp_if_name_per_profile"),
        ),
        migrations.AddConstraint(
            model_name="snmpportbinding",
            constraint=models.UniqueConstraint(condition=Q(if_index__isnull=False), fields=("profile", "if_index"), name="unique_snmp_if_index_per_profile"),
        ),
        migrations.AddIndex(
            model_name="snmpportbinding",
            index=models.Index(fields=["profile", "enabled", "last_status"], name="snmp_bind_profile_status_idx"),
        ),
        migrations.AddIndex(
            model_name="snmpportbinding",
            index=models.Index(fields=["company", "role", "last_status"], name="snmp_bind_company_role_idx"),
        ),
        migrations.AddConstraint(
            model_name="monitorednetworklink",
            constraint=models.UniqueConstraint(condition=~Q(code=""), fields=("project", "code"), name="unique_monitored_link_code_per_project"),
        ),
        migrations.AddConstraint(
            model_name="monitorednetworklink",
            constraint=models.CheckConstraint(condition=~Q(source_element=models.F("destination_element")), name="monitored_link_distinct_elements"),
        ),
        migrations.AddIndex(
            model_name="monitorednetworklink",
            index=models.Index(fields=["project", "enabled", "status"], name="snmp_link_project_status_idx"),
        ),
        migrations.AddIndex(
            model_name="monitorednetworklink",
            index=models.Index(fields=["company", "status", "status_changed_at"], name="snmp_link_company_status_idx"),
        ),
    ]
