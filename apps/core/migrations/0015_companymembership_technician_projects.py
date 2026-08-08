from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_company_membership_technician_role"),
        ("network_map", "0033_route_memberships_and_cto_drop_ports"),
    ]

    operations = [
        migrations.AddField(
            model_name="companymembership",
            name="technician_projects",
            field=models.ManyToManyField(
                blank=True,
                related_name="technician_members",
                to="network_map.networkproject",
                verbose_name="Projetos liberados para o técnico",
            ),
        ),
    ]
