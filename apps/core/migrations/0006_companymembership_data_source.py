from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0005_company_onboarding")]
    operations = [
        migrations.AddField(
            model_name="companymembership",
            name="data_source",
            field=models.CharField(
                choices=[("manual", "Usuário padrão — sem ERP"), ("erp", "Usuário vinculado a ERP")],
                default="manual",
                max_length=20,
                verbose_name="Origem dos dados",
            ),
        ),
        migrations.AddField(
            model_name="companymembership",
            name="erp_provider",
            field=models.CharField(blank=True, max_length=30, verbose_name="ERP vinculado"),
        ),
        migrations.AddField(
            model_name="companymembership",
            name="erp_configuration_id",
            field=models.PositiveBigIntegerField(blank=True, null=True, verbose_name="ID da configuração ERP"),
        ),
    ]
