from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.access import can_edit_company, scope_company_queryset
from apps.core.enums import OperationalStatus, Severity
from apps.network_map.models import (
    ContainerEquipment,
    ContainerEquipmentPort,
    FiberCable,
    NetworkElement,
    NetworkProject,
)
from .models import (
    MonitoredNetworkLink,
    SNMPInterfaceState,
    SNMPMonitoringProfile,
    SNMPPortBinding,
)
from .tasks import poll_snmp_status


STATUS_LABELS = dict(OperationalStatus.choices)

UNIVERSAL_SNMP_EQUIPMENT_TYPES = {
    ContainerEquipment.EquipmentType.SWITCH,
    ContainerEquipment.EquipmentType.ROUTER,
    ContainerEquipment.EquipmentType.FIREWALL,
    ContainerEquipment.EquipmentType.ACCESS_POINT,
    ContainerEquipment.EquipmentType.PTP,
    ContainerEquipment.EquipmentType.ONU,
    ContainerEquipment.EquipmentType.OTHER,
}


def _is_universal_snmp_equipment(equipment: ContainerEquipment) -> bool:
    return bool(equipment.enabled and equipment.equipment_type in UNIVERSAL_SNMP_EQUIPMENT_TYPES)


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on", "sim"}


def _validation_detail(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return " ".join(
            f"{field}: {' '.join(str(item) for item in messages)}"
            for field, messages in exc.message_dict.items()
        )
    return " ".join(str(item) for item in getattr(exc, "messages", [str(exc)]))


def _project_for_user(request, project_id):
    return get_object_or_404(
        scope_company_queryset(NetworkProject.objects.all(), request.user),
        pk=project_id,
    )


def _equipment_for_user(request, equipment_id):
    return get_object_or_404(
        scope_company_queryset(
            ContainerEquipment.objects.select_related("container", "company").prefetch_related("ports"),
            request.user,
        ),
        pk=equipment_id,
    )


def _profile_payload(profile: SNMPMonitoringProfile | None):
    if not profile:
        return None
    return {
        "id": profile.id,
        "enabled": profile.enabled,
        "management_ip": profile.management_ip,
        "port": profile.port,
        "snmp_version": profile.snmp_version,
        "polling_interval_seconds": profile.polling_interval_seconds,
        "aggregate_policy": profile.aggregate_policy,
        "influx_id": profile.influx_id,
        "community_set": bool(profile.community_encrypted),
        "last_status": profile.last_status,
        "last_status_label": STATUS_LABELS.get(profile.last_status, profile.last_status),
        "last_poll_at": profile.last_poll_at.isoformat() if profile.last_poll_at else None,
        "last_success_at": profile.last_success_at.isoformat() if profile.last_success_at else None,
        "last_poll_message": profile.last_poll_message,
    }


def _interface_payload(state: SNMPInterfaceState):
    return {
        "id": state.id,
        "if_name": state.if_name,
        "if_index": state.if_index,
        "if_alias": state.if_alias,
        "status": state.status,
        "status_label": state.get_status_display(),
        "raw_status": state.raw_status,
        "last_seen_at": state.last_seen_at.isoformat() if state.last_seen_at else None,
        "status_changed_at": state.status_changed_at.isoformat() if state.status_changed_at else None,
    }


def _binding_payload(binding: SNMPPortBinding):
    profile = binding.profile
    target_element = profile.target_element
    return {
        "id": binding.id,
        "profile_id": profile.id,
        "equipment_id": profile.equipment_id,
        "equipment": profile.target_name,
        "element_id": getattr(target_element, "id", None),
        "element": getattr(target_element, "name", ""),
        "equipment_port_id": binding.equipment_port_id,
        "equipment_port": binding.equipment_port.label if binding.equipment_port_id else "",
        "label": binding.label,
        "if_name": binding.if_name,
        "if_index": binding.if_index,
        "role": binding.role,
        "role_label": binding.get_role_display(),
        "enabled": binding.enabled,
        "expected_up": binding.expected_up,
        "alert_enabled": binding.alert_enabled,
        "severity": binding.severity,
        "outage_persistence_seconds": binding.outage_persistence_seconds,
        "recovery_seconds": binding.recovery_seconds,
        "last_status": binding.last_status,
        "last_seen_at": binding.last_seen_at.isoformat() if binding.last_seen_at else None,
        "status_changed_at": binding.status_changed_at.isoformat() if binding.status_changed_at else None,
        "display_name": binding.display_name,
    }


def _link_geometry(link: MonitoredNetworkLink):
    if link.cable_id and link.cable.geometry:
        return {
            "type": "MultiLineString",
            "coordinates": link.cable.geometry.coords,
        }
    if link.source_element.point and link.destination_element.point:
        return {
            "type": "MultiLineString",
            "coordinates": [[
                [link.source_element.point.x, link.source_element.point.y],
                [link.destination_element.point.x, link.destination_element.point.y],
            ]],
        }
    return None


def _link_payload(link: MonitoredNetworkLink, *, feature=False):
    source_binding = _binding_payload(link.source_binding) if link.source_binding_id else None
    destination_binding = _binding_payload(link.destination_binding) if link.destination_binding_id else None
    properties = {
        "id": link.id,
        "name": link.name,
        "code": link.code,
        "link_type": link.link_type,
        "link_type_label": link.get_link_type_display(),
        "project_id": link.project_id,
        "source_element_id": link.source_element_id,
        "source_element": link.source_element.name,
        "destination_element_id": link.destination_element_id,
        "destination_element": link.destination_element.name,
        "source_binding": source_binding,
        "destination_binding": destination_binding,
        "cable_id": link.cable_id,
        "cable": link.cable.name if link.cable_id else "",
        "enabled": link.enabled,
        "require_both_endpoints": link.require_both_endpoints,
        "alert_enabled": link.alert_enabled,
        "severity": link.severity,
        "normal_color": link.normal_color,
        "down_color": link.down_color,
        "display_color": link.display_color,
        "dash_array": link.dash_array or ("12 10" if link.link_type == MonitoredNetworkLink.LinkType.WIRELESS else ""),
        "weight": link.weight,
        "status": link.status,
        "status_label": link.get_status_display(),
        "status_changed_at": link.status_changed_at.isoformat() if link.status_changed_at else None,
        "last_evaluated_at": link.last_evaluated_at.isoformat() if link.last_evaluated_at else None,
        "last_message": link.last_message,
        "outage_persistence_seconds": link.outage_persistence_seconds,
        "recovery_seconds": link.recovery_seconds,
    }
    if feature:
        return {
            "type": "Feature",
            "id": link.id,
            "geometry": _link_geometry(link),
            "properties": properties,
        }
    return properties


def _profile_for_equipment(equipment):
    try:
        return equipment.snmp_monitoring
    except SNMPMonitoringProfile.DoesNotExist:
        return None


@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def equipment_monitoring_profile(request, equipment_id):
    equipment = _equipment_for_user(request, equipment_id)
    profile = _profile_for_equipment(equipment)
    if not _is_universal_snmp_equipment(equipment):
        return JsonResponse(
            {
                "detail": (
                    "Este tipo não participa do monitoramento SNMP universal. "
                    "DIO, PTO, servidor, OLT, Rack/Torre e elementos ópticos são somente inventário/topologia."
                )
            },
            status=409,
        )
    if request.method == "GET":
        states = profile.interface_states.all() if profile else []
        bindings = profile.port_bindings.select_related("equipment_port", "profile__equipment", "profile__equipment__container") if profile else []
        return JsonResponse({
            "equipment": {
                "id": equipment.id,
                "name": equipment.name,
                "type": equipment.equipment_type,
                "type_label": equipment.get_equipment_type_display(),
                "management_ip": equipment.management_ip,
                "container_id": equipment.container_id,
                "container": equipment.container.name,
                "project_id": equipment.container.project_id,
            },
            "profile": _profile_payload(profile),
            "ports": [{
                "id": port.id,
                "label": port.label,
                "type": port.port_type,
                "type_label": port.get_port_type_display(),
                "binding_id": getattr(getattr(port, "snmp_binding", None), "id", None),
            } for port in equipment.ports.all()],
            "interfaces": [_interface_payload(item) for item in states],
            "bindings": [_binding_payload(item) for item in bindings],
        })

    if not can_edit_company(request.user, equipment.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    if request.method == "DELETE":
        if profile:
            profile.delete()
        if equipment.provisioning_mode != ContainerEquipment.ProvisioningMode.MANUAL:
            equipment.provisioning_mode = ContainerEquipment.ProvisioningMode.MANUAL
            equipment.save(update_fields=["provisioning_mode", "updated_at"])
        return JsonResponse({"success": True})

    data = request.data
    community = str(data.get("community") or "").strip()
    if profile is None and not community:
        return JsonResponse({"detail": "Informe a community SNMP na criação."}, status=400)
    management_ip = str(data.get("management_ip") or equipment.management_ip or "").strip()
    if not management_ip:
        return JsonResponse({"detail": "Informe o IP de gerência."}, status=400)
    try:
        snmp_port = int(data.get("port") or 161)
        interval = int(data.get("polling_interval_seconds") or 30)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Porta e intervalo devem ser números."}, status=400)

    try:
        with transaction.atomic():
            if profile is None:
                profile = SNMPMonitoringProfile(
                    company=equipment.company,
                    equipment=equipment,
                    management_ip=management_ip,
                )
            profile.management_ip = management_ip
            profile.port = snmp_port
            profile.polling_interval_seconds = interval
            profile.enabled = _as_bool(data.get("enabled"), True)
            profile.aggregate_policy = SNMPMonitoringProfile.AggregatePolicy.BOUND_PORTS
            if community:
                profile.set_community(community)
            profile.save()
            equipment_fields = []
            if equipment.management_ip != management_ip:
                equipment.management_ip = management_ip
                equipment_fields.append("management_ip")
            if equipment.provisioning_mode != ContainerEquipment.ProvisioningMode.SNMP:
                equipment.provisioning_mode = ContainerEquipment.ProvisioningMode.SNMP
                equipment_fields.append("provisioning_mode")
            if equipment_fields:
                equipment.save(update_fields=[*equipment_fields, "updated_at"])
    except ValidationError as exc:
        return JsonResponse({"detail": _validation_detail(exc)}, status=400)
    return JsonResponse({"profile": _profile_payload(profile)})


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def equipment_monitoring_bindings(request, equipment_id):
    equipment = _equipment_for_user(request, equipment_id)
    if not can_edit_company(request.user, equipment.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    profile = _profile_for_equipment(equipment)
    if not profile:
        return JsonResponse({"detail": "Salve o perfil SNMP antes de mapear as portas."}, status=409)
    rows = request.data.get("bindings")
    if not isinstance(rows, list):
        return JsonResponse({"detail": "bindings deve ser uma lista."}, status=400)
    existing = {item.id: item for item in profile.port_bindings.select_related("equipment_port")}
    keep = set()
    allowed_roles = dict(SNMPPortBinding.Role.choices)
    try:
        with transaction.atomic():
            for row in rows:
                if not isinstance(row, dict):
                    continue
                binding_id = row.get("id")
                binding = existing.get(int(binding_id)) if str(binding_id or "").isdigit() else None
                if binding is None:
                    binding = SNMPPortBinding(profile=profile, company=equipment.company)
                if_name = str(row.get("if_name") or "").strip()
                if not if_name:
                    return JsonResponse({"detail": "Toda porta vinculada precisa do nome SNMP/ifName."}, status=400)
                port_id = row.get("equipment_port_id") or None
                port = None
                if port_id:
                    port = get_object_or_404(ContainerEquipmentPort, pk=port_id, equipment=equipment)
                role = str(row.get("role") or SNMPPortBinding.Role.OTHER)
                if role not in allowed_roles:
                    role = SNMPPortBinding.Role.OTHER
                binding.equipment_port = port
                binding.label = str(row.get("label") or (port.label if port else if_name)).strip()
                binding.if_name = if_name
                try:
                    binding.if_index = int(row["if_index"]) if row.get("if_index") not in (None, "") else None
                    binding.outage_persistence_seconds = max(0, int(row.get("outage_persistence_seconds") or 30))
                    binding.recovery_seconds = max(0, int(row.get("recovery_seconds") or 30))
                except (TypeError, ValueError):
                    return JsonResponse({"detail": f"ifIndex ou tempos inválidos para {if_name}."}, status=400)
                binding.role = role
                binding.enabled = _as_bool(row.get("enabled"), True)
                binding.expected_up = _as_bool(row.get("expected_up"), True)
                binding.alert_enabled = _as_bool(row.get("alert_enabled"), True)
                binding.severity = str(row.get("severity") or Severity.HIGH)
                if binding.severity not in dict(Severity.choices):
                    return JsonResponse({"detail": f"Severidade inválida para {if_name}."}, status=400)
                binding.save()
                keep.add(binding.id)
            for binding in profile.port_bindings.exclude(pk__in=keep):
                if binding.source_links.filter(enabled=True).exists() or binding.destination_links.filter(enabled=True).exists():
                    binding.enabled = False
                    binding.save(update_fields=["enabled", "updated_at"])
                else:
                    binding.delete()
    except ValidationError as exc:
        return JsonResponse({"detail": _validation_detail(exc)}, status=400)
    result = profile.port_bindings.select_related(
        "equipment_port", "profile__equipment", "profile__equipment__container"
    )
    return JsonResponse({"bindings": [_binding_payload(item) for item in result]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def equipment_monitoring_poll_now(request, equipment_id):
    equipment = _equipment_for_user(request, equipment_id)
    if not can_edit_company(request.user, equipment.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    profile = _profile_for_equipment(equipment)
    if not profile:
        return JsonResponse({"detail": "Equipamento sem perfil SNMP."}, status=404)
    task = poll_snmp_status.delay([profile.id])
    return JsonResponse({"queued": True, "task_id": task.id}, status=202)


def _project_links_queryset(request, project):
    return scope_company_queryset(
        MonitoredNetworkLink.objects.filter(project=project, enabled=True).select_related(
            "project", "company", "cable__route", "source_element", "destination_element",
            "source_binding__profile__equipment__container", "source_binding__equipment_port",
            "destination_binding__profile__equipment__container", "destination_binding__equipment_port",
        ),
        request.user,
    )


def _project_options(request, project):
    profiles = SNMPMonitoringProfile.objects.filter(
        company=project.company,
        enabled=True,
        equipment__enabled=True,
        equipment__provisioning_mode=ContainerEquipment.ProvisioningMode.SNMP,
        equipment__equipment_type__in=UNIVERSAL_SNMP_EQUIPMENT_TYPES,
        equipment__container__project=project,
    ).select_related("equipment__container", "element").prefetch_related("port_bindings__equipment_port")
    bindings = []
    equipment_statuses = []
    port_statuses = []
    for profile in profiles:
        equipment_statuses.append({
            "equipment_id": profile.equipment_id,
            "element_id": getattr(profile.target_element, "id", None),
            "status": profile.last_status,
            "message": profile.last_poll_message,
        })
        for binding in profile.port_bindings.filter(enabled=True):
            bindings.append(_binding_payload(binding))
            if binding.equipment_port_id:
                port_statuses.append({
                    "port_id": binding.equipment_port_id,
                    "binding_id": binding.id,
                    "status": binding.last_status,
                    "last_seen_at": binding.last_seen_at.isoformat() if binding.last_seen_at else None,
                })
    cables = (
        FiberCable.objects.filter(project=project, company=project.company).order_by("name")
        if profiles else FiberCable.objects.none()
    )
    elements = (
        NetworkElement.objects.filter(project=project, company=project.company).order_by("name")
        if profiles else NetworkElement.objects.none()
    )
    return {
        "monitoring_enabled": bool(profiles),
        "refresh_interval_seconds": 30,
        "bindings": bindings,
        "equipment_statuses": equipment_statuses,
        "port_statuses": port_statuses,
        "cables": [{
            "id": cable.id,
            "name": cable.name,
            "code": cable.code,
            "type": cable.cable_type,
            "origin_id": cable.origin_id,
            "destination_id": cable.destination_id,
            "status": cable.status,
            "monitored_link_id": getattr(getattr(cable, "monitored_link", None), "id", None),
        } for cable in cables],
        "elements": [{
            "id": element.id,
            "name": element.name,
            "type": element.element_type,
        } for element in elements],
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def project_monitoring_snapshot(request, project_id):
    project = _project_for_user(request, project_id)
    links = list(_project_links_queryset(request, project))
    features = [_link_payload(link, feature=True) for link in links]
    priority = {
        OperationalStatus.OFFLINE: 5,
        OperationalStatus.DEGRADED: 4,
        OperationalStatus.WARNING: 3,
        OperationalStatus.NO_DATA: 2,
        OperationalStatus.RECOVERING: 1,
        OperationalStatus.NORMAL: 0,
    }
    element_status_map: dict[int, dict[str, Any]] = {}
    for link in links:
        for element in (link.source_element, link.destination_element):
            current = element_status_map.get(element.id)
            if not current or priority.get(link.status, 0) > priority.get(current["status"], 0):
                element_status_map[element.id] = {
                    "element_id": element.id,
                    "status": link.status,
                    "message": link.last_message,
                    "link_id": link.id,
                }
    options = _project_options(request, project)
    for row in options["equipment_statuses"]:
        element_id = row.get("element_id")
        if not element_id:
            continue
        current = element_status_map.get(element_id)
        if not current or priority.get(row["status"], 0) > priority.get(current["status"], 0):
            element_status_map[element_id] = {
                "element_id": element_id,
                "status": row["status"],
                "message": row["message"],
                "link_id": None,
            }
    return JsonResponse({
        "project": {"id": project.id, "name": project.name},
        "links": {"type": "FeatureCollection", "features": features},
        "element_statuses": list(element_status_map.values()),
        **options,
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def monitored_links(request):
    if request.method == "GET":
        project_id = request.GET.get("project_id")
        if not project_id:
            return JsonResponse({"detail": "Informe project_id."}, status=400)
        project = _project_for_user(request, project_id)
        return JsonResponse({"links": [_link_payload(item) for item in _project_links_queryset(request, project)]})

    data = request.data
    project = _project_for_user(request, data.get("project_id"))
    if not can_edit_company(request.user, project.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    source_binding = get_object_or_404(
        SNMPPortBinding.objects.select_related("profile__equipment__container", "profile__element"),
        pk=data.get("source_binding_id"),
        company=project.company,
        enabled=True,
    )
    destination_binding = get_object_or_404(
        SNMPPortBinding.objects.select_related("profile__equipment__container", "profile__element"),
        pk=data.get("destination_binding_id"),
        company=project.company,
        enabled=True,
    )
    if source_binding.id == destination_binding.id:
        return JsonResponse({"detail": "Escolha portas diferentes nas duas pontas."}, status=400)
    source_element = source_binding.target_element
    destination_element = destination_binding.target_element
    if not source_element or not destination_element:
        return JsonResponse({"detail": "As duas portas precisam estar ligadas a estruturas do mapa."}, status=400)
    if source_element.project_id != project.id or destination_element.project_id != project.id:
        return JsonResponse({"detail": "As duas pontas precisam pertencer ao projeto selecionado."}, status=400)
    if source_element.id == destination_element.id:
        return JsonResponse({"detail": "Escolha estruturas diferentes nas duas pontas."}, status=400)
    link_type = str(data.get("link_type") or "backbone")
    if link_type not in dict(MonitoredNetworkLink.LinkType.choices):
        return JsonResponse({"detail": "Tipo de enlace inválido."}, status=400)
    cable = None
    cable_id = data.get("cable_id")
    if cable_id:
        cable = get_object_or_404(FiberCable, pk=cable_id, project=project, company=project.company)
        endpoints = {cable.origin_id, cable.destination_id} - {None}
        expected = {source_element.id, destination_element.id}
        if endpoints and not endpoints.issubset(expected):
            return JsonResponse({"detail": "As pontas do cabo não correspondem às estruturas das portas escolhidas."}, status=409)
        if endpoints != expected:
            if cable.origin_id in expected and cable.destination_id is None:
                missing_id = next(iter(expected - {cable.origin_id}))
                cable.destination_id = missing_id
            elif cable.destination_id in expected and cable.origin_id is None:
                missing_id = next(iter(expected - {cable.destination_id}))
                cable.origin_id = missing_id
            else:
                cable.origin = source_element
                cable.destination = destination_element
            cable.save(update_fields=["origin", "destination", "updated_at"])
    elif link_type in {MonitoredNetworkLink.LinkType.BACKBONE, MonitoredNetworkLink.LinkType.FIBER}:
        return JsonResponse({"detail": "Selecione o cabo óptico deste enlace."}, status=400)

    try:
        outage = max(0, int(data.get("outage_persistence_seconds") or 30))
        recovery = max(0, int(data.get("recovery_seconds") or 30))
        weight = int(data.get("weight") or 5)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Tempos e espessura precisam ser números."}, status=400)
    severity = str(data.get("severity") or Severity.HIGH)
    if severity not in dict(Severity.choices):
        return JsonResponse({"detail": "Severidade inválida."}, status=400)
    link = MonitoredNetworkLink(
        company=project.company,
        project=project,
        name=str(data.get("name") or "").strip() or f"{source_element.name} ↔ {destination_element.name}",
        code=str(data.get("code") or "").strip(),
        link_type=link_type,
        source_element=source_element,
        destination_element=destination_element,
        source_binding=source_binding,
        destination_binding=destination_binding,
        cable=cable,
        enabled=_as_bool(data.get("enabled"), True),
        require_both_endpoints=_as_bool(data.get("require_both_endpoints"), True),
        alert_enabled=_as_bool(data.get("alert_enabled"), True),
        severity=severity,
        normal_color=str(data.get("normal_color") or ("#a855f7" if link_type == "wireless" else "#38bdf8")),
        down_color="#ef4444",
        dash_array=str(data.get("dash_array") or ("12 10" if link_type == "wireless" else "")),
        weight=weight,
        outage_persistence_seconds=outage,
        recovery_seconds=recovery,
    )
    try:
        link.save()
    except ValidationError as exc:
        return JsonResponse({"detail": _validation_detail(exc)}, status=400)
    poll_snmp_status.delay([source_binding.profile_id, destination_binding.profile_id])
    return JsonResponse({"link": _link_payload(link)}, status=201)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def monitored_link_detail(request, link_id):
    link = get_object_or_404(
        scope_company_queryset(
            MonitoredNetworkLink.objects.select_related("project", "company", "cable", "source_element", "destination_element"),
            request.user,
        ),
        pk=link_id,
    )
    if not can_edit_company(request.user, link.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    if request.method == "DELETE":
        from apps.alerts.models import AlertEvent
        AlertEvent.objects.filter(
            monitored_link=link,
            state__in=[AlertEvent.State.OPEN, AlertEvent.State.ACKNOWLEDGED, AlertEvent.State.RECOVERING],
        ).update(
            state=AlertEvent.State.CLOSED,
            source_status=OperationalStatus.NORMAL,
            closed_at=timezone.now(),
            message=f"Enlace monitorado removido: {link.name}.",
        )
        cable = link.cable
        link.delete()
        if cable and cable.status in {OperationalStatus.OFFLINE, OperationalStatus.NO_DATA, OperationalStatus.DEGRADED}:
            cable.status = OperationalStatus.NO_DATA
            cable.save(update_fields=["status", "updated_at"])
        return JsonResponse({"success": True})
    data = request.data
    for field in (
        "name", "code", "normal_color", "dash_array", "severity",
    ):
        if field in data:
            setattr(link, field, str(data.get(field) or "").strip())
    if link.severity not in dict(Severity.choices):
        return JsonResponse({"detail": "Severidade inválida."}, status=400)
    for field in ("enabled", "require_both_endpoints", "alert_enabled"):
        if field in data:
            setattr(link, field, _as_bool(data.get(field)))
    try:
        for field in ("outage_persistence_seconds", "recovery_seconds", "weight"):
            if field in data:
                setattr(link, field, max(0, int(data.get(field) or 0)))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Tempos e espessura precisam ser números."}, status=400)
    try:
        link.save()
    except ValidationError as exc:
        return JsonResponse({"detail": _validation_detail(exc)}, status=400)
    return JsonResponse({"link": _link_payload(link)})
