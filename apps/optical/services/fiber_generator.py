from django.db import transaction

from apps.network_map.models import (
    FiberStrand,
    FiberTube,
)


class FiberGenerator:
    def __init__(self, cable):
        self.cable = cable

    @transaction.atomic
    def generate(self):
        # Não gera novamente se já existir estrutura
        if self.cable.tubes.exists():
            return

        model = self.cable.cable_model

        if not model:
            raise ValueError("O cabo precisa possuir um modelo cadastrado.")

        if not model.color_standard:
            raise ValueError("O modelo do cabo não possui padrão de cores.")

        colors = list(
            model.color_standard.items.select_related("color").order_by("position")
        )

        if len(colors) < model.fibers_per_tube:
            raise ValueError("O padrão de cores está incompleto.")

        fiber_number = 1

        for tube_number in range(1, model.tube_count + 1):
            tube = FiberTube.objects.create(
                cable=self.cable,
                number=tube_number,
                color=colors[(tube_number - 1) % len(colors)].color,
                identification=f"T{tube_number:02d}",
            )

            for position in range(1, model.fibers_per_tube + 1):
                FiberStrand.objects.create(
                    cable=self.cable,
                    tube=tube,
                    number=fiber_number,
                    position_in_tube=position,
                    color=colors[position - 1].color,
                )

                fiber_number += 1
