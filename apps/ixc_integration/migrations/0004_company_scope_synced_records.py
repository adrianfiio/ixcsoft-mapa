import django.db.models.deletion
from django.db import migrations, models


def assign_existing_company(apps, schema_editor):
    configuration = apps.get_model("ixc_integration", "IXCConfiguration").objects.exclude(company=None).first()
    if not configuration:
        return
    company_id = configuration.company_id
    apps.get_model("ixc_integration", "IXCCustomer").objects.filter(company=None).update(company_id=company_id)
    apps.get_model("ixc_integration", "IXCLogin").objects.filter(company=None).update(company_id=company_id)
    apps.get_model("ixc_integration", "IXCFiberAssignment").objects.filter(company=None).update(company_id=company_id)


class Migration(migrations.Migration):
    dependencies = [("core", "0004_company_roles_view_edit"), ("ixc_integration", "0003_erp_onboarding_options")]

    operations = [
        migrations.AddField(model_name="ixccustomer", name="company", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="ixc_customers", to="core.company")),
        migrations.AddField(model_name="ixclogin", name="company", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="ixc_logins", to="core.company")),
        migrations.AddField(model_name="ixcfiberassignment", name="company", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="ixc_fiber_assignments", to="core.company")),
        migrations.RunPython(assign_existing_company, migrations.RunPython.noop),
        migrations.AlterField(model_name="ixccustomer", name="ixc_customer_id", field=models.CharField(max_length=80)),
        migrations.AlterField(model_name="ixclogin", name="ixc_login_id", field=models.CharField(max_length=80)),
        migrations.AlterField(model_name="ixcfiberassignment", name="ixc_id", field=models.CharField(db_index=True, max_length=80)),
        migrations.AddConstraint(model_name="ixccustomer", constraint=models.UniqueConstraint(fields=("company", "ixc_customer_id"), name="unique_ixc_customer_per_company")),
        migrations.AddConstraint(model_name="ixclogin", constraint=models.UniqueConstraint(fields=("company", "ixc_login_id"), name="unique_ixc_login_per_company")),
        migrations.AddConstraint(model_name="ixcfiberassignment", constraint=models.UniqueConstraint(fields=("company", "ixc_id"), name="unique_ixc_fiber_per_company")),
    ]
