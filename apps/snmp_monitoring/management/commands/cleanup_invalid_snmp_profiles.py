from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.core.enums import OperationalStatus
from apps.network_map.models import ContainerEquipment
from apps.snmp_monitoring import services
from apps.snmp_monitoring.docker_control import reload_telegraf
from apps.snmp_monitoring.models import MonitoredNetworkLink, SNMPMonitoringProfile


ELIGIBLE_TYPES = {
    ContainerEquipment.EquipmentType.SWITCH,
    ContainerEquipment.EquipmentType.ROUTER,
    ContainerEquipment.EquipmentType.FIREWALL,
    ContainerEquipment.EquipmentType.ACCESS_POINT,
    ContainerEquipment.EquipmentType.PTP,
    ContainerEquipment.EquipmentType.ONU,
    ContainerEquipment.EquipmentType.OTHER,
}


class Command(BaseCommand):
    help = (
        "Audita e corrige perfis SNMP universais inválidos. DIO, PTO, servidor, "
        "OLT universal e perfis ligados diretamente a elementos do mapa deixam de ser coletados."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica as correções. Sem esta opção, executa somente a auditoria.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        profiles = list(
            SNMPMonitoringProfile.objects.select_related("equipment", "element").all()
        )
        invalid = []
        promote_to_snmp = []

        for profile in profiles:
            equipment = profile.equipment
            if equipment is None:
                invalid.append((profile, "perfil ligado diretamente a elemento do mapa"))
                continue
            if equipment.equipment_type not in ELIGIBLE_TYPES:
                invalid.append((profile, f"tipo não monitorável: {equipment.equipment_type}"))
                continue
            if not equipment.enabled:
                invalid.append((profile, "equipamento desativado"))
                continue
            if equipment.provisioning_mode != ContainerEquipment.ProvisioningMode.SNMP:
                promote_to_snmp.append(equipment)

        servers = ContainerEquipment.objects.filter(
            equipment_type=ContainerEquipment.EquipmentType.SERVER,
            enabled=True,
        )

        self.stdout.write(f"Perfis analisados: {len(profiles)}")
        self.stdout.write(f"Perfis inválidos: {len(invalid)}")
        self.stdout.write(f"Equipamentos válidos a marcar como SNMP: {len(promote_to_snmp)}")
        server_count = servers.count()
        self.stdout.write(f"Servidores ativos a ocultar do mapa: {server_count}")
        for profile, reason in invalid[:30]:
            self.stdout.write(f"- perfil {profile.pk}: {reason}")

        if not apply_changes:
            self.stdout.write(self.style.WARNING("Auditoria concluída. Use --apply para corrigir."))
            return

        invalid_profile_ids = {profile.pk for profile, _reason in invalid}
        with transaction.atomic():
            for profile, _reason in invalid:
                services.remove_conf_by_influx_id(profile.influx_id)
                profile.enabled = False
                profile.last_status = OperationalStatus.NO_DATA
                profile.last_poll_message = "Monitoramento desativado pela regra de elegibilidade v0.74."
                profile.save(update_fields=[
                    "enabled", "last_status", "last_poll_message", "updated_at",
                ])

            for equipment in promote_to_snmp:
                equipment.provisioning_mode = ContainerEquipment.ProvisioningMode.SNMP
                equipment.save(update_fields=["provisioning_mode", "updated_at"])

            servers.update(enabled=False)

            links = MonitoredNetworkLink.objects.filter(enabled=True).filter(
                Q(source_binding__profile_id__in=invalid_profile_ids)
                | Q(destination_binding__profile_id__in=invalid_profile_ids)
            )
            link_count = links.update(
                enabled=False,
                status=OperationalStatus.NO_DATA,
                candidate_status="",
                candidate_since=None,
                last_message="Enlace desativado: uma das pontas não é elegível para SNMP universal.",
            )

        reload_telegraf()
        self.stdout.write(self.style.SUCCESS(
            f"Correção aplicada: {len(invalid)} perfil(is), {link_count} enlace(s) e "
            f"{server_count} servidor(es) tratados."
        ))
