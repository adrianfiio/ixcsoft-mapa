from django.db import migrations
from django.db.models import Q


def classify_cdo_as_splice_box(apps, schema_editor):
    CTO = apps.get_model("network_map", "CTO")
    NetworkElement = apps.get_model("network_map", "NetworkElement")

    cdo_names = Q(name__icontains="CDO") | Q(name__iregex=r"C[\s._-]*D[\s._-]*O")
    CTO.objects.filter(
        cdo_names,
        code__startswith="IXC-CTO-",
    ).update(element_type="splice_box")
    NetworkElement.objects.filter(
        cdo_names,
        code__startswith="IXC-ELEM-",
    ).update(element_type="splice_box")


class Migration(migrations.Migration):
    dependencies = [
        ("network_map", "0017_remove_pending_ixc_cables"),
    ]

    operations = [
        migrations.RunPython(classify_cdo_as_splice_box, migrations.RunPython.noop),
    ]
