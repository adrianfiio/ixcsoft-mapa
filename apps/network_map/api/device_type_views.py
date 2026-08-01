from __future__ import annotations

from django.db import transaction
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


ALLOWED_BY_CONTAINER = {
    NetworkElement.ElementType.RACK: {
        ContainerEquipment.EquipmentType.OLT,
        ContainerEquipment.EquipmentType.DIO,
        ContainerEquipment.EquipmentType.SWITCH,
        ContainerEquipment.EquipmentType.OTHER,
    },
    NetworkElement.ElementType.TOWER: {
        ContainerEquipment.EquipmentType.OLT,
        ContainerEquipment.EquipmentType.SWITCH,
        ContainerEquipment.EquipmentType.ACCESS_POINT,
        ContainerEquipment.EquipmentType.PTP,
        ContainerEquipment.EquipmentType.DIO,
        ContainerEquipment.EquipmentType.OTHER,
    },
}


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

    action = str(request.data.get("action") or "preview").strip().lower()
    selected_type = str(request.data.get("equipment_type") or "auto").strip()
    equipment_type = parsed.suggested_equipment_type if selected_type == "auto" else selected_type
    if equipment_type not in ALLOWED_BY_CONTAINER[container.element_type]:
        return JsonResponse(
            {"detail": "O tipo escolhido não é permitido neste rack/torre."}, status=400
        )

    preview = parsed.payload()
    preview["equipment_type"] = equipment_type
    preview["equipment_type_label"] = dict(ContainerEquipment.EquipmentType.choices).get(
        equipment_type, "ONU / Outro"
    )
    if action == "preview":
        return JsonResponse({"preview": preview})
    if action != "import":
        return JsonResponse({"detail": "Ação inválida."}, status=400)

    name = str(request.data.get("name") or parsed.model).strip()
    if not name:
        return JsonResponse({"detail": "Informe o nome do equipamento."}, status=400)
    management_ip = request.data.get("management_ip") or None
    subtype = str(request.data.get("equipment_subtype") or "").strip()
    if equipment_type == ContainerEquipment.EquipmentType.OTHER and not subtype:
        subtype = "onu" if any(
            item.port_type == ContainerEquipmentPort.PortType.PON
            for item in parsed.interfaces
        ) else "device"

    with transaction.atomic():
        equipment = ContainerEquipment.objects.create(
            company=container.company,
            container=container,
            name=name,
            equipment_type=equipment_type,
            management_ip=management_ip,
            provisioning_mode=ContainerEquipment.ProvisioningMode.MANUAL,
            vendor=parsed.manufacturer,
            model=parsed.model,
            metadata={
                "device_type": {
                    "manufacturer": parsed.manufacturer,
                    "model": parsed.model,
                    "slug": parsed.slug,
                    "source_format": "netbox-device-type-yaml",
                    "skipped_interfaces": [
                        {
                            "name": item.name,
                            "type": item.source_type,
                            "reason": item.warning,
                        }
                        for item in parsed.skipped_interfaces
                    ],
                },
                "equipment_subtype": subtype,
            },
        )
        ports = []
        for number, interface in enumerate(parsed.interfaces, 1):
            ports.append(
                ContainerEquipmentPort(
                    equipment=equipment,
                    port_type=interface.port_type,
                    number=number,
                    port_number=number,
                    label=interface.name,
                    enabled=interface.enabled,
                )
            )
        ContainerEquipmentPort.objects.bulk_create(ports)

    return JsonResponse(
        {
            "created": {
                "id": equipment.id,
                "name": equipment.name,
                "ports_created": len(ports),
                "equipment_type": equipment.equipment_type,
            },
            "preview": preview,
        },
        status=201,
    )
