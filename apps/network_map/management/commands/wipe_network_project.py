from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.network_map.kmz_import_models import KMZImportBatch
from apps.network_map.models import (
    FiberCable,
    NetworkElement,
    NetworkProject,
    NetworkRoute,
    POP,
)


class Command(BaseCommand):
    help = (
        "Apaga toda a estrutura de rede de UM projeto (postes, CTOs, cabos, "
        "tubos/fibras, splitters, fusões, reservas, lotes de importação KMZ), "
        "preservando o projeto em si (nome, código, empresa). Ação destrutiva "
        "e irreversível — sempre rode antes sem --confirm para ver a contagem."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "project",
            help="Nome ou código exato do projeto, como aparece no seletor do mapa.",
        )
        parser.add_argument(
            "--confirm",
            default="",
            help="Repita o código do projeto (mostrado na simulação) para confirmar.",
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        name = options["project"]
        matches = list(
            NetworkProject.objects.filter(Q(name__iexact=name) | Q(code__iexact=name))
        )
        if not matches:
            raise CommandError(f'Nenhum projeto encontrado com nome/código "{name}".')
        if len(matches) > 1:
            details = ", ".join(f"#{p.pk} {p.name} ({p.code})" for p in matches)
            raise CommandError(
                f'Mais de um projeto bateu com "{name}": {details}. '
                "Rode de novo usando o código exato de um deles."
            )
        project = matches[0]

        if not options["dry_run"] and options["confirm"] != project.code:
            raise CommandError(f"Confirme o alvo com --confirm {project.code}")

        targets = [
            ("Lotes de importação KMZ", KMZImportBatch.objects.filter(project=project)),
            (
                "Cabos (tubos, fibras, reservas e passagens ligados a eles)",
                FiberCable.objects.filter(project=project),
            ),
            (
                "Elementos (postes, CTOs, CEOs/CDOs, racks, DIOs, OLTs, splitters, fusões...)",
                NetworkElement.objects.filter(project=project),
            ),
            ("Rotas", NetworkRoute.objects.filter(project=project)),
            ("POP", POP.objects.filter(project=project)),
        ]

        self.stdout.write(f"Projeto: {project.name} ({project.code})")
        for label, queryset in targets:
            self.stdout.write(f"- {label}: {queryset.count()}")

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING("Simulação concluída; nenhum registro foi removido.")
            )
            return

        with transaction.atomic():
            # Cabos antes dos elementos: limpa reservas/passagens/tubos/fibras
            # ligados a eles por CASCADE antes de remover o restante da estrutura.
            for _, queryset in targets:
                queryset.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f'Projeto "{project.name}" zerado. O projeto continua existindo, vazio.'
            )
        )
