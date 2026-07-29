from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.models import Company
from apps.network_map.models import (
    CableModel,
    FiberColor,
    FiberColorStandard,
    FiberColorStandardItem,
)


COLORS = [
    ("green", "Verde", "#00B050", "#000000"),
    ("yellow", "Amarelo", "#FFFF00", "#000000"),
    ("white", "Branco", "#FFFFFF", "#000000"),
    ("blue", "Azul", "#00A6D6", "#000000"),
    ("red", "Vermelho", "#FF0000", "#000000"),
    ("violet", "Violeta", "#7030A0", "#FFFFFF"),
    ("brown", "Marrom", "#996633", "#000000"),
    ("pink", "Rosa", "#FF3399", "#000000"),
    ("black", "Preto", "#000000", "#FFFFFF"),
    ("gray", "Cinza", "#808080", "#000000"),
    ("orange", "Laranja", "#FF9900", "#000000"),
    ("aqua", "Água", "#00E5E5", "#000000"),
]


CABLES = [
    ("DROP 1F", CableModel.Construction.DROP, 1, 1),
    ("DROP 2F", CableModel.Construction.DROP, 2, 2),
    ("AS 2F", CableModel.Construction.OTHER, 2, 2),
    ("AS 6F", CableModel.Construction.OTHER, 6, 6),
    ("AS 8F", CableModel.Construction.OTHER, 8, 8),
    ("AS 12F", CableModel.Construction.OTHER, 12, 12),
    ("LOOSE TUBE 12F", CableModel.Construction.LOOSE_TUBE, 12, 12),
    ("LOOSE TUBE 24F", CableModel.Construction.LOOSE_TUBE, 24, 12),
    ("LOOSE TUBE 48F", CableModel.Construction.LOOSE_TUBE, 48, 12),
    ("LOOSE TUBE 72F", CableModel.Construction.LOOSE_TUBE, 72, 12),
    ("LOOSE TUBE 96F", CableModel.Construction.LOOSE_TUBE, 96, 12),
    ("LOOSE TUBE 144F", CableModel.Construction.LOOSE_TUBE, 144, 12),
    ("LOOSE TUBE 288F", CableModel.Construction.LOOSE_TUBE, 288, 12),
]


class Command(BaseCommand):
    help = "Cria o catálogo inicial de cores e cabos ópticos."

    def add_arguments(self, parser):
        parser.add_argument("--company-slug", default="nicfibra")

    def get_company(self, slug):
        try:
            return Company.objects.get(slug=slug, active=True)
        except Company.DoesNotExist as exc:
            raise CommandError(
                f"Empresa ativa com slug '{slug}' não encontrada."
            ) from exc

    @transaction.atomic
    def handle(self, *args, **options):
        company = self.get_company(options["company_slug"])

        self.stdout.write(
            f"Empresa: {company.trade_name} — ID {company.pk}"
        )

        colors = {}

        for position, data in enumerate(COLORS, start=1):
            code, name, hex_color, text_color = data

            color, created = FiberColor.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "hex_color": hex_color,
                    "text_color": text_color,
                    "order": position,
                },
            )

            colors[position] = color

            self.stdout.write(
                f"{position:02d}. {name}: "
                f"{'criada' if created else 'atualizada'}"
            )

        standard, created = FiberColorStandard.objects.update_or_create(
            company=company,
            code="ABNT-12",
            defaults={
                "name": "Padrão ABNT de 12 cores",
                "description": (
                    "Sequência de 12 cores para fibras e tubos ópticos."
                ),
            },
        )

        for position, color in colors.items():
            FiberColorStandardItem.objects.update_or_create(
                standard=standard,
                position=position,
                defaults={"color": color},
            )

        self.stdout.write(
            f"Padrão ABNT-12: "
            f"{'criado' if created else 'atualizado'}"
        )

        for model, construction, fiber_count, fibers_per_tube in CABLES:
            tube_count = max(
                1,
                (fiber_count + fibers_per_tube - 1) // fibers_per_tube,
            )

            cable, created = CableModel.objects.update_or_create(
                company=company,
                manufacturer="Genérico",
                model=model,
                defaults={
                    "name": model,
                    "construction": construction,
                    "fiber_count": fiber_count,
                    "tube_count": tube_count,
                    "fibers_per_tube": fibers_per_tube,
                    "color_standard": standard,
                    "metadata": {
                        "catalog_seed": True,
                    },
                },
            )

            self.stdout.write(
                f"{cable.model}: "
                f"{'criado' if created else 'atualizado'} — "
                f"{fiber_count}F / {tube_count} tubo(s)"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Catálogo óptico carregado com sucesso."
            )
        )
