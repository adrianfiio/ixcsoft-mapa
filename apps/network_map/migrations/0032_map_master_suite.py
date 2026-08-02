import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_dashboard_widget_layout'),
        ('network_map', '0031_kmz_import_object_related_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='containerequipment',
            name='equipment_type',
            field=models.CharField(choices=[('olt', 'OLT'), ('dio', 'DIO'), ('switch', 'Switch'), ('router', 'Roteador'), ('firewall', 'Firewall'), ('server', 'Servidor'), ('access_point', 'Access point'), ('ptp', 'Rádio PTP'), ('onu', 'ONU / ONT'), ('pto', 'PTO'), ('other', 'Outro')], max_length=30),
        ),
        migrations.AlterField(
            model_name='containerequipmentport',
            name='port_type',
            field=models.CharField(choices=[('pon', 'PON'), ('dio', 'Porta de DIO'), ('rj45_100m', 'RJ45 100 Mb'), ('rj45_1g', 'RJ45 1 Gb'), ('rj45_2g5', 'RJ45 2.5 Gb'), ('sfp_1g', 'SFP 1 Gb'), ('sfp_plus_10g', 'SFP+ 10 Gb'), ('sfp28_25g', 'SFP28 25 Gb'), ('qsfp_plus_40g', 'QSFP+ 40 Gb'), ('qsfp28_100g', 'QSFP28 100 Gb'), ('sc_apc', 'SC/APC'), ('sc_upc', 'SC/UPC'), ('lc', 'LC'), ('wireless', 'Interface wireless'), ('power', 'Energia')], max_length=20),
        ),
        migrations.CreateModel(
            name='MapIconStyle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('element_type', models.CharField(db_index=True, max_length=40)),
                ('subtype', models.CharField(blank=True, db_index=True, max_length=40)),
                ('display_name', models.CharField(max_length=80)),
                ('svg_markup', models.TextField(blank=True)),
                ('image_url', models.URLField(blank=True)),
                ('foreground_color', models.CharField(default='#e6edf7', max_length=16)),
                ('background_color', models.CharField(default='#0f1f33', max_length=16)),
                ('border_color', models.CharField(default='#53c7ff', max_length=16)),
                ('size_px', models.PositiveSmallIntegerField(default=30, validators=[django.core.validators.MinValueValidator(16), django.core.validators.MaxValueValidator(96)])),
                ('show_label', models.BooleanField(default=True)),
                ('show_name_inside_icon', models.BooleanField(default=False)),
                ('enabled', models.BooleanField(default=True)),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core.company')),
            ],
            options={
                'verbose_name': 'Estilo de ícone do mapa',
                'verbose_name_plural': 'Estilos de ícones do mapa',
                'ordering': ('element_type', 'subtype', 'display_name'),
            },
        ),
        migrations.CreateModel(
            name='MapDiagramRevision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('diagram_type', models.CharField(choices=[('fusion', 'Fusões'), ('container', 'POP/Rack/Torre'), ('route', 'Rota óptica')], max_length=20)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('note', models.CharField(blank=True, max_length=240)),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core.company')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='map_diagram_revisions', to=settings.AUTH_USER_MODEL)),
                ('element', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='map_diagram_revisions', to='network_map.networkelement')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='map_diagram_revisions', to='network_map.networkproject')),
            ],
            options={
                'verbose_name': 'Revisão de diagrama',
                'verbose_name_plural': 'Revisões de diagramas',
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='NetworkAssetLifecycle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('asset_type', models.CharField(choices=[('element', 'Elemento'), ('cable', 'Cabo'), ('equipment', 'Equipamento'), ('link', 'Ligação'), ('splitter_port', 'Porta de splitter')], max_length=24)),
                ('asset_id', models.PositiveBigIntegerField()),
                ('stage', models.CharField(choices=[('planning', 'Em projeto'), ('not_deployed', 'Não implantado'), ('deployed', 'Implantado'), ('certified', 'Certificado'), ('disabled', 'Desativado')], default='planning', max_length=24)),
                ('note', models.TextField(blank=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='map_asset_lifecycle_events', to=settings.AUTH_USER_MODEL)),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='core.company')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='asset_lifecycle_events', to='network_map.networkproject')),
            ],
            options={
                'verbose_name': 'Histórico de implantação',
                'verbose_name_plural': 'Histórico de implantação',
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddIndex(
            model_name='mapdiagramrevision',
            index=models.Index(fields=['project', 'diagram_type', 'created_at'], name='network_map_project_9d0a41_idx'),
        ),
        migrations.AddIndex(
            model_name='mapdiagramrevision',
            index=models.Index(fields=['element', 'diagram_type', 'created_at'], name='network_map_element_5f7b2a_idx'),
        ),
        migrations.AddIndex(
            model_name='networkassetlifecycle',
            index=models.Index(fields=['project', 'asset_type', 'asset_id', 'created_at'], name='network_map_project_3c8e6d_idx'),
        ),
        migrations.AddIndex(
            model_name='networkassetlifecycle',
            index=models.Index(fields=['stage', 'created_at'], name='network_map_stage_e1a4b9_idx'),
        ),
        migrations.AddConstraint(
            model_name='mapiconstyle',
            constraint=models.UniqueConstraint(fields=('company', 'element_type', 'subtype'), name='unique_map_icon_style_per_company_type'),
        ),
    ]
