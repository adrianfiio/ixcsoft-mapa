from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("access", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="accesspoint",
            name="ixc_customer_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=80,
                verbose_name="ID Cliente IXC",
            ),
        ),
        migrations.AddField(
            model_name="accesspoint",
            name="ixc_contract_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=80,
                verbose_name="ID Contrato IXC",
            ),
        ),
        migrations.AddField(
            model_name="accesspoint",
            name="onu_mac",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=80,
                verbose_name="MAC ONU",
            ),
        ),
        migrations.AddField(
            model_name="accesspoint",
            name="cto_ixc_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=80,
                verbose_name="ID CTO IXC",
            ),
        ),
        migrations.AddField(
            model_name="accesspoint",
            name="ftth_port",
            field=models.CharField(
                blank=True,
                max_length=30,
                verbose_name="Porta FTTH",
            ),
        ),
        migrations.AddField(
            model_name="accesspoint",
            name="concentrator_id",
            field=models.CharField(
                blank=True,
                max_length=80,
                verbose_name="ID Concentrador",
            ),
        ),
        migrations.AddField(
            model_name="accesspoint",
            name="concentrator",
            field=models.CharField(
                blank=True,
                max_length=120,
                verbose_name="Concentrador",
            ),
        ),
        migrations.AddField(
            model_name="accesspoint",
            name="interface_transmission",
            field=models.CharField(
                blank=True,
                max_length=120,
                verbose_name="Interface transmissão",
            ),
        ),
        migrations.AddField(
            model_name="accesspoint",
            name="connection_type",
            field=models.CharField(
                blank=True,
                max_length=80,
                verbose_name="Tipo conexão",
            ),
        ),
        migrations.AddField(
            model_name="accesspoint",
            name="last_connection_start",
            field=models.DateTimeField(
                blank=True,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="accesspoint",
            name="last_connection_end",
            field=models.DateTimeField(
                blank=True,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="accesspoint",
            name="disconnect_reason",
            field=models.CharField(
                blank=True,
                max_length=255,
            ),
        ),
    ]
