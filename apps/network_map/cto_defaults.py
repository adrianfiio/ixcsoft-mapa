from __future__ import annotations

from apps.network_map.models import (
    CTO,
    CTOSplitter,
    SpliceTray,
    SpliceTraySplitter,
    SpliceTraySplitterPort,
)
from apps.network_map.serializers import sync_splitter_ports


_SPLITTER_SIZES = (64, 32, 16, 8, 4, 2)


def splitter_sizes_for_capacity(capacity: int) -> list[int]:
    """Decompõe a capacidade da CTO em splitters balanceados suportados.

    Exemplos: 8 -> [8], 16 -> [16], 24 -> [16, 8], 36 -> [32, 4].
    Capacidades ímpares recebem uma última saída 1:2, pois o modelo atual não
    possui splitter 1:1. A capacidade nominal da CTO permanece inalterada.
    """
    remaining = max(1, min(int(capacity or 1), 128))
    plan: list[int] = []
    while remaining >= 2 and len(plan) < 8:
        selected = next((size for size in _SPLITTER_SIZES if size <= remaining), 2)
        plan.append(selected)
        remaining -= selected
    if remaining == 1 and len(plan) < 8:
        plan.append(2)
    return plan or [2]


def ensure_cto_default_splitters(cto: CTO, capacity: int | None = None) -> list[int]:
    """Cria a estrutura padrão de splitter e suas portas para uma CTO.

    Mantém os dois modelos usados hoje pelo MAPA:
    - CTOSplitter/CTOSplitterPort para cadastro e ocupação comercial;
    - SpliceTraySplitter/Port para o diagrama de fusões.
    """
    capacity = max(1, min(int(capacity or cto.capacity or 8), 128))
    plan = splitter_sizes_for_capacity(capacity)

    cto.capacity = capacity
    cto.splitter_ratio = f"1:{plan[0]}" if len(plan) == 1 else ""
    cto.save(update_fields=["capacity", "splitter_ratio", "updated_at"])

    for position, output_ports in enumerate(plan, 1):
        ratio = f"1:{output_ports}"
        splitter, _created = CTOSplitter.objects.update_or_create(
            cto=cto,
            position=position,
            defaults={
                "name": f"Splitter {position}",
                "ratio": ratio,
                "output_ports": output_ports,
                "enabled": True,
            },
        )
        sync_splitter_ports(splitter, output_ports)
    cto.splitters.filter(position__gt=len(plan)).delete()

    tray, _created = SpliceTray.objects.get_or_create(
        splice_box=cto,
        number=1,
        defaults={"name": "Bandeja 1", "capacity": max(12, sum(plan))},
    )
    desired_capacity = max(12, sum(plan))
    if tray.capacity != desired_capacity:
        tray.capacity = desired_capacity
        tray.save(update_fields=["capacity", "updated_at"])

    for position, output_ports in enumerate(plan, 1):
        ratio = f"1:{output_ports}"
        graphic_splitter, _created = SpliceTraySplitter.objects.update_or_create(
            tray=tray,
            position=position,
            defaults={"ratio": ratio, "output_ports": output_ports},
        )
        existing = set(graphic_splitter.ports.values_list("number", flat=True))
        SpliceTraySplitterPort.objects.bulk_create(
            [
                SpliceTraySplitterPort(splitter=graphic_splitter, number=number)
                for number in range(1, output_ports + 1)
                if number not in existing
            ]
        )
        graphic_splitter.ports.filter(number__gt=output_ports).delete()
    tray.splitters.filter(position__gt=len(plan)).delete()

    return plan
