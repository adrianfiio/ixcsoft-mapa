from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.network_map.models import (
    ContainerEquipment,
    ContainerPortLink,
    CTOSplitter,
    CTOSplitterPort,
    FiberCable,
    FiberSplice,
    NetworkElement,
    SpliceTray,
    SpliceTraySplitter,
    SpliceTraySplitterPort,
)

OPTICAL_BOX_TYPES = [NetworkElement.ElementType.CTO, NetworkElement.ElementType.SPLICE_BOX]

# MAP_V07533_OPTICAL_CLEANUP: chave de metadata usada pelo Canvas 2D do
# Rack/Torre (container_layout_v3, apps/network_map/api/optical_editor_v3.py)
# quando a integração experimental fazia CTO/CEO/CDO abrirem por esse motor.
# Esse endpoint agora rejeita CTO/SPLICE_BOX (revertido na v0.75.33) -- essa
# chave, se ainda existir em alguma caixa óptica, é lixo órfão e inofensivo
# de remover: não é usada por nenhum código daqui pra frente.
EXPERIMENTAL_LAYOUT_METADATA_KEY = "container_layout_v3"


class Command(BaseCommand):
    help = (
        "Relata e, opcionalmente, limpa resíduos deixados pela integração "
        "experimental CTO/CEO/CDO-no-motor-do-Rack/Torre (removida na "
        "v0.75.33). NÃO apaga splitters, bandejas de emenda ou fusões "
        "reais das caixas ópticas -- não há como distinguir com segurança "
        "dados de teste de dados de produção nesses modelos (podem estar "
        "atendendo clientes reais). Só remove o que é estruturalmente "
        "impossível de ser dado legítimo: registros de 'equipamento "
        "genérico' (modelo do Rack/Torre) presos numa CTO/CEO/CDO, e a "
        "chave de layout do Canvas do Rack/Torre órfã na metadata dessas "
        "caixas. Sempre rode sem --confirm primeiro para ver o relatório."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Só mostra o relatório, não altera nada (padrão).")
        parser.add_argument("--confirm", action="store_true", help="Executa a limpeza dentro de uma transação.")

    def handle(self, *args, **options):
        dry_run = options["dry_run"] or not options["confirm"]

        optical_boxes = NetworkElement.objects.filter(element_type__in=OPTICAL_BOX_TYPES)
        cto_count = optical_boxes.filter(element_type=NetworkElement.ElementType.CTO).count()
        splice_box_qs = optical_boxes.filter(element_type=NetworkElement.ElementType.SPLICE_BOX)
        ceo_count = splice_box_qs.filter(metadata__import_subtype="ceo").count()
        cdo_count = splice_box_qs.filter(metadata__import_subtype="cdo").count()
        splice_box_other_count = splice_box_qs.count() - ceo_count - cdo_count

        self.stdout.write(self.style.MIGRATE_HEADING("Caixas ópticas encontradas"))
        self.stdout.write(f"- CTO: {cto_count}")
        self.stdout.write(f"- CEO: {ceo_count}")
        self.stdout.write(f"- CDO: {cdo_count}")
        if splice_box_other_count:
            self.stdout.write(f"- splice_box sem subtipo definido: {splice_box_other_count}")

        # --- Dados ópticos LEGÍTIMOS: nunca apagados por este comando -----
        splitters = CTOSplitter.objects.filter(cto__element_type=NetworkElement.ElementType.CTO)
        splitter_ports = CTOSplitterPort.objects.filter(splitter__in=splitters)
        occupied_ports = splitter_ports.filter(access_point__isnull=False)
        trays = SpliceTray.objects.filter(splice_box__element_type__in=OPTICAL_BOX_TYPES)
        tray_splitters = SpliceTraySplitter.objects.filter(tray__in=trays)
        tray_splitter_ports = SpliceTraySplitterPort.objects.filter(splitter__in=tray_splitters)
        splices = FiberSplice.objects.filter(splice_box__element_type__in=OPTICAL_BOX_TYPES)

        self.stdout.write(self.style.MIGRATE_HEADING(
            "Dados ópticos reais (splitters, bandejas, fusões) -- NUNCA apagados"
        ))
        self.stdout.write(f"- Splitters de CTO: {splitters.count()}")
        self.stdout.write(f"- Portas de splitter de CTO: {splitter_ports.count()} "
                           f"({occupied_ports.count()} ocupadas por access_point real de cliente)")
        self.stdout.write(f"- Bandejas de emenda (CEO/CDO/CTO): {trays.count()}")
        self.stdout.write(f"- Splitters em bandeja de emenda: {tray_splitters.count()}")
        self.stdout.write(f"- Portas de splitter em bandeja de emenda: {tray_splitter_ports.count()}")
        self.stdout.write(f"- Fusões (FiberSplice): {splices.count()}")
        self.stdout.write(
            "  Motivo: os models não guardam nenhuma marca de \"criado durante o "
            "teste da integração quebrada\" -- uma CTO real de cliente e uma CTO "
            "de teste têm exatamente a mesma forma nos dados. Apagar aqui "
            "arriscaria derrubar atendimentos reais. Nenhum splitter/bandeja/"
            "fusão é removido por este comando, com ou sem --confirm."
        )

        # --- Cabos ligados às caixas: relatados, nunca apagados ------------
        connected_cables = _connected_cables(optical_boxes)
        self.stdout.write(self.style.MIGRATE_HEADING("Cabos conectados às caixas ópticas (apenas relatório)"))
        self.stdout.write(f"- Cabos com origem/destino numa CTO/CEO/CDO: {connected_cables.count()}")

        # --- Resíduos estruturais da integração experimental ---------------
        # ContainerEquipment.container é, por convenção do model, sempre
        # rack/tower (limit_choices_to). Qualquer linha presa numa
        # CTO/SPLICE_BOX só existe porque a integração quebrada deixou essas
        # caixas passarem pelos endpoints de equipamento do Rack/Torre --
        # nunca é dado legítimo, e o endpoint que criava isso já foi
        # revertido para rejeitar CTO/SPLICE_BOX.
        stray_equipment = ContainerEquipment.objects.filter(container__element_type__in=OPTICAL_BOX_TYPES)
        stray_port_links = ContainerPortLink.objects.filter(container__element_type__in=OPTICAL_BOX_TYPES)
        boxes_with_stale_layout = optical_boxes.filter(metadata__has_key=EXPERIMENTAL_LAYOUT_METADATA_KEY)

        self.stdout.write(self.style.MIGRATE_HEADING(
            "Resíduos da integração experimental (isto sim é removido com --confirm)"
        ))
        self.stdout.write(f"- Equipamento genérico preso numa caixa óptica: {stray_equipment.count()}")
        self.stdout.write(f"- Ligação de porta presa numa caixa óptica: {stray_port_links.count()}")
        self.stdout.write(
            f"- Caixas ópticas com metadata.{EXPERIMENTAL_LAYOUT_METADATA_KEY} órfã: "
            f"{boxes_with_stale_layout.count()}"
        )

        if not stray_equipment.exists() and not boxes_with_stale_layout.exists():
            self.stdout.write(self.style.SUCCESS("Nada para limpar -- nenhum resíduo estrutural encontrado."))

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "Simulação (--dry-run): nenhum registro foi alterado ou removido."
            ))
            return

        with transaction.atomic():
            equipment_count = stray_equipment.count()
            # CASCADE cuida de ContainerEquipmentCard, ContainerEquipmentPort
            # e ContainerPortLink dependurados nesse equipamento.
            stray_equipment.delete()
            cleaned_layout = 0
            for box in boxes_with_stale_layout:
                metadata = dict(box.metadata or {})
                if EXPERIMENTAL_LAYOUT_METADATA_KEY in metadata:
                    del metadata[EXPERIMENTAL_LAYOUT_METADATA_KEY]
                    box.metadata = metadata
                    box.save(update_fields=["metadata", "updated_at"])
                    cleaned_layout += 1

        self.stdout.write(self.style.SUCCESS(
            f"Limpeza concluída: {equipment_count} equipamento(s) genérico(s) removido(s) "
            f"de caixas ópticas, {cleaned_layout} metadata.{EXPERIMENTAL_LAYOUT_METADATA_KEY} órfã(s) limpa(s)."
        ))


def _connected_cables(optical_boxes):
    ids = list(optical_boxes.values_list("id", flat=True))
    return FiberCable.objects.filter(Q(origin_id__in=ids) | Q(destination_id__in=ids))
