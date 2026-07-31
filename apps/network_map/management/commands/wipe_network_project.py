from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from apps.network_map.models import NetworkProject
from apps.network_map.services import project_structure_counts, wipe_project_structure

LABELS = {
    "kmz_batches": "Lotes de importação KMZ",
    "cables": "Cabos (tubos, fibras, reservas e passagens ligados a eles)",
    "elements": "Elementos (postes, CTOs, CEOs/CDOs, racks, DIOs, OLTs, splitters, fusões...)",
    "routes": "Rotas",
    "pop": "POP",
}


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

        self.stdout.write(f"Projeto: {project.name} ({project.code})")
        for key, count in project_structure_counts(project).items():
            self.stdout.write(f"- {LABELS.get(key, key)}: {count}")

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING("Simulação concluída; nenhum registro foi removido.")
            )
            return

        wipe_project_structure(project)

        self.stdout.write(
            self.style.SUCCESS(
                f'Projeto "{project.name}" zerado. O projeto continua existindo, vazio.'
            )
        )
