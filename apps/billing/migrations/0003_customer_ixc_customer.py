import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ixc_integration", "0008_sync_progress"),
        ("billing", "0002_gateway_configuration"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="ixc_customer",
            field=models.OneToOneField(
                blank=True,
                help_text="Vincula este cadastro financeiro a um cliente já sincronizado do IXCSoft.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="billing_customer",
                to="ixc_integration.ixccustomer",
                verbose_name="Cliente do ERP vinculado",
            ),
        ),
    ]
