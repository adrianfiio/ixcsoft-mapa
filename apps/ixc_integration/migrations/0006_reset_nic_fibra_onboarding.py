from django.db import migrations


def reset_nic_fibra(apps, schema_editor):
    Company = apps.get_model("core", "Company")
    IXCConfiguration = apps.get_model("ixc_integration", "IXCConfiguration")
    company_ids = list(
        Company.objects.filter(name__iexact="Nic Fibra Telecom").values_list("id", flat=True)
    )
    company_ids += list(
        Company.objects.filter(trade_name__iexact="Nic Fibra Telecom").values_list("id", flat=True)
    )
    companies = Company.objects.filter(id__in=set(company_ids))
    IXCConfiguration.objects.filter(company__in=companies).delete()
    companies.update(onboarding_completed=False, integration_mode="")


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_company_onboarding"),
        ("ixc_integration", "0005_ixc_contracts"),
    ]
    operations = [migrations.RunPython(reset_nic_fibra, migrations.RunPython.noop)]
