from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("network_map", "0014_cpd_and_pole_attachments"),
    ]

    operations = [
        migrations.AddField(
            model_name="networkproject",
            name="ixc_project_id",
            field=models.CharField(blank=True, db_index=True, max_length=80),
        ),
        migrations.AlterField(
            model_name="cto",
            name="ixc_box_id",
            field=models.CharField(blank=True, db_index=True, max_length=80, null=True),
        ),
        migrations.AddConstraint(
            model_name="networkproject",
            constraint=models.UniqueConstraint(condition=~models.Q(ixc_project_id=""), fields=("company", "ixc_project_id"), name="unique_ixc_project_per_company"),
        ),
    ]
