from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv46_address
from django.db import DataError, IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company, scope_company_queryset
from apps.network_map.device_type_yaml import DeviceTypeYAMLError, parse_device_type_yaml
from apps.network_map.models import (
    ContainerEquipment,
    ContainerEquipmentPort,
    NetworkElement,
)


logger = logging.getLogger(__name__)
MAX_IMPORTED_INTERFACES = 256

RACK_ALLOWED_TYPES = {
    ContainerEquipment.EquipmentType.OLT,
    ContainerEquipment.EquipmentType.DIO,
    ContainerEquipment.EquipmentType.SWITCH,
    ContainerEquipment.EquipmentType.ROUTER,
    ContainerEquipment.EquipmentType.FIREWALL,
    ContainerEquipment.EquipmentType.SERVER,
    ContainerEquipment.EquipmentType.PTO,
    ContainerEquipment.EquipmentType.OTHER,
}

TOWER_ALLOWED_TYPES = {
    ContainerEquipment.EquipmentType.OLT,
    ContainerEquipment.EquipmentType.DIO,
    ContainerEquipment.EquipmentType.SWITCH,
    ContainerEquipment.EquipmentType.ROUTER,
    ContainerEquipment.EquipmentType.FIREWALL,
    ContainerEquipment.EquipmentType.ACCESS_POINT,
    ContainerEquipment.EquipmentType.PTP,
    ContainerEquipment.EquipmentType.ONU,
    ContainerEquipment.EquipmentType.PTO,
    ContainerEquipment.EquipmentType.OTHER,
}

ALLOWED_BY_CONTAINER = {
    NetworkElement.ElementType.RACK: RACK_ALLOWED_TYPES,
    NetworkElement.ElementType.TOWER: TOWER_ALLOWED_TYPES,
}


def _error_detail(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        if hasattr(exc, "message_dict"):
            return " ".join(
                f"{field}: {' '.join(str(item) for item in messages)}"
                for field, messages in exc.message_dict.items()
            )
        return " ".join(str(item) for item in exc.messages)
    return str(exc)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_container_device_type_yaml(request, element_id):
    container = get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type__in=[NetworkElement.ElementType.RACK, NetworkElement.ElementType.TOWER],
    )
    if not can_edit_company(request.user, container.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)

    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"detail": "Selecione um YAML de device type."}, status=400)
    try:
        parsed = parse_device_type_yaml(upload.read())
    except DeviceTypeYAMLError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    if len(parsed.interfaces) > MAX_IMPORTED_INTERFACES:
        return JsonResponse(
            {
                "detail": (
                    f"O YAML possui {len(parsed.interfaces)} interfaces físicas após expandir os intervalos. "
                    f"O limite por importação é {MAX_IMPORTED_INTERFACES}."
                )
            },
            status=400,
        )

    action = str(request.data.get("action") or "preview").strip().lower()
    selected_type = str(request.data.get("equipment_type") or "auto").strip()
    equipment_type = parsed.suggested_equipment_type if selected_type == "auto" else selected_type
    if equipment_type not in ALLOWED_BY_CONTAINER[container.element_type]:
        return JsonResponse(
            {"detail": "O tipo escolhido não é permitido nesta estrutura."}, status=400
        )

    preview = parsed.payload()
    preview["equipment_type"] = equipment_type
    preview["equipment_type_label"] = dict(ContainerEquipment.EquipmentType.choices).get(
        equipment_type, "ONU / Outro"
    )
    preview["expanded_interface_count"] = len(parsed.interfaces)
    if action == "preview":
        return JsonResponse({"preview": preview})
    if action != "import":
        return JsonResponse({"detail": "Ação inválida."}, status=400)

    name = str(request.data.get("name") or parsed.model).strip()
    if not name:
        return JsonResponse({"detail": "Informe o nome do equipamento."}, status=400)
    if ContainerEquipment.objects.filter(container=container, name=name).exists():
        return JsonResponse(
            {
                "detail": (
                    f"Já existe um equipamento chamado '{name}' nesta estrutura. "
                    "Informe um nome diferente antes de importar."
                )
            },
            status=409,
        )

    management_ip = str(request.data.get("management_ip") or "").strip() or None
    if management_ip:
        try:
            validate_ipv46_address(management_ip)
        except ValidationError:
            return JsonResponse({"detail": "O IP de gerência informado é inválido."}, status=400)

    subtype = str(request.data.get("equipment_subtype") or "").strip()
    if equipment_type == ContainerEquipment.EquipmentType.ONU:
        subtype = "onu"
    elif equipment_type == ContainerEquipment.EquipmentType.PTO:
        subtype = "pto"
    elif equipment_type == ContainerEquipment.EquipmentType.OLT:
        subtype = "olt-chassis"
    elif equipment_type == ContainerEquipment.EquipmentType.OTHER and not subtype:
        subtype = "onu" if any(
            item.port_type == ContainerEquipmentPort.PortType.PON
            for item in parsed.interfaces
        ) else "device"

    device_type_metadata = {
        **parsed.payload(),
        "source_format": "netbox-device-type-yaml",
    }

    try:
        with transaction.atomic():
            equipment = ContainerEquipment(
                company=container.company,
                container=container,
                name=name,
                description=parsed.comments,
                equipment_type=equipment_type,
                management_ip=management_ip,
                provisioning_mode=ContainerEquipment.ProvisioningMode.MANUAL,
                vendor=parsed.manufacturer,
                model=parsed.model,
                metadata={
                    "device_type": device_type_metadata,
                    "equipment_subtype": subtype,
                    "canvas_renderer": "modular-chassis-v07510" if equipment_type == ContainerEquipment.EquipmentType.OLT else "default",
                },
            )
            equipment.full_clean()
            equipment.save()

            ports = []
            for number, interface in enumerate(parsed.interfaces, 1):
                ports.append(
                    ContainerEquipmentPort(
                        equipment=equipment,
                        port_type=str(interface.port_type),
                        number=number,
                        port_number=number,
                        label=interface.name,
                        enabled=interface.enabled,
                    )
                )
            ContainerEquipmentPort.objects.bulk_create(ports)
    except IntegrityError:
        logger.exception("Conflito ao importar Device Type YAML no container %s", container.id)
        return JsonResponse(
            {
                "detail": (
                    "Não foi possível importar porque nome, porta ou outro dado já existe "
                    "nesta estrutura. Revise o nome do equipamento e tente novamente."
                )
            },
            status=409,
        )
    except (ValidationError, DataError, ValueError) as exc:
        logger.warning("YAML rejeitado no container %s: %s", container.id, exc)
        return JsonResponse({"detail": _error_detail(exc)}, status=400)
    except Exception:
        logger.exception("Erro inesperado ao importar Device Type YAML no container %s", container.id)
        return JsonResponse(
            {
                "detail": (
                    "Falha interna ao importar o YAML. O erro foi registrado nos logs "
                    "do servidor para diagnóstico."
                )
            },
            status=500,
        )

    return JsonResponse(
        {
            "created": {
                "id": equipment.id,
                "name": equipment.name,
                "ports_created": len(ports),
                "equipment_type": equipment.equipment_type,
                "renderer": equipment.metadata.get("canvas_renderer"),
            },
            "preview": preview,
        },
        status=201,
    )
