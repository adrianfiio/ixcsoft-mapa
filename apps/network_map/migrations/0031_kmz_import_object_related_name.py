from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """`KMZImportObject.batch` usava related_name="objects", que sobrescrevia
    o manager padrão `KMZImportBatch.objects` (o Django troca o atributo de
    classe pelo descriptor da relação reversa) — qualquer
    `KMZImportBatch.objects.filter/create/...` quebrava com
    `AttributeError: 'ReverseManyToOneDescriptor' object has no attribute`.
    Sem mudança de coluna no banco; só corrige o nome do acessor reverso."""

    dependencies = [("network_map", "0030_kmz_import_v04")]

    operations = [
        migrations.AlterField(
            model_name="kmzimportobject",
            name="batch",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tracked_objects",
                to="network_map.kmzimportbatch",
            ),
        ),
    ]
