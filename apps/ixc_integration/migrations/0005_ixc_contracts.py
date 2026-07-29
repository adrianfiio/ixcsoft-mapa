import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ixc_integration", "0004_company_scope_synced_records"),
    ]

    operations = [
        migrations.CreateModel(
            name="IXCContract",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("ixc_contract_id", models.CharField(max_length=80)),
                ("status", models.CharField(blank=True, max_length=30)),
                ("active", models.BooleanField(db_index=True, default=True)),
                ("description", models.CharField(blank=True, max_length=255)),
                ("raw_data", models.JSONField(blank=True, default=dict)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ixc_contracts", to="core.company")),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="contracts", to="ixc_integration.ixccustomer")),
            ],
            options={"ordering": ["customer__name", "ixc_contract_id"]},
        ),
        migrations.AddConstraint(
            model_name="ixccontract",
            constraint=models.UniqueConstraint(fields=("company", "ixc_contract_id"), name="unique_ixc_contract_per_company"),
        ),
        migrations.AddField(
            model_name="ixclogin",
            name="contract",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="logins", to="ixc_integration.ixccontract"),
        ),
    ]
