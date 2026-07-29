from django.db import migrations


def remove_pending_ixc_cables(apps, schema_editor):
    FiberCable = apps.get_model("network_map", "FiberCable")
    NetworkElement = apps.get_model("network_map", "NetworkElement")
    FiberCable.objects.filter(code__startswith="IXC-CAB-").delete()
    for element in NetworkElement.objects.filter(code__startswith="IXC-ELEM-").iterator():
        normalized_name = (element.name or "").upper()
        if "CABO" in normalized_name or "CABLE" in normalized_name:
            element.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("network_map", "0016_fibercable_optional_geometry"),
    ]

    operations = [
        migrations.RunPython(remove_pending_ixc_cables, migrations.RunPython.noop),
    ]
