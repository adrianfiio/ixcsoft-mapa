from django.contrib.gis.db import models
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("network_map", "0015_ixc_company_import_keys"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fibercable",
            name="geometry",
            field=models.MultiLineStringField(blank=True, null=True, srid=4326),
        ),
    ]
