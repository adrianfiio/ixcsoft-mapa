from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from .models import (
    FiberCable,
    FiberColor,
    FiberSplice,
    FiberStrand,
    FiberTube,
    KMZImportBatch,
    NetworkElement,
    NetworkRoute,
    POP,
)


class FiberStructureError(Exception):
    """Erro durante a geração da estrutura interna do cabo."""


def get_color_sequence(cable):
    """
    Retorna a sequência de cores associada ao modelo do cabo.

    Caso o modelo não tenha um padrão configurado, utiliza as cores
    cadastradas ordenadas pelo campo 'order'.
    """
    cable_model = cable.cable_model

    if cable_model and cable_model.color_standard:
        items = (
            cable_model.color_standard.items
            .select_related("color")
            .order_by("position")
        )

        colors = [item.color for item in items]

        if colors:
            return colors

    colors = list(FiberColor.objects.order_by("order", "id"))

    if not colors:
        raise FiberStructureError(
            "Nenhuma cor de fibra foi cadastrada."
        )

    return colors


def validate_cable_model(cable):
    if not cable.cable_model:
        raise FiberStructureError(
            "O cabo precisa possuir um modelo para gerar tubos e fibras."
        )

    model = cable.cable_model

    if model.fiber_count <= 0:
        raise FiberStructureError(
            "O modelo do cabo possui quantidade de fibras inválida."
        )

    if model.fibers_per_tube <= 0:
        raise FiberStructureError(
            "O modelo do cabo possui fibras por tubo inválidas."
        )

    if model.tube_count <= 0:
        raise FiberStructureError(
            "O modelo do cabo possui quantidade de tubos inválida."
        )


@transaction.atomic
def generate_cable_fibers(cable, force=False):
    """
    Gera tubos e fibras conforme o modelo associado ao cabo.

    force=False:
        Não recria se já existirem tubos ou fibras.

    force=True:
        Apaga a estrutura existente e recria tudo.
        Não deve ser utilizado quando existirem fusões.
    """
    if not isinstance(cable, FiberCable):
        raise FiberStructureError("Cabo inválido.")

    cable = (
        FiberCable.objects
        .select_for_update()
        .get(pk=cable.pk)
    )

    validate_cable_model(cable)

    existing_tubes = cable.tubes.exists()
    existing_fibers = cable.fibers.exists()

    if existing_tubes or existing_fibers:
        if not force:
            raise FiberStructureError(
                "Este cabo já possui tubos ou fibras gerados."
            )

        has_splices = cable.fibers.filter(
            splice_output__isnull=False
        ).exists() or cable.fibers.filter(
            splice_input__isnull=False
        ).exists()

        if has_splices:
            raise FiberStructureError(
                "Não é possível recriar as fibras porque existem fusões."
            )

        cable.fibers.all().delete()
        cable.tubes.all().delete()

    model = cable.cable_model
    colors = get_color_sequence(cable)

    total_fibers = model.fiber_count
    fibers_per_tube = model.fibers_per_tube

    created_tubes = []
    created_fibers = []

    global_fiber_number = 1

    for tube_number in range(1, model.tube_count + 1):
        if global_fiber_number > total_fibers:
            break

        tube_color = colors[
            (tube_number - 1) % len(colors)
        ]

        tube = FiberTube.objects.create(
            cable=cable,
            number=tube_number,
            color=tube_color,
            identification=f"Tubo {tube_number}",
        )

        created_tubes.append(tube)

        for position_in_tube in range(
            1,
            fibers_per_tube + 1,
        ):
            if global_fiber_number > total_fibers:
                break

            fiber_color = colors[
                (position_in_tube - 1) % len(colors)
            ]

            fiber = FiberStrand(
                cable=cable,
                tube=tube,
                number=global_fiber_number,
                position_in_tube=position_in_tube,
                color=fiber_color,
                status=FiberStrand.Status.FREE,
                origin_element=cable.origin,
                destination_element=cable.destination,
            )

            created_fibers.append(fiber)
            global_fiber_number += 1

    if len(created_fibers) != total_fibers:
        raise FiberStructureError(
            (
                f"O modelo prevê {total_fibers} fibras, mas a configuração "
                f"de tubos permite gerar apenas {len(created_fibers)}."
            )
        )

    FiberStrand.objects.bulk_create(created_fibers)

    cable.fiber_count = total_fibers
    cable.used_fibers = 0
    cable.save(
        update_fields=[
            "fiber_count",
            "used_fibers",
            "updated_at",
        ]
    )

    return {
        "cable": cable,
        "tube_count": len(created_tubes),
        "fiber_count": len(created_fibers),
    }


def _project_splices(project):
    """FiberSplice protege (`on_delete=PROTECT`) as fibras que funde, então
    precisa ser apagado antes do cabo — senão a exclusão do cabo trava
    tentando apagar os `FiberStrand` ainda referenciados pela fusão."""
    return FiberSplice.objects.filter(
        Q(input_fiber__cable__project=project) | Q(output_fiber__cable__project=project)
    )


def _project_cpd_olts(project):
    """`olt_integration.OLT.cpd` protege (`on_delete=PROTECT`) o POP — sem
    apagar essas OLTs antes, apagar o POP do projeto travaria do mesmo jeito
    que as fusões travavam a exclusão do cabo."""
    from apps.olt_integration.models import OLT

    return OLT.objects.filter(cpd__project=project)


def project_structure_counts(project):
    """Conta, por categoria, tudo que `wipe_project_structure` apagaria."""
    return {
        "kmz_batches": KMZImportBatch.objects.filter(project=project).count(),
        "splices": _project_splices(project).count(),
        "cables": FiberCable.objects.filter(project=project).count(),
        "elements": NetworkElement.objects.filter(project=project).count(),
        "routes": NetworkRoute.objects.filter(project=project).count(),
        "cpd_olts": _project_cpd_olts(project).count(),
        "pop": POP.objects.filter(project=project).count(),
    }


def wipe_project_structure(project):
    """Apaga toda a estrutura de rede de um projeto (postes, CTOs, cabos,
    tubos/fibras, splitters, fusões, reservas, lotes de importação KMZ,
    POP), preservando o projeto em si (nome, código, empresa)."""
    targets = [
        KMZImportBatch.objects.filter(project=project),
        _project_splices(project),
        FiberCable.objects.filter(project=project),
        NetworkElement.objects.filter(project=project),
        NetworkRoute.objects.filter(project=project),
        _project_cpd_olts(project),
        POP.objects.filter(project=project),
    ]
    with transaction.atomic():
        for queryset in targets:
            queryset.delete()
