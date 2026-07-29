from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("network_map", "0013_fiber_termination_per_element"),
    ]

    operations = [
        migrations.AddField(
            model_name="pop",
            name="project",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cpd",
                to="network_map.networkproject",
                verbose_name="Projeto de rede",
            ),
        ),
        migrations.AlterModelOptions(
            name="pop",
            options={
                "ordering": ["name"],
                "verbose_name": "CPD / POP",
                "verbose_name_plural": "CPDs / POPs",
            },
        ),
        migrations.CreateModel(
            name="PoleCableAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("sequence", models.PositiveIntegerField(default=1, verbose_name="Sequência")),
                ("height_m", models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name="Altura (m)")),
                ("notes", models.CharField(blank=True, max_length=255, verbose_name="Observações")),
                ("cable", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pole_attachments", to="network_map.fibercable", verbose_name="Cabo")),
                ("pole", models.ForeignKey(limit_choices_to={"element_type": "pole"}, on_delete=django.db.models.deletion.CASCADE, related_name="cable_attachments", to="network_map.networkelement", verbose_name="Poste")),
            ],
            options={"ordering": ["cable", "sequence"], "verbose_name": "Passagem de cabo no poste", "verbose_name_plural": "Passagens de cabos nos postes"},
        ),
        migrations.CreateModel(
            name="PoleEquipmentAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("height_m", models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name="Altura (m)")),
                ("notes", models.CharField(blank=True, max_length=255, verbose_name="Observações")),
                ("equipment", models.OneToOneField(limit_choices_to={"element_type__in": ["cto", "splice_box"]}, on_delete=django.db.models.deletion.CASCADE, related_name="pole_attachment", to="network_map.networkelement", verbose_name="Equipamento")),
                ("pole", models.ForeignKey(limit_choices_to={"element_type": "pole"}, on_delete=django.db.models.deletion.CASCADE, related_name="equipment_attachments", to="network_map.networkelement", verbose_name="Poste")),
            ],
            options={"verbose_name": "Equipamento instalado no poste", "verbose_name_plural": "Equipamentos instalados nos postes"},
        ),
        migrations.AddConstraint(
            model_name="polecableattachment",
            constraint=models.UniqueConstraint(fields=("pole", "cable"), name="unique_cable_attachment_per_pole"),
        ),
    ]
