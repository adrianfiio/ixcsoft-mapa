import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0011_platformdashboardlayout")]

    operations = [
        migrations.AddField(
            model_name="company",
            name="logo",
            field=models.ImageField(
                blank=True,
                help_text="Substitui a logo padrão na barra lateral para os usuários desta empresa.",
                null=True,
                upload_to="company_logos/",
                verbose_name="Logo (whitelabel)",
            ),
        ),
        migrations.AddField(
            model_name="company",
            name="brand_color",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Substitui a cor de destaque padrão para os usuários desta empresa.",
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        "^#[0-9A-Fa-f]{6}$", "Use o formato #RRGGBB."
                    )
                ],
                verbose_name="Cor de destaque (whitelabel)",
            ),
        ),
    ]
