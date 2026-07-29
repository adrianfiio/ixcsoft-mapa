from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.access.models import AccessPoint
from apps.core.models import Company
from apps.ixc_integration.fiber_models import IXCFiberAssignment
from apps.ixc_integration.models import IXCContract, IXCCustomer, IXCLogin, IXCSyncExecution
from apps.network_map.models import CTO, NetworkElement, NetworkProject


class Command(BaseCommand):
    help = (
        "Apaga somente dados importados do ERP de uma empresa, preservando empresa, "
        "usuários, acessos, configuração/token do ERP e estrutura criada manualmente."
    )

    def add_arguments(self, parser):
        parser.add_argument("--company-slug", required=True)
        parser.add_argument("--confirm", default="")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        slug = options["company_slug"]
        company = Company.objects.filter(slug=slug).first()
        if not company:
            raise CommandError(f"Empresa não encontrada: {slug}")
        if not options["dry_run"] and options["confirm"] != slug:
            raise CommandError(f"Confirme o alvo com --confirm {slug}")

        imported_projects = NetworkProject.objects.filter(
            company=company
        ).exclude(ixc_project_id="")
        imported_elements = NetworkElement.objects.filter(
            company=company
        ).filter(code__startswith="IXC-")
        imported_ctos = CTO.objects.filter(
            company=company, ixc_box_id__isnull=False
        ).exclude(ixc_box_id="")
        targets = [
            ("Pontos de acesso", AccessPoint.objects.filter(company=company, source="ixc")),
            ("Vínculos de fibra/ONU", IXCFiberAssignment.objects.filter(company=company)),
            ("Logins PPPoE", IXCLogin.objects.filter(company=company)),
            ("Contratos", IXCContract.objects.filter(company=company)),
            ("Clientes", IXCCustomer.objects.filter(company=company)),
            ("Execuções de sincronização", IXCSyncExecution.objects.filter(configuration__company=company)),
            ("CTOs importadas", imported_ctos),
            ("Elementos importados", imported_elements),
            ("Projetos importados", imported_projects),
        ]
        self.stdout.write(f"Empresa: {company} ({company.slug})")
        for label, queryset in targets:
            self.stdout.write(f"- {label}: {queryset.count()}")
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Simulação concluída; nenhum registro foi removido."))
            return

        with transaction.atomic():
            # Dependências primeiro; querysets posteriores podem já estar vazios por CASCADE.
            for _, queryset in targets:
                queryset.delete()
            company.ixc_configurations.update(
                last_sync_at=None,
                last_sync_status="",
                last_sync_message="",
            )
        self.stdout.write(self.style.SUCCESS(
            "Limpeza concluída. Empresa, usuários, acessos e configuração ERP foram preservados."
        ))
