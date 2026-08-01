import django.db.models.deletion
from django.db import migrations, models

import apps.snmp_monitoring.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0013_dashboard_widget_layout'),
        ('network_map', '0031_kmz_import_object_related_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='SNMPMonitoringProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('enabled', models.BooleanField(default=True)),
                ('management_ip', models.GenericIPAddressField()),
                ('port', models.PositiveIntegerField(default=161)),
                ('snmp_version', models.CharField(choices=[('2c', 'SNMP v2c')], default='2c', max_length=10)),
                ('community_encrypted', models.TextField(blank=True)),
                ('polling_interval_seconds', models.PositiveIntegerField(default=60)),
                ('influx_id', models.CharField(default=apps.snmp_monitoring.models._generate_influx_id, editable=False, max_length=32, unique=True)),
                ('last_poll_at', models.DateTimeField(blank=True, null=True)),
                ('last_poll_message', models.TextField(blank=True)),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core.company')),
                ('element', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='snmp_monitoring', to='network_map.networkelement')),
            ],
            options={
                'verbose_name': 'Monitoramento SNMP',
                'verbose_name_plural': 'Monitoramentos SNMP',
            },
        ),
        migrations.AddIndex(
            model_name='snmpmonitoringprofile',
            index=models.Index(fields=['enabled'], name='snmp_monito_enabled_1a2b3c_idx'),
        ),
    ]
