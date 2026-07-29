from django.db import migrations


def cleanup_duplicate_links(apps, schema_editor):
    FiberSplice = apps.get_model("network_map", "FiberSplice")
    Splitter = apps.get_model("network_map", "SpliceTraySplitter")
    Port = apps.get_model("network_map", "SpliceTraySplitterPort")
    used = set()
    for splice in FiberSplice.objects.order_by("id"):
        if splice.input_fiber_id in used or splice.output_fiber_id in used:
            splice.delete()
            continue
        used.update([splice.input_fiber_id, splice.output_fiber_id])
    for splitter in Splitter.objects.exclude(input_fiber=None).order_by("id"):
        if splitter.input_fiber_id in used:
            splitter.input_fiber = None
            splitter.save(update_fields=["input_fiber"])
        else:
            used.add(splitter.input_fiber_id)
    for port in Port.objects.exclude(output_fiber=None).order_by("id"):
        if port.output_fiber_id in used:
            port.output_fiber = None
            port.save(update_fields=["output_fiber"])
        else:
            used.add(port.output_fiber_id)


class Migration(migrations.Migration):
    dependencies = [("network_map", "0011_splice_splitter_ports")]
    operations = [
        migrations.RunPython(cleanup_duplicate_links, migrations.RunPython.noop),
    ]
