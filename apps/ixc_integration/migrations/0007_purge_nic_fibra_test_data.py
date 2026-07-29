from django.db import migrations


def purge_nic_fibra(apps, schema_editor):
    Company = apps.get_model("core", "Company")
    Membership = apps.get_model("core", "CompanyMembership")
    company_ids = set(
        Company.objects.filter(name__icontains="Nic Fibra").values_list("id", flat=True)
    )
    company_ids.update(
        Company.objects.filter(trade_name__icontains="Nic Fibra").values_list("id", flat=True)
    )
    company_ids.update(
        Membership.objects.filter(user__username__iexact="eduardo.mota").values_list(
            "company_id", flat=True
        )
    )
    if not company_ids:
        return

    # O reset é proposital e limitado ao ambiente de teste Nic Fibra/Eduardo.
    apps.get_model("access", "AccessPoint").objects.filter(company_id__in=company_ids).delete()
    apps.get_model("ixc_integration", "IXCFiberAssignment").objects.filter(company_id__in=company_ids).delete()
    apps.get_model("ixc_integration", "IXCLogin").objects.filter(company_id__in=company_ids).delete()
    apps.get_model("ixc_integration", "IXCContract").objects.filter(company_id__in=company_ids).delete()
    apps.get_model("ixc_integration", "IXCCustomer").objects.filter(company_id__in=company_ids).delete()
    apps.get_model("ixc_integration", "IXCConfiguration").objects.filter(company_id__in=company_ids).delete()
    apps.get_model("network_map", "NetworkProject").objects.filter(company_id__in=company_ids).delete()
    apps.get_model("network_map", "POP").objects.filter(company_id__in=company_ids).delete()
    Company.objects.filter(id__in=company_ids).update(
        onboarding_completed=False,
        integration_mode="",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("ixc_integration", "0006_reset_nic_fibra_onboarding"),
        ("network_map", "0015_ixc_company_import_keys"),
        ("access", "0002_add_ftth_fields"),
    ]
    operations = [migrations.RunPython(purge_nic_fibra, migrations.RunPython.noop)]
