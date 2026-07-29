from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("network_map", "0018_classify_ixc_cdo_as_splice_box"),
    ]

    operations = [
        migrations.AlterField(
            model_name="networkelement",
            name="element_type",
            field=models.CharField(
                choices=[
                    ("olt", "OLT"),
                    ("dio", "DIO"),
                    ("splice_box", "Caixa de emenda"),
                    ("cto", "CTO"),
                    ("pole", "Poste"),
                    ("rack", "Rack"),
                    ("tower", "Torre"),
                    ("switch", "Switch"),
                    ("access_point", "Access point"),
                    ("ptp", "Rádio PTP"),
                    ("cabinet", "Armário"),
                    ("other", "Outro"),
                ],
                max_length=30,
            ),
        ),
    ]
