from django.db import migrations, models
import django.db.models.deletion


def migrate_legacy_splice_route_metadata(apps, schema_editor):
    NetworkElement = apps.get_model("network_map", "NetworkElement")
    NetworkRoute = apps.get_model("network_map", "NetworkRoute")
    Membership = apps.get_model("network_map", "NetworkRouteElementMembership")

    for element in NetworkElement.objects.filter(element_type="splice_box").iterator():
        metadata = element.metadata or {}
        route_ids = metadata.get("route_ids")
        if not isinstance(route_ids, list):
            route_ids = [metadata.get("route_id")] if metadata.get("route_id") else []
        for raw_route_id in route_ids:
            try:
                route_id = int(raw_route_id)
            except (TypeError, ValueError):
                continue
            route = NetworkRoute.objects.filter(
                pk=route_id,
                project_id=element.project_id,
                company_id=element.company_id,
            ).first()
            if route:
                Membership.objects.get_or_create(route_id=route.id, element_id=element.id)


class Migration(migrations.Migration):
    dependencies = [
        ("network_map", "0032_map_master_suite"),
    ]

    operations = [
        migrations.CreateModel(
            name="NetworkRouteElementMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "element",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="route_memberships",
                        to="network_map.networkelement",
                    ),
                ),
                (
                    "route",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="element_memberships",
                        to="network_map.networkroute",
                    ),
                ),
            ],
            options={
                "ordering": ["route", "element"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("route", "element"),
                        name="unique_element_membership_per_route",
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="ctosplitterport",
            name="direct_drop_cable",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cto_splitter_port",
                to="network_map.fibercable",
            ),
        ),
        migrations.AddField(
            model_name="ctosplitterport",
            name="direct_drop_label",
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.RunPython(
            migrate_legacy_splice_route_metadata,
            migrations.RunPython.noop,
        ),
    ]
