from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0004_company_roles_view_edit")]
    operations = [
        migrations.AddField(model_name="company", name="address", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="company", name="contact_email", field=models.EmailField(blank=True, max_length=254)),
        migrations.AddField(model_name="company", name="contact_name", field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name="company", name="contact_phone", field=models.CharField(blank=True, max_length=40)),
        migrations.AddField(model_name="company", name="integration_mode", field=models.CharField(blank=True, choices=[("erp", "Usar com ERP"), ("manual", "Usar sem ERP")], max_length=20)),
        migrations.AddField(model_name="company", name="onboarding_completed", field=models.BooleanField(default=False)),
    ]
