from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ixc_integration", "0002_ixcconfiguration_company")]

    operations = [
        migrations.AddField(model_name="ixcconfiguration", name="provider", field=models.CharField(choices=[("ixcsoft", "IXCSoft")], default="ixcsoft", max_length=30)),
        migrations.AddField(model_name="ixcconfiguration", name="sync_active_contracts_only", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="ixcconfiguration", name="sync_customers", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="ixcconfiguration", name="sync_pppoe", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="ixcconfiguration", name="sync_projects", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ixcconfiguration", name="sync_ctos", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ixcconfiguration", name="sync_map_elements", field=models.BooleanField(default=False)),
        migrations.AddConstraint(
            model_name="ixcconfiguration",
            constraint=models.UniqueConstraint(fields=("company", "provider"), name="unique_erp_provider_per_company"),
        ),
    ]
