from decimal import Decimal, InvalidOperation
import math
import re

import requests
from django.contrib.gis.geos import LineString, MultiLineString, Point
from django.contrib.gis.measure import D
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from apps.access.models import AccessPoint
from apps.ixc_integration.fiber_models import IXCFiberAssignment
from apps.core.crypto import SecretCipher
from apps.core.models import MapBaseConfiguration
from apps.core.access import can_edit_company, can_view_company, scope_company_queryset
from apps.network_map.models import (
    CableModel,
    CableReserve,
    ContainerEquipment,
    ContainerEquipmentCard,
    ContainerEquipmentPort,
    ContainerPortLink,
    CTO,
    CTOSplitter,
    FiberCable,
    FiberStrand,
    FiberSplice,
    NetworkElement,
    NetworkProject,
    PoleCableAttachment,
    PoleEquipmentAttachment,
    SpliceTray,
    SpliceTraySplitter,
    SpliceTraySplitterPort,
)
from apps.network_map.serializers import NetworkElementSerializer, sync_splice_box
from apps.network_map.route_metadata import element_route_payload
from apps.network_map.cto_defaults import ensure_cto_default_splitters
from apps.network_map.services import (
    FiberStructureError,
    generate_cable_fibers,
)


GOOGLE_TILES_BASE_URL = "https://tile.googleapis.com/v1"
GOOGLE_SESSION_PATTERN = re.compile(r"^[A-Za-z0-9_-]{20,2048}$")

# MAP_V07536_OPTICAL_CAPTURE: CEO e CDO só capturam cabos a até 5 m.
OPTICAL_BOX_CAPTURE_RADIUS_M = 5.0


def _google_tiles_configuration():
    configuration = MapBaseConfiguration.objects.filter(
        google_tiles_enabled=True
    ).first()
    if not configuration or not configuration.google_api_key_encrypted:
        return None, ""
    try:
        return configuration, SecretCipher().decrypt(
            configuration.google_api_key_encrypted
        )
    except (RuntimeError, ValueError):
        return configuration, ""


@require_GET
def google_tiles_session(request):
    configuration, api_key = _google_tiles_configuration()
    if not configuration or not api_key:
        return JsonResponse(
            {"detail": "Google Map Tiles não está configurado."},
            status=503,
        )
    try:
        response = requests.post(
            f"{GOOGLE_TILES_BASE_URL}/createSession",
            params={"key": api_key},
            json={
                "mapType": "satellite",
                "language": "pt-BR",
                "region": "BR",
            },
            timeout=15,
        )
    except requests.RequestException:
        return JsonResponse(
            {"detail": "Não foi possível conectar ao Google Map Tiles."},
            status=502,
        )
    if not response.ok:
        try:
            detail = response.json().get("error", {}).get("message")
        except ValueError:
            detail = None
        return JsonResponse(
            {"detail": detail or f"Google Map Tiles respondeu HTTP {response.status_code}."},
            status=502,
        )
    data = response.json()
    return JsonResponse(
        {
            "session": data.get("session"),
            "expiry": data.get("expiry"),
            "tileWidth": data.get("tileWidth", 256),
            "tileHeight": data.get("tileHeight", 256),
        }
    )


@require_GET
def google_satellite_tile(request, z, x, y):
    if z < 0 or z > 22 or x < 0 or y < 0 or x >= 2**z or y >= 2**z:
        return JsonResponse({"detail": "Coordenada de bloco inválida."}, status=400)
    session = request.GET.get("session", "")
    if not GOOGLE_SESSION_PATTERN.fullmatch(session):
        return JsonResponse({"detail": "Sessão do mapa inválida."}, status=400)
    configuration, api_key = _google_tiles_configuration()
    if not configuration or not api_key:
        return JsonResponse(
            {"detail": "Google Map Tiles não está configurado."},
            status=503,
        )
    try:
        response = requests.get(
            f"{GOOGLE_TILES_BASE_URL}/2dtiles/{z}/{x}/{y}",
            params={"session": session, "key": api_key},
            timeout=15,
        )
    except requests.RequestException:
        return JsonResponse({"detail": "Falha ao carregar o bloco."}, status=502)
    if not response.ok:
        return JsonResponse(
            {"detail": f"Google Map Tiles respondeu HTTP {response.status_code}."},
            status=response.status_code if response.status_code < 500 else 502,
        )
    tile = HttpResponse(
        response.content,
        content_type=response.headers.get("Content-Type", "image/jpeg"),
    )
    tile["Cache-Control"] = response.headers.get("Cache-Control", "private, max-age=0")
    return tile


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticatedOrReadOnly])
def pole_infrastructure(request, element_id):
    pole = get_object_or_404(
        NetworkElement,
        pk=element_id,
        element_type=NetworkElement.ElementType.POLE,
    )
    passing_cables = FiberCable.objects.none()
    if pole.point:
        passing_cables = FiberCable.objects.filter(
            project=pole.project,
            geometry__distance_lte=(pole.point, D(m=8)),
        ).order_by("name")

    if request.method == "POST":
        action = request.data.get("action")
        if action == "add_equipment":
            if not pole.point:
                return JsonResponse({"error": "O poste não possui localização no mapa."}, status=400)
            element_type = request.data.get("element_type")
            if element_type not in {
                NetworkElement.ElementType.CTO,
                NetworkElement.ElementType.SPLICE_BOX,
            }:
                return JsonResponse({"error": "Escolha CTO ou CEO."}, status=400)
            name = str(request.data.get("name", "")).strip()
            if not name:
                return JsonResponse({"error": "Informe o nome do equipamento."}, status=400)
            serializer = NetworkElementSerializer(data={
                "project": pole.project_id,
                "element_type": element_type,
                "name": name,
                "code": str(request.data.get("code", "")).strip() or name,
                "latitude": pole.point.y,
                "longitude": pole.point.x,
                "enabled": True,
            })
            if not serializer.is_valid():
                return JsonResponse({"error": serializer.errors}, status=400)
            with transaction.atomic():
                equipment = serializer.save()
                PoleEquipmentAttachment.objects.create(pole=pole, equipment=equipment)
            return JsonResponse({"created": {"id": equipment.id, "name": equipment.name}}, status=201)

        if action == "add_reserve":
            try:
                cable_id = int(request.data.get("cable_id"))
                length_m = Decimal(str(request.data.get("length_m")))
            except (TypeError, ValueError, InvalidOperation):
                return JsonResponse({"error": "Informe o cabo e a metragem da reserva."}, status=400)
            cable = passing_cables.filter(pk=cable_id).first()
            if not cable:
                return JsonResponse(
                    {"error": "A reserva só pode ser adicionada a um cabo que passa pelo poste."},
                    status=400,
                )
            if not length_m.is_finite() or length_m <= 0:
                return JsonResponse({"error": "A metragem deve ser maior que zero."}, status=400)
            reserve = CableReserve.objects.create(
                cable=cable,
                point=pole.point,
                length_m=length_m,
                label=str(request.data.get("label", "")).strip() or f"Reserva · {pole.name}",
            )
            return JsonResponse({"created": {"id": reserve.id, "label": reserve.label}}, status=201)

        return JsonResponse({"error": "Ação inválida."}, status=400)

    installed_equipment = NetworkElement.objects.filter(
        pole_attachment__pole=pole,
    ).order_by("name")
    return JsonResponse({
        "pole": {"id": pole.id, "name": pole.name, "code": pole.code},
        "cables": [
            {"id": cable.id, "name": cable.name}
            for cable in passing_cables
        ],
        "equipment": [
            {"id": item.id, "name": item.name, "type": item.element_type}
            for item in installed_equipment
        ],
    })


def get_first_value(instance, field_names, default=None):
    """
    Retorna o primeiro atributo existente e preenchido.

    Isso permite compatibilidade enquanto os nomes dos campos
    do modelo AccessPoint ainda estão sendo consolidados.
    """
    for field_name in field_names:
        if not hasattr(instance, field_name):
            continue

        value = getattr(instance, field_name)

        if callable(value):
            value = value()

        if value not in (None, ""):
            return value

    return default


def normalize_value(value):
    """
    Converte objetos que não são serializáveis diretamente em JSON.
    """
    if value is None:
        return None

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


def normalize_status(value):
    """
    Normaliza o status para online, offline ou unknown.
    """
    if isinstance(value, bool):
        return "online" if value else "offline"

    if value is None:
        return "unknown"

    normalized = str(value).strip().lower()

    online_values = {
        "online",
        "on",
        "ativo",
        "active",
        "connected",
        "conectado",
        "1",
        "true",
    }

    offline_values = {
        "offline",
        "off",
        "inativo",
        "inactive",
        "disconnected",
        "desconectado",
        "0",
        "false",
    }

    if normalized in online_values:
        return "online"

    if normalized in offline_values:
        return "offline"

    return normalized or "unknown"


@require_GET
def access_points_geojson(request):
    """
    Retorna os acessos com coordenadas no formato GeoJSON.

    Endpoint:
        GET /api/map/access-points/
    """
    features = []

    # Somente acessos ativos vindos do IXC.
    # O filtro também impede que registros inativos antigos apareçam
    # antes da próxima sincronização.
    queryset = list(
        scope_company_queryset(AccessPoint.objects, request.user).filter(
            raw_data__ativo__in=[
                "S",
                "SS",
                "SIM",
                "1",
                "TRUE",
                "s",
                "ss",
                "sim",
                "true",
            ]
        )
    )
    assignments = {}
    assignment_queryset = IXCFiberAssignment.objects.filter(
        company_id__in={item.company_id for item in queryset},
        login__username__in={item.username for item in queryset if item.username},
    ).select_related("login", "cto", "onu")
    for assignment in assignment_queryset:
        assignments.setdefault(
            (assignment.company_id, assignment.login.username),
            assignment,
        )

    for access_point in queryset:
        assignment = assignments.get((access_point.company_id, access_point.username))
        latitude = get_first_value(
            access_point,
            [
                "latitude",
                "lat",
                "client_latitude",
                "customer_latitude",
            ],
        )

        longitude = get_first_value(
            access_point,
            [
                "longitude",
                "lon",
                "lng",
                "client_longitude",
                "customer_longitude",
            ],
        )

        if latitude in (None, "") or longitude in (None, ""):
            continue

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            continue

        # Evita coordenadas vazias ou inválidas.
        if latitude == 0 or longitude == 0:
            continue

        if not (-90 <= latitude <= 90):
            continue

        if not (-180 <= longitude <= 180):
            continue

        customer = get_first_value(
            access_point,
            [
                "customer_name",
                "client_name",
                "cliente",
                "customer",
                "client",
                "name",
            ],
            default="",
        )

        login = get_first_value(
            access_point,
            [
                "login",
                "pppoe_login",
                "username",
                "user",
            ],
            default="",
        )

        raw_status = get_first_value(
            access_point,
            [
                "online",
                "is_online",
                "online_status",
                "status",
                "connection_status",
            ],
            default=None,
        )

        cto = get_first_value(
            access_point,
            [
                "cto",
                "cto_name",
                "cto_id_ixc",
                "ixc_cto",
                "fiber_box",
            ],
            default="",
        )
        if assignment and assignment.cto:
            cto = assignment.cto.name

        onu = get_first_value(
            access_point,
            [
                "onu_mac",
                "onu",
                "onu_serial",
                "onu_identifier",
                "mac_onu",
            ],
            default="",
        )
        if assignment:
            onu = (
                assignment.onu.serial_number if assignment.onu
                else assignment.mac_address or assignment.onu_number or onu
            )

        ftth_port = get_first_value(
            access_point,
            [
                "ftth_port",
                "fiber_port",
                "porta_ftth",
                "port",
            ],
            default="",
        )
        if assignment and assignment.cto_port:
            ftth_port = assignment.cto_port

        concentrator = get_first_value(
            access_point,
            [
                "concentrator",
                "concentrador",
                "nas",
            ],
            default="",
        )

        interface = get_first_value(
            access_point,
            [
                "interface",
                "connection_interface",
            ],
            default="",
        )

        properties = {
            "id": access_point.pk,
            "cliente": normalize_value(customer),
            "login": normalize_value(login),
            "status": normalize_status(raw_status),
            "cto": normalize_value(cto),
            "onu": normalize_value(onu),
            "onu_serial": normalize_value(
                assignment.onu.serial_number
                if assignment and assignment.onu
                else (
                    assignment.raw_data.get("serial")
                    or assignment.raw_data.get("serial_onu")
                    or assignment.raw_data.get("onu_serial")
                    or assignment.raw_data.get("sn")
                    or ""
                ) if assignment else ""
            ),
            "onu_number": normalize_value(assignment.onu_number if assignment else ""),
            "porta_ftth": normalize_value(ftth_port),
            "concentrador": normalize_value(concentrator),
            "interface": normalize_value(interface),
        }

        features.append(
            {
                "type": "Feature",
                "id": access_point.pk,
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        longitude,
                        latitude,
                    ],
                },
                "properties": properties,
            }
        )

    response = {
        "type": "FeatureCollection",
        "count": len(features),
        "features": features,
    }

    return JsonResponse(
        response,
        json_dumps_params={
            "ensure_ascii": False,
            "separators": (",", ":"),
        },
    )


@require_GET
def network_elements_geojson(request):
    """
    Retorna elementos da rede em formato GeoJSON.

    Endpoint:
        GET /api/map/elements/
    """

    features = []

    queryset = NetworkElement.objects.filter(
        enabled=True
    )
    queryset = scope_company_queryset(queryset, request.user)
    project_id = request.GET.get("project_id")
    if project_id:
        queryset = queryset.filter(project_id=project_id)
    queryset = queryset.order_by("id")

    for element in queryset:

        if not element.point:
            continue

        route_payload = element_route_payload(element)
        subtype = str(element.metadata.get("import_subtype") or "").lower()
        features.append(
            {
                "type": "Feature",
                "id": element.id,
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        element.point.x,
                        element.point.y,
                    ],
                },
                "properties": {
                    "id": element.id,
                    "nome": element.name,
                    "codigo": element.code,
                    "tipo": element.element_type,
                    "status": element.status,
                    "project_id": element.project_id,
                    "subtype": subtype,
                    **route_payload,
                },
            }
        )

    return JsonResponse(
        {
            "type": "FeatureCollection",
            "count": len(features),
            "features": features,
        },
        json_dumps_params={
            "ensure_ascii": False,
            "separators": (",", ":"),
        },
    )


@require_GET
def fiber_cables_geojson(request):
    """
    Retorna cabos de fibra em formato GeoJSON.

    Endpoint:
        GET /api/map/cables/
    """

    features = []

    queryset = FiberCable.objects.filter(
        geometry__isnull=False
    ).filter(
        status__isnull=False
    )
    queryset = scope_company_queryset(queryset, request.user)
    project_id = request.GET.get("project_id")
    if project_id:
        queryset = queryset.filter(project_id=project_id)

    optical_adjacency = {}
    splice_queryset = FiberSplice.objects.filter(
        splice_box__project_id=project_id
    ).values_list("input_fiber__cable_id", "output_fiber__cable_id")
    for first_cable_id, second_cable_id in splice_queryset:
        optical_adjacency.setdefault(first_cable_id, set()).add(second_cable_id)
        optical_adjacency.setdefault(second_cable_id, set()).add(first_cable_id)
    splitter_queryset = SpliceTraySplitter.objects.filter(
        tray__splice_box__project_id=project_id,
        input_fiber_id__isnull=False,
        ports__output_fiber_id__isnull=False,
    ).values_list("input_fiber__cable_id", "ports__output_fiber__cable_id")
    for first_cable_id, second_cable_id in splitter_queryset:
        optical_adjacency.setdefault(first_cable_id, set()).add(second_cable_id)
        optical_adjacency.setdefault(second_cable_id, set()).add(first_cable_id)

    # Caminho OLT -> DIO -> cabo dentro de um rack: a fibra do cabo é fundida
    # no fundo de uma porta do DIO (cable_fiber) cuja frente tem o cordão da
    # PON da OLT (source_port). O sinal de luz precisa nascer nesse cabo.
    cable_origin_olt = {}
    fusion_links = ContainerPortLink.objects.filter(
        container__project_id=project_id,
        cable_fiber__isnull=False,
        destination_port__port_type=ContainerEquipmentPort.PortType.DIO,
    ).select_related("cable_fiber")
    dio_port_ids = [link.destination_port_id for link in fusion_links]
    cord_by_dio_port = {
        link.destination_port_id: link.source_port.equipment
        for link in ContainerPortLink.objects.filter(
            destination_port_id__in=dio_port_ids, source_port__isnull=False
        ).select_related("source_port__equipment")
    }
    for link in fusion_links:
        olt = cord_by_dio_port.get(link.destination_port_id)
        if olt and link.cable_fiber_id and link.cable_fiber.cable_id not in cable_origin_olt:
            cable_origin_olt[link.cable_fiber.cable_id] = olt

    for cable in queryset:

        if not cable.geometry:
            continue

        features.append(
            {
                "type": "Feature",
                "id": cable.id,
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": cable.geometry.coords,
                },
                "properties": {
                    "id": cable.id,
                    "nome": cable.name,
                    "codigo": cable.code,
                    "tipo": cable.cable_type,
                    "fibras": cable.fiber_count,
                    "fibras_usadas": cable.used_fibers,
                    "status": cable.status,
                    "project_id": cable.project_id,
                    "route_id": cable.route_id,
                    "route_name": cable.route.name if cable.route_id else "",
                    "route_code": cable.route.code if cable.route_id else "",
                    "route_ids": [cable.route_id] if cable.route_id else [],
                    "route_names": [cable.route.name] if cable.route_id else [],
                    "route_codes": [cable.route.code] if cable.route_id else [],
                    "origem": (
                        cable.origin.name
                        if cable.origin
                        else None
                    ),
                    "origin_id": cable.origin_id,
                    "destination_id": cable.destination_id,
                    "origin_olt_id": getattr(cable_origin_olt.get(cable.id), "id", None),
                    "origin_olt_name": getattr(cable_origin_olt.get(cable.id), "name", None),
                    "optical_next_cable_ids": sorted(
                        optical_adjacency.get(cable.id, set())
                    ),
                    "destino": (
                        cable.destination.name
                        if cable.destination
                        else None
                    ),
                    "reservas": [
                        {
                            "id": reserve.id,
                            "latitude": reserve.point.y,
                            "longitude": reserve.point.x,
                            "metragem": float(reserve.length_m),
                            "label": reserve.label,
                        }
                        for reserve in cable.reserves.all()
                    ],
                },
            }
        )

    return JsonResponse(
        {
            "type": "FeatureCollection",
            "count": len(features),
            "features": features,
        },
        json_dumps_params={
            "ensure_ascii": False,
            "separators": (",", ":"),
        },
    )


from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework import status


def element_detail_payload(element):
    payload = {
        "id": element.id,
        "name": element.name,
        "code": element.code,
        "description": element.description,
        "project_id": element.project_id,
        "element_type": element.element_type,
        "status": element.status,
        "enabled": element.enabled,
        "internal_equipment": element.metadata.get("internal_equipment", []),
        "metadata": element.metadata,
        "element_subtype": element.metadata.get("import_subtype", ""),
        "latitude": element.point.y if element.point else None,
        "longitude": element.point.x if element.point else None,
        "cto": None,
        "splice_box": None,
    }
    try:
        cto = element.cto
    except CTO.DoesNotExist:
        cto = None
    if cto is not None:
        # CTOs importadas por versões antigas podiam chegar sem ratio e sem
        # bandeja. Isso fazia sync_splice_box receber uma string vazia e
        # derrubar /api/map/elements/<id>/ com HTTP 500.
        if not cto.splitters.exists() or not element.splice_trays.exists():
            ensure_cto_default_splitters(cto, cto.capacity)
        connected_cables = FiberCable.objects.filter(
            Q(origin=cto) | Q(destination=cto)
        ).order_by("name")
        payload["cto"] = {
            "capacity": cto.capacity,
            "splitter_ratio": cto.splitter_ratio,
            "connected_cables": [
                {
                    "id": cable.id,
                    "name": cable.name,
                    "code": cable.code,
                    "fiber_count": cable.fiber_count,
                }
                for cable in connected_cables
            ],
            "splitters": [
                {
                    "id": splitter.id,
                    "name": splitter.name,
                    "ratio": splitter.ratio,
                    "output_ports": splitter.output_ports,
                    "input_cable": (
                        {
                            "id": splitter.input_cable_id,
                            "name": splitter.input_cable.name,
                            "code": splitter.input_cable.code,
                        }
                        if splitter.input_cable_id else None
                    ),
                    "input_fiber": (
                        {
                            "id": splitter.input_fiber_id,
                            "number": splitter.input_fiber.number,
                            "color_name": splitter.input_fiber.color.name,
                            "color_hex": splitter.input_fiber.color.hex_color,
                        }
                        if splitter.input_fiber_id else None
                    ),
                    "ports": [
                        {
                            "id": port.id,
                            "number": port.number,
                            "label": port.label,
                            "status": port.status,
                            "status_label": port.get_status_display(),
                            "access_point_id": port.access_point_id,
                        }
                        for port in splitter.ports.all()
                    ],
                }
                for splitter in cto.splitters.select_related(
                    "input_cable", "input_fiber__color"
                ).prefetch_related("ports").all()
            ],
        }
    if element.element_type in {
        NetworkElement.ElementType.SPLICE_BOX,
        NetworkElement.ElementType.CTO,
    }:
        trays = element.splice_trays.prefetch_related("splitters", "splices").all()
        payload["splice_box"] = {
            "tray_count": len(trays),
            "splitters_per_tray": max(
                [tray.splitters.count() for tray in trays] or [0]
            ),
            "splitter_ratio": next(
                (
                    splitter.ratio
                    for tray in trays
                    for splitter in tray.splitters.all()
                ),
                "1:8",
            ),
            "trays": [
                {
                    "id": tray.id,
                    "number": tray.number,
                    "name": tray.name,
                    "capacity": tray.capacity,
                    "splice_count": tray.splices.count(),
                    "splitters": [
                        {
                            "id": splitter.id,
                            "position": splitter.position,
                            "ratio": splitter.ratio,
                            "output_ports": splitter.output_ports,
                            "input_fiber_id": splitter.input_fiber_id,
                            "input_splitter_port_id": splitter.input_splitter_port_id,
                            "ports": [
                                {
                                    "id": port.id,
                                    "number": port.number,
                                    "output_fiber_id": port.output_fiber_id,
                                }
                                for port in splitter.ports.all()
                            ],
                        }
                        for splitter in tray.splitters.prefetch_related("ports").all()
                    ],
                }
                for tray in trays
            ],
        }
    return payload


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def container_equipment(request, element_id):
    container = get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type__in=[NetworkElement.ElementType.RACK, NetworkElement.ElementType.TOWER],
    )
    if request.method == "POST":
        if not can_edit_company(request.user, container.company_id):
            return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
        requested_equipment_type = str(request.data.get("equipment_type", "")).strip()
        is_onu = requested_equipment_type == "onu"
        # IXCSOFT_MAP_MASTER_SUITE_V1: ONU/PTO e ativos são tipos reais.
        equipment_type = requested_equipment_type
        allowed = (
            {
                ContainerEquipment.EquipmentType.OLT,
                ContainerEquipment.EquipmentType.DIO,
                ContainerEquipment.EquipmentType.SWITCH,
                ContainerEquipment.EquipmentType.ROUTER,
                ContainerEquipment.EquipmentType.FIREWALL,
                ContainerEquipment.EquipmentType.SERVER,
                ContainerEquipment.EquipmentType.PTO,
                ContainerEquipment.EquipmentType.OTHER,
            }
            if container.element_type == NetworkElement.ElementType.RACK
            else {
                ContainerEquipment.EquipmentType.OLT,
                ContainerEquipment.EquipmentType.SWITCH,
                ContainerEquipment.EquipmentType.ACCESS_POINT,
                ContainerEquipment.EquipmentType.PTP,
                ContainerEquipment.EquipmentType.DIO,
                ContainerEquipment.EquipmentType.ROUTER,
                ContainerEquipment.EquipmentType.FIREWALL,
                ContainerEquipment.EquipmentType.ONU,
                ContainerEquipment.EquipmentType.PTO,
                ContainerEquipment.EquipmentType.OTHER,
            }
        )
        if equipment_type not in allowed:
            return JsonResponse({"detail": "Tipo de equipamento inválido para esta estrutura."}, status=400)
        equipment_name = str(request.data.get("name", "")).strip()
        if not equipment_name:
            return JsonResponse({"detail": "Informe o nome do equipamento."}, status=400)
        try:
            dio_capacity = int(request.data.get("dio_port_capacity") or 0)
            card_count = int(request.data.get("card_count") or 0)
            pons_per_card = int(request.data.get("pons_per_card") or 0)
            onu_lan_count = int(request.data.get("onu_lan_count") or 4)
            # MAP_V07557_TOWER_SWITCH_PORTS: o diálogo genérico "+ Equipamento"
            # não tinha campo de quantidade de portas — sem isto, Switch/
            # Router/Firewall/Servidor sempre caíam no valor padrão.
            port_count = int(request.data["port_count"]) if request.data.get("port_count") else None
        except (TypeError, ValueError):
            return JsonResponse({"detail": "Capacidades informadas são inválidas."}, status=400)
        if is_onu and not 1 <= onu_lan_count <= 16:
            return JsonResponse({"detail": "A ONU deve possuir de 1 a 16 portas LAN."}, status=400)
        if equipment_type == ContainerEquipment.EquipmentType.DIO and dio_capacity not in {
            12, 24, 36, 48, 72, 96, 144, 192, 244,
        }:
            return JsonResponse({"detail": "Escolha uma capacidade padrão para o DIO."}, status=400)
        if (
            container.element_type == NetworkElement.ElementType.TOWER
            and equipment_type == ContainerEquipment.EquipmentType.DIO
            and dio_capacity > 24
        ):
            return JsonResponse(
                {"detail": "Na Torre, o Canvas 2D aceita DIO de até 24 portas. Use um Rack para DIOs maiores."},
                status=400,
            )
        connector_type = str(request.data.get("connector_type", "")).strip()
        if connector_type and connector_type not in dict(ContainerEquipment.ConnectorType.choices):
            return JsonResponse({"detail": "Tipo de conector inválido."}, status=400)
        provisioning_mode = request.data.get("provisioning_mode") or "manual"
        management_ip = request.data.get("management_ip") or None
        if (
            equipment_type == ContainerEquipment.EquipmentType.OLT
            and provisioning_mode == ContainerEquipment.ProvisioningMode.SNMP
            and not management_ip
        ):
            return JsonResponse({"detail": "Informe o IP de gerência para cadastro por SNMP."}, status=400)
        tx_power_dbm = None
        if equipment_type == ContainerEquipment.EquipmentType.OLT and request.data.get("tx_power_dbm"):
            try:
                tx_power_dbm = Decimal(str(request.data["tx_power_dbm"]))
            except (InvalidOperation, ValueError):
                return JsonResponse({"detail": "Potência de saída inválida."}, status=400)
        metadata = {}
        if is_onu:
            metadata.update({
                "equipment_subtype": "onu",
                "onu_lan_count": onu_lan_count,
                "pon_connector": "SC/APC",
            })
        elif equipment_type == ContainerEquipment.EquipmentType.OTHER:
            metadata["equipment_subtype"] = str(request.data.get("equipment_subtype") or "other").strip() or "other"
        if port_count and equipment_type in {
            ContainerEquipment.EquipmentType.SWITCH,
            ContainerEquipment.EquipmentType.ROUTER,
            ContainerEquipment.EquipmentType.FIREWALL,
            ContainerEquipment.EquipmentType.SERVER,
        }:
            metadata["port_count"] = max(1, min(port_count, 96))
        snmp_community = str(request.data.get("snmp_community", "")).strip()
        if snmp_community:
            metadata["snmp_community_encrypted"] = SecretCipher().encrypt(snmp_community)
        drop_cable = None
        drop_cable_id = request.data.get("drop_cable_id")
        if is_onu and drop_cable_id:
            drop_cable = get_object_or_404(
                FiberCable.objects.filter(Q(origin=container) | Q(destination=container)),
                pk=drop_cable_id,
                company=container.company,
                cable_type=FiberCable.CableType.DROP,
            )
        with transaction.atomic():
            equipment = ContainerEquipment.objects.create(
                company=container.company,
                container=container,
                name=equipment_name,
                description=str(request.data.get("description", "")).strip(),
                equipment_type=equipment_type,
                management_ip=management_ip if equipment_type != ContainerEquipment.EquipmentType.DIO else None,
                connector_type=(
                    ContainerEquipment.ConnectorType.SC_APC
                    if is_onu
                    else connector_type
                    if equipment_type in {
                        ContainerEquipment.EquipmentType.DIO,
                        ContainerEquipment.EquipmentType.PTO,
                    }
                    else ""
                ),
                tx_power_dbm=tx_power_dbm,
                provisioning_mode=provisioning_mode,
                vendor=str(request.data.get("vendor", "")).strip(),
                model=str(request.data.get("model", "")).strip(),
                serial_number=str(request.data.get("serial_number", "")).strip(),
                card_count=max(0, min(card_count, 64)),
                pons_per_card=max(0, min(pons_per_card, 64)),
                dio_port_capacity=dio_capacity,
                metadata=metadata,
            )
            _generate_container_equipment_ports(equipment)
            if drop_cable:
                pon_port = equipment.ports.filter(
                    port_type=ContainerEquipmentPort.PortType.PON
                ).first()
                ContainerPortLink.objects.create(
                    container=container,
                    destination_port=pon_port,
                    cable=drop_cable,
                    link_type=ContainerPortLink.LinkType.FIBER,
                    notes="DROP com conector direto na ONU / ONT",
                    loss_db=Decimal("0.10"),
                )
        return JsonResponse({"equipment": _container_equipment_payload(equipment)}, status=201)
    return JsonResponse({
        "container": {"id": container.id, "name": container.name, "type": container.element_type},
        "equipment": [
            _container_equipment_payload(item)
            for item in container.internal_equipments.prefetch_related(
                "cards", "ports__incoming_links", "ports__outgoing_link"
            ).exclude(equipment_type=ContainerEquipment.EquipmentType.SERVER)
        ],
        "cables": [
            {
                "id": cable.id,
                "name": cable.name,
                "fiber_count": cable.fiber_count,
                "cable_type": cable.cable_type,
                "cable_type_label": cable.get_cable_type_display(),
                "relation": "input" if cable.destination_id == container.id else "output",
                "fibers": [_fiber_payload(fiber) for fiber in cable.fibers.select_related("color").all()],
            }
            for cable in FiberCable.objects.filter(company=container.company)
            .filter(Q(origin=container) | Q(destination=container))
            .prefetch_related("fibers__color", "fibers__container_port_links")
            .order_by("name")
        ],
        "links": [
            {
                "id": link.id,
                "source_port_id": link.source_port_id,
                "source": (
                    f"{link.source_port.equipment.name} · {link.source_port.label}"
                    if link.source_port
                    else f"DROP · {link.cable.name if link.cable else 'Entrada externa'}"
                ),
                "destination_port_id": link.destination_port_id,
                "destination": f"{link.destination_port.equipment.name} · {link.destination_port.label}",
                "cable_id": link.cable_id,
                "cable_fiber_id": link.cable_fiber_id,
                "cable": link.cable.name if link.cable else "",
                "link_type": link.link_type,
                "link_type_label": link.get_link_type_display(),
            }
            for link in container.internal_port_links.select_related(
                "source_port__equipment", "destination_port__equipment", "cable"
            )
        ],
    })


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def container_equipment_detail(request, element_id, equipment_id):
    equipment = get_object_or_404(
        ContainerEquipment.objects.select_related("container"),
        pk=equipment_id,
        container_id=element_id,
    )
    if not can_edit_company(request.user, equipment.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    if request.method == "DELETE":
        equipment.delete()
        return HttpResponse(status=204)
    data = request.data
    update_fields = []
    for field in ("name", "vendor", "model", "serial_number", "description"):
        if field in data:
            setattr(equipment, field, str(data[field]).strip())
            update_fields.append(field)
    if "management_ip" in data and equipment.equipment_type != ContainerEquipment.EquipmentType.DIO:
        equipment.management_ip = data["management_ip"] or None
        update_fields.append("management_ip")
    if "provisioning_mode" in data and equipment.equipment_type == ContainerEquipment.EquipmentType.OLT:
        equipment.provisioning_mode = data["provisioning_mode"]
        update_fields.append("provisioning_mode")
    if "connector_type" in data and equipment.equipment_type == ContainerEquipment.EquipmentType.DIO:
        connector_type = str(data["connector_type"]).strip()
        if connector_type and connector_type not in dict(ContainerEquipment.ConnectorType.choices):
            return JsonResponse({"detail": "Tipo de conector inválido."}, status=400)
        equipment.connector_type = connector_type
        update_fields.append("connector_type")
    if "tx_power_dbm" in data and equipment.equipment_type == ContainerEquipment.EquipmentType.OLT:
        raw_power = data.get("tx_power_dbm")
        if raw_power:
            try:
                equipment.tx_power_dbm = Decimal(str(raw_power))
            except (InvalidOperation, ValueError):
                return JsonResponse({"detail": "Potência de saída inválida."}, status=400)
        else:
            equipment.tx_power_dbm = None
        update_fields.append("tx_power_dbm")
    snmp_community = str(data.get("snmp_community", "")).strip()
    if snmp_community:
        metadata = dict(equipment.metadata)
        metadata["snmp_community_encrypted"] = SecretCipher().encrypt(snmp_community)
        equipment.metadata = metadata
        update_fields.append("metadata")
    if update_fields:
        equipment.save(update_fields=[*update_fields, "updated_at"])
    return JsonResponse({"equipment": _container_equipment_payload(equipment)})


def _cord_link(port):
    """Ligação de cordão (frente da porta): equipamento a equipamento, ex.: PON da OLT -> porta do DIO."""
    outgoing = getattr(port, "outgoing_link", None)
    if outgoing:
        return outgoing
    return next((link for link in port.incoming_links.all() if link.source_port_id), None)


def _fusion_link(port):
    """Ligação de fusão (fundo da porta): fibra do cabo fundida na porta do DIO."""
    return next((link for link in port.incoming_links.all() if link.cable_fiber_id), None)


def _external_cable_link(port):
    """Terminação direta de um cabo externo na porta, como DROP -> PON da ONU."""
    return next(
        (
            link
            for link in port.incoming_links.all()
            if link.source_port_id is None and link.cable_id
        ),
        None,
    )


def _linked_cable_name(port):
    link = _cord_link(port) or _external_cable_link(port)
    return link.cable.name if link and link.cable else None


def _fusion_cable_name(port):
    link = _fusion_link(port)
    return link.cable.name if link and link.cable else None


def _port_budget_dbm(port):
    """Potência estimada (dBm) injetada no cabo nesta porta: TX da OLT menos
    a perda do cordão (frente) e da fusão (fundo), quando conhecidas."""
    cord = _cord_link(port)
    if not cord or not cord.source_port_id:
        return None
    olt = cord.source_port.equipment
    if olt.tx_power_dbm is None:
        return None
    power = float(olt.tx_power_dbm) - float(cord.loss_db)
    fusion = _fusion_link(port)
    if fusion:
        power -= float(fusion.loss_db)
    return round(power, 2)


# Orçamento óptico de PROJETO. Estes valores são estimativas, não medição.
# Regras operacionais solicitadas: porta DIO 0,50 dB; cada fusão 0,10 dB.
DIO_PORT_LOSS_DB = 0.50
FUSION_LOSS_DB = 0.10
FIBER_ATTENUATION_DB_PER_KM = 0.35

# Perdas máximas de referência para PLC balanceado (famílias comerciais FTTH).
BALANCED_SPLITTER_LOSS_DB = {
    "1:2": 3.7, "1:4": 7.0, "1:8": 10.5, "1:16": 13.5, "1:32": 16.7, "1:64": 20.4,
}

# FBT 1x2 desbalanceado. O modelo grava a perna de menor percentual primeiro
# (ex. 10:90), então P1 = saída secundária/baixa potência e P2 = saída
# primária/alta potência. Valores máximos de inserção de referência.
UNBALANCED_SPLITTER_LOSS_DB = {
    "10:90": (11.2, 0.8),
    "15:85": (9.2, 1.0),
    "20:80": (7.8, 1.3),
    "30:70": (6.0, 2.0),
    "40:60": (4.7, 2.7),
    "45:55": (4.1, 3.2),
}


def _cable_length_km(cable):
    if not cable or not cable.geometry:
        return 0.0
    try:
        return cable.geometry.transform(3857, clone=True).length / 1000
    except Exception:
        return 0.0


def _splitter_output_loss_db(ratio, port_number):
    if ratio in BALANCED_SPLITTER_LOSS_DB:
        return BALANCED_SPLITTER_LOSS_DB[ratio]
    if ratio in UNBALANCED_SPLITTER_LOSS_DB:
        try:
            return UNBALANCED_SPLITTER_LOSS_DB[ratio][int(port_number) - 1]
        except (ValueError, IndexError, TypeError):
            return 0.0
    return 0.0


def _trace_fiber_upstream(fiber, visited=None):
    """Percorre a fibra para trás (cordão/fusão -> emenda -> splitter -> cabo
    anterior) até achar a OLT de origem. Retorna (caminho, perda_total_db,
    potencia_tx_dbm) — potencia_tx_dbm vem None se a OLT não tiver potência
    cadastrada, ou se o caminho não chegar a nenhuma OLT."""
    visited = visited if visited is not None else set()
    if fiber is None or ("fiber", fiber.id) in visited or len(visited) > 40:
        return [], 0.0, None
    visited.add(("fiber", fiber.id))

    fusion = ContainerPortLink.objects.filter(
        cable_fiber=fiber, destination_port__port_type=ContainerEquipmentPort.PortType.DIO,
    ).select_related("destination_port__equipment").first()
    if fusion:
        cord = ContainerPortLink.objects.filter(
            destination_port=fusion.destination_port, source_port__isnull=False,
        ).select_related("source_port__equipment").first()
        loss = FUSION_LOSS_DB
        path = [{"type": "dio", "name": fusion.destination_port.equipment.name}]
        if cord:
            olt = cord.source_port.equipment
            loss += DIO_PORT_LOSS_DB
            path.insert(0, {"type": "olt", "name": olt.name})
            tx_power = float(olt.tx_power_dbm) if olt.tx_power_dbm is not None else None
            return path, loss, tx_power
        return path, loss, None

    splice = FiberSplice.objects.filter(output_fiber=fiber).select_related(
        "input_fiber__cable", "splice_box",
    ).first()
    if splice:
        upstream_path, upstream_loss, tx_power = _trace_fiber_upstream(splice.input_fiber, visited)
        cable_km = _cable_length_km(splice.input_fiber.cable)
        loss = upstream_loss + FUSION_LOSS_DB + cable_km * FIBER_ATTENUATION_DB_PER_KM
        return [*upstream_path, {"type": "splice_box", "name": splice.splice_box.name}], loss, tx_power

    port = SpliceTraySplitterPort.objects.filter(output_fiber=fiber).select_related(
        "splitter__input_fiber__cable", "splitter__input_splitter_port",
        "splitter__tray__splice_box",
    ).first()
    if port:
        return _trace_splitter_port_upstream(port, visited)

    return [], 0.0, None


def _trace_splitter_port_upstream(port, visited=None):
    """Percorre para trás a partir de uma porta de saída de splitter. Uma
    porta pode alimentar outra fibra normal OU, em cascata, entrar
    diretamente na entrada de outro splitter sem que exista uma fibra
    própria entre os dois (splitter->splitter físico dentro da mesma
    caixa) — por isso este cálculo não depende de `output_fiber`."""
    visited = visited if visited is not None else set()
    if port is None or ("port", port.id) in visited or len(visited) > 40:
        return [], 0.0, None
    visited.add(("port", port.id))

    splitter = port.splitter
    if splitter.input_fiber_id:
        upstream_path, upstream_loss, tx_power = _trace_fiber_upstream(splitter.input_fiber, visited)
        cable_loss = _cable_length_km(splitter.input_fiber.cable) * FIBER_ATTENUATION_DB_PER_KM
    elif splitter.input_splitter_port_id:
        upstream_path, upstream_loss, tx_power = _trace_splitter_port_upstream(
            splitter.input_splitter_port, visited
        )
        cable_loss = 0.0
    else:
        return [], 0.0, None
    split_loss = _splitter_output_loss_db(splitter.ratio, port.number)
    loss = upstream_loss + cable_loss + split_loss
    box_name = splitter.tray.splice_box.name
    return [*upstream_path, {"type": "splitter", "name": f"Splitter {splitter.ratio} · {box_name}"}], loss, tx_power


def _fiber_budget_payload(fiber, element=None):
    path, loss_db, tx_power = _trace_fiber_upstream(fiber)
    # _trace_fiber_upstream devolve a potência no INÍCIO do segmento atual.
    # Ao inspecionar a fibra numa caixa que é o destino desse cabo, soma-se
    # também a atenuação do próprio segmento para obter a potência NA PONTA.
    if fiber is not None and element is not None and fiber.cable.destination_id == element.id:
        cable_loss = _cable_length_km(fiber.cable) * FIBER_ATTENUATION_DB_PER_KM
        loss_db += cable_loss
        path = [*path, {"type": "cable", "name": fiber.cable.name}]
    payload = {
        "path": path,
        "loss_db": round(loss_db, 2),
        "tx_dbm": round(tx_power, 2) if tx_power is not None else None,
        "budget_dbm": None,
        "estimated": True,
    }
    if tx_power is not None:
        payload["budget_dbm"] = round(tx_power - loss_db, 2)
    return payload


def _splitter_port_budget_payload(port):
    path, loss_db, tx_power = _trace_splitter_port_upstream(port)
    payload = {
        "path": path,
        "loss_db": round(loss_db, 2),
        "tx_dbm": round(tx_power, 2) if tx_power is not None else None,
        "budget_dbm": None,
        "estimated": True,
    }
    if tx_power is not None:
        payload["budget_dbm"] = round(tx_power - loss_db, 2)
    return payload


def _fiber_payload(fiber):
    link = fiber.container_port_links.first()
    return {
        "id": fiber.id,
        "number": fiber.number,
        "color_name": fiber.color.name,
        "color_hex": fiber.color.hex_color,
        "used": link is not None,
        "link_id": link.id if link else None,
        "used_by": (
            f"{link.destination_port.equipment.name} · {link.destination_port.label}"
            if link and link.destination_port_id
            else None
        ),
    }


def _container_equipment_payload(item):
    return {
        "id": item.id,
        "metadata": item.metadata or {},
        "name": item.name,
        "type": (
            "onu"
            if item.equipment_type == ContainerEquipment.EquipmentType.ONU
            or (
                item.equipment_type == ContainerEquipment.EquipmentType.OTHER
                and item.metadata.get("equipment_subtype") == "onu"
            )
            else item.equipment_type
        ),
        "type_label": (
            "ONU / ONT"
            if item.equipment_type == ContainerEquipment.EquipmentType.ONU
            or (
                item.equipment_type == ContainerEquipment.EquipmentType.OTHER
                and item.metadata.get("equipment_subtype") == "onu"
            )
            else item.get_equipment_type_display()
        ),
        "management_ip": item.management_ip,
        "provisioning_mode": item.provisioning_mode,
        "monitoring_eligible": item.enabled and item.equipment_type in {
            ContainerEquipment.EquipmentType.SWITCH,
            ContainerEquipment.EquipmentType.ROUTER,
            ContainerEquipment.EquipmentType.FIREWALL,
            ContainerEquipment.EquipmentType.ACCESS_POINT,
            ContainerEquipment.EquipmentType.PTP,
            ContainerEquipment.EquipmentType.ONU,
            ContainerEquipment.EquipmentType.OTHER,
        },
        "monitoring_configured": (
            item.provisioning_mode == ContainerEquipment.ProvisioningMode.SNMP
            and bool(item.management_ip)
        ),
        "tx_power_dbm": float(item.tx_power_dbm) if item.tx_power_dbm is not None else None,
        "vendor": item.vendor,
        "model": item.model,
        "serial_number": item.serial_number,
        "connector_type": item.connector_type,
        "connector_type_label": item.get_connector_type_display(),
        "has_snmp_community": bool(item.metadata.get("snmp_community_encrypted")),
        "card_count": item.card_count,
        "pons_per_card": item.pons_per_card,
        "pon_count": item.ports.filter(port_type=ContainerEquipmentPort.PortType.PON).count(),
        "dio_port_capacity": item.dio_port_capacity,
        "cards": [
            {
                "id": card.id,
                "slot": card.slot,
                "name": card.name or f"Placa {card.slot}",
                "model": card.model,
                "serial_number": card.serial_number,
                "pon_count": card.pon_count,
            }
            for card in item.cards.all()
        ],
        "ports": [
            {
                "id": port.id,
                "type": port.port_type,
                "number": port.number,
                "card_number": port.card_number,
                "port_number": port.port_number,
                "label": port.label,
                "used": _cord_link(port) is not None or _external_cable_link(port) is not None,
                "linked_cable": _linked_cable_name(port),
                "link_id": getattr(_cord_link(port) or _external_cable_link(port), "id", None),
                "link_loss_db": (
                    float((_cord_link(port) or _external_cable_link(port)).loss_db)
                    if (_cord_link(port) or _external_cable_link(port))
                    else None
                ),
                "fusion_used": _fusion_link(port) is not None,
                "fusion_link_id": getattr(_fusion_link(port), "id", None),
                "fusion_linked_cable": _fusion_cable_name(port),
                "fusion_loss_db": float(_fusion_link(port).loss_db) if _fusion_link(port) else None,
                "budget_dbm": _port_budget_dbm(port),
            }
            for port in item.ports.all()
        ],
    }


def _generate_container_equipment_ports(equipment):
    ports = []
    if equipment.equipment_type == ContainerEquipment.EquipmentType.OLT:
        number = 0
        for card in range(1, equipment.card_count + 1):
            card_obj = ContainerEquipmentCard.objects.create(
                equipment=equipment,
                slot=card,
                name=f"Placa {card}",
                pon_count=equipment.pons_per_card,
            )
            for pon in range(1, equipment.pons_per_card + 1):
                number += 1
                ports.append(ContainerEquipmentPort(
                    equipment=equipment,
                    card=card_obj,
                    port_type=ContainerEquipmentPort.PortType.PON,
                    number=number,
                    card_number=card,
                    port_number=pon,
                    label=f"Placa {card} / PON {pon}",
                ))
    elif (
        equipment.equipment_type == ContainerEquipment.EquipmentType.ONU
        or (
            equipment.equipment_type == ContainerEquipment.EquipmentType.OTHER
            and equipment.metadata.get("equipment_subtype") == "onu"
        )
    ):
        lan_count = max(1, min(int(equipment.metadata.get("onu_lan_count") or 4), 16))
        ports = [
            ContainerEquipmentPort(
                equipment=equipment,
                port_type=ContainerEquipmentPort.PortType.PON,
                number=1,
                port_number=1,
                label="PON 1 · SC/APC",
            )
        ]
        ports.extend(
            ContainerEquipmentPort(
                equipment=equipment,
                port_type=ContainerEquipmentPort.PortType.RJ45_1G,
                number=number + 1,
                port_number=number,
                label=f"LAN {number}",
            )
            for number in range(1, lan_count + 1)
        )
    elif equipment.equipment_type == ContainerEquipment.EquipmentType.PTO:
        ports = [ContainerEquipmentPort(
            equipment=equipment,
            port_type=ContainerEquipmentPort.PortType.DIO,
            number=1,
            port_number=1,
            label=f"PTO 1 · {equipment.get_connector_type_display() or 'SC/APC'}",
        )]
    elif equipment.equipment_type == ContainerEquipment.EquipmentType.DIO:
        ports = [
            ContainerEquipmentPort(
                equipment=equipment,
                port_type=ContainerEquipmentPort.PortType.DIO,
                number=number,
                port_number=number,
                label=f"Porta {number}",
            )
            for number in range(1, equipment.dio_port_capacity + 1)
        ]
    elif equipment.equipment_type in {
        ContainerEquipment.EquipmentType.SWITCH,
        ContainerEquipment.EquipmentType.ROUTER,
        ContainerEquipment.EquipmentType.FIREWALL,
        ContainerEquipment.EquipmentType.SERVER,
    }:
        # MAP_V07557_TOWER_SWITCH_PORTS: este endpoint (container_equipment,
        # usado pelo diálogo genérico "+ Equipamento" da Torre) nunca gerava
        # nenhuma porta pra Switch/Router/Firewall/Servidor — só o diálogo
        # próprio do Rack (equipment_collection_v07539) fazia isso. Um
        # Switch criado pela Torre ficava com 0 portas reais, e o editor de
        # portas mostrava "Da porta 1 até 1" (o mínimo de segurança da UI),
        # sem deixar editar nada de verdade.
        default_count = 24 if equipment.equipment_type == ContainerEquipment.EquipmentType.SWITCH else 8
        port_count = max(1, min(int(equipment.metadata.get("port_count") or default_count), 96))
        ports = [
            ContainerEquipmentPort(
                equipment=equipment,
                port_type=ContainerEquipmentPort.PortType.RJ45_1G,
                number=number,
                port_number=number,
                label=f"Porta {number}",
            )
            for number in range(1, port_count + 1)
        ]
    elif equipment.equipment_type in {
        ContainerEquipment.EquipmentType.PTP,
        ContainerEquipment.EquipmentType.ACCESS_POINT,
    }:
        # MAP_V07514_PTP_DEFAULT_WIRELESS_PORT: sem isto, um rádio PTP ou AP
        # recém-criado ficava sem nenhuma porta — o clique em "Ligar PTP?"
        # nunca aparecia porque não existia porta wireless pra clicar, e
        # nada indicava ao usuário que era preciso adicionar uma manualmente
        # antes de usar o enlace.
        ports = [ContainerEquipmentPort(
            equipment=equipment,
            port_type=ContainerEquipmentPort.PortType.WIRELESS,
            number=1,
            port_number=1,
            label="Interface wireless",
        )]
    ContainerEquipmentPort.objects.bulk_create(ports)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def container_equipment_cards(request, element_id, equipment_id):
    equipment = get_object_or_404(
        ContainerEquipment.objects.select_related("container"),
        pk=equipment_id,
        container_id=element_id,
        equipment_type=ContainerEquipment.EquipmentType.OLT,
    )
    if not can_edit_company(request.user, equipment.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    try:
        slot = int(request.data.get("slot") or 0)
        pon_count = int(request.data.get("pon_count") or 0)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Slot e quantidade de PONs devem ser números."}, status=400)
    if slot < 1 or slot > 64 or pon_count < 1 or pon_count > 64:
        return JsonResponse({"detail": "Use slot e quantidade de PONs entre 1 e 64."}, status=400)
    if equipment.cards.filter(slot=slot).exists():
        return JsonResponse({"detail": "Já existe uma placa neste slot."}, status=409)
    with transaction.atomic():
        card = ContainerEquipmentCard.objects.create(
            equipment=equipment,
            slot=slot,
            name=str(request.data.get("name", "")).strip() or f"Placa {slot}",
            model=str(request.data.get("model", "")).strip(),
            serial_number=str(request.data.get("serial_number", "")).strip(),
            pon_count=pon_count,
        )
        next_number = equipment.ports.order_by("-number").values_list("number", flat=True).first() or 0
        ContainerEquipmentPort.objects.bulk_create([
            ContainerEquipmentPort(
                equipment=equipment,
                card=card,
                port_type=ContainerEquipmentPort.PortType.PON,
                number=next_number + pon,
                card_number=slot,
                port_number=pon,
                label=f"{card.name} / PON {pon}",
            )
            for pon in range(1, pon_count + 1)
        ])
        equipment.card_count = equipment.cards.count()
        equipment.save(update_fields=["card_count", "updated_at"])
    return JsonResponse({"equipment": _container_equipment_payload(equipment)}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def container_equipment_ports(request, element_id, equipment_id):
    equipment = get_object_or_404(
        ContainerEquipment.objects.select_related("container"),
        pk=equipment_id,
        container_id=element_id,
    )
    if not can_edit_company(request.user, equipment.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    allowed_types = {
        ContainerEquipmentPort.PortType.RJ45_100M,
        ContainerEquipmentPort.PortType.RJ45_1G,
        ContainerEquipmentPort.PortType.RJ45_2G5,
        ContainerEquipmentPort.PortType.SFP_1G,
        ContainerEquipmentPort.PortType.SFP_PLUS_10G,
        ContainerEquipmentPort.PortType.SFP28_25G,
        ContainerEquipmentPort.PortType.QSFP_PLUS_40G,
        ContainerEquipmentPort.PortType.QSFP28_100G,
        ContainerEquipmentPort.PortType.SC_APC,
        ContainerEquipmentPort.PortType.SC_UPC,
        ContainerEquipmentPort.PortType.LC,
        ContainerEquipmentPort.PortType.WIRELESS,
        ContainerEquipmentPort.PortType.POWER,
        ContainerEquipmentPort.PortType.PON,
    }
    port_type = str(request.data.get("port_type", "")).strip()
    try:
        count = int(request.data.get("count") or 0)
    except (TypeError, ValueError):
        count = 0
    if port_type not in allowed_types or count < 1 or count > 256:
        return JsonResponse({"detail": "Informe um tipo válido e de 1 a 256 portas."}, status=400)
    start = equipment.ports.order_by("-number").values_list("number", flat=True).first() or 0
    label = dict(ContainerEquipmentPort.PortType.choices)[port_type]
    ContainerEquipmentPort.objects.bulk_create([
        ContainerEquipmentPort(
            equipment=equipment,
            port_type=port_type,
            number=start + offset,
            port_number=offset,
            label=f"{label} {offset}",
        )
        for offset in range(1, count + 1)
    ])
    return JsonResponse({"equipment": _container_equipment_payload(equipment)}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def container_port_links(request, element_id):
    container = get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type__in=[NetworkElement.ElementType.RACK, NetworkElement.ElementType.TOWER],
    )
    if not can_edit_company(request.user, container.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    source = None
    if request.data.get("source_port_id"):
        source = get_object_or_404(
            ContainerEquipmentPort.objects.select_related("equipment"),
            pk=request.data.get("source_port_id"),
            equipment__container=container,
        )
    destination = get_object_or_404(
        ContainerEquipmentPort.objects.select_related("equipment"),
        pk=request.data.get("destination_port_id"),
        equipment__container=container,
    )
    cable = None
    cable_fiber = None
    if request.data.get("cable_fiber_id"):
        cable_fiber = get_object_or_404(
            FiberStrand.objects.select_related("cable", "color"),
            pk=request.data.get("cable_fiber_id"),
        )
        if not FiberCable.objects.filter(
            Q(origin=container) | Q(destination=container),
            pk=cable_fiber.cable_id,
            company=container.company,
        ).exists():
            return JsonResponse({"detail": "Fibra não pertence a um cabo deste rack/torre."}, status=400)
        if ContainerPortLink.objects.filter(container=container, cable_fiber=cable_fiber).exists():
            return JsonResponse({"detail": "Esta fibra já está ligada neste Rack/Torre."}, status=409)
        cable = cable_fiber.cable
    elif request.data.get("cable_id"):
        cable = get_object_or_404(
            FiberCable.objects.filter(Q(origin=container) | Q(destination=container)),
            pk=request.data.get("cable_id"),
            company=container.company,
        )
    if source is None and cable is None:
        return JsonResponse(
            {"detail": "Selecione a porta de origem ou o cabo para a fusão."}, status=400
        )
    if source is not None and (source.pk == destination.pk or source.equipment_id == destination.equipment_id):
        return JsonResponse({"detail": "Escolha portas de equipamentos diferentes."}, status=400)
    if source is None:
        # Fusão: só conflita com outra fusão já existente na mesma porta do
        # DIO. O cordão da frente (se houver) é uma ligação independente.
        in_use_query = Q(destination_port=destination, cable_fiber__isnull=False)
        role_label = "traseira (fusão)"
    else:
        # Cordão: só conflita com outro cordão já existente na mesma porta de
        # destino, além dos conflitos usuais nas duas pontas do cabo/cordão.
        in_use_query = (
            Q(destination_port=destination, source_port__isnull=False)
            | Q(source_port=source) | Q(destination_port=source) | Q(source_port=destination)
        )
        role_label = "frontal (cordão)"
    conflict = ContainerPortLink.objects.filter(in_use_query).select_related(
        "source_port__equipment", "destination_port__equipment", "cable"
    ).first()
    if conflict:
        # MAP_V07517_DIO_CONFLICT_MESSAGE: mensagem antes era genérica
        # ("Uma das portas já está em uso"), sem dizer QUAL porta bateu nem
        # com qual ligação — difícil de diagnosticar sem acesso ao banco.
        # Agora nomeia o lado que a requisição tentou usar (frontal/
        # traseira) e a ligação existente que conflitou.
        existing = (
            f"{conflict.source_port.equipment.name} · {conflict.source_port.label}"
            if conflict.source_port_id
            else f"cabo {conflict.cable.name if conflict.cable else '?'}"
        ) + f" → {conflict.destination_port.equipment.name} · {conflict.destination_port.label}"
        return JsonResponse(
            {"detail": f"Porta {role_label} já está em uso por: {existing}."},
            status=409,
        )
    link_type = str(request.data.get("link_type", "fiber"))
    link_notes = ""
    if source is None:
        # MAP v0.75.12 R4: a fibra de qualquer cabo alimentador/distribuição
        # continua terminando exclusivamente no conector TRASEIRO do DIO.
        # DROP também pode terminar diretamente em PTO ou na PON de ONU/ONT.
        # O termination_method permanece explícito para preservar o contrato
        # da API e classificar corretamente cada forma de terminação.
        destination_equipment = destination.equipment
        destination_subtype = str(
            (destination_equipment.metadata or {}).get("equipment_subtype", "")
        ).lower()
        is_dio_target = (
            destination_equipment.equipment_type == ContainerEquipment.EquipmentType.DIO
            and destination.port_type == ContainerEquipmentPort.PortType.DIO
        )
        is_pto_target = (
            destination_equipment.equipment_type == ContainerEquipment.EquipmentType.PTO
            and destination.port_type in {
                ContainerEquipmentPort.PortType.DIO,
                ContainerEquipmentPort.PortType.SC_APC,
                ContainerEquipmentPort.PortType.SC_UPC,
                ContainerEquipmentPort.PortType.LC,
            }
        )
        is_onu_pon_target = (
            destination.port_type == ContainerEquipmentPort.PortType.PON
            and (
                destination_equipment.equipment_type == ContainerEquipment.EquipmentType.ONU
                or destination_subtype in {"onu", "ont"}
            )
        )
        termination_method = str(
            request.data.get("termination_method") or ""
        ).strip().lower()

        if cable.cable_type == FiberCable.CableType.DROP:
            if not (is_dio_target or is_pto_target or is_onu_pon_target):
                return JsonResponse(
                    {"detail": "DROP só pode terminar no fundo do DIO, em PTO ou porta PON de ONU/ONT."},
                    status=400,
                )

            if is_dio_target:
                allowed_methods = {"", "fusion", "dio_rear"}
                normalized_method = "dio_rear"
            elif is_pto_target:
                # O frontend atual envia direct_connector tanto para PTO quanto
                # para ONU/ONT. No backend, PTO é normalizado para o método pto.
                allowed_methods = {"", "pto", "direct_connector"}
                normalized_method = "pto"
            else:
                allowed_methods = {"", "direct_connector"}
                normalized_method = "direct_connector"

            if termination_method not in allowed_methods:
                return JsonResponse(
                    {"detail": "Método de terminação incompatível com o destino selecionado."},
                    status=400,
                )
            termination_method = normalized_method

            connector_type = str(
                request.data.get("connector_type")
                or destination_equipment.connector_type
                or (destination_equipment.metadata or {}).get("pon_connector")
                or "SC/APC"
            ).strip().upper().replace("_", "/")
            if connector_type not in {"SC/APC", "SC/UPC", "LC/APC", "LC/UPC"}:
                connector_type = "SC/APC"

            method_labels = {
                "dio_rear": "DROP fundido no fundo do DIO",
                "pto": "DROP terminado em PTO",
                "direct_connector": "DROP com conector direto na ONU/ONT",
            }
            link_notes = f"{method_labels[termination_method]} · {connector_type}"
        else:
            if not is_dio_target:
                return JsonResponse(
                    {"detail": "Cabo alimentador/distribuição só pode ser fundido no fundo de uma porta DIO."},
                    status=400,
                )
            if termination_method not in {"", "fusion", "dio_rear"}:
                return JsonResponse(
                    {"detail": "Cabo alimentador/distribuição deve usar fusão traseira no DIO."},
                    status=400,
                )
            termination_method = "fusion"
            link_notes = "Fusão traseira no DIO"
        link_type = ContainerPortLink.LinkType.FIBER
    else:
        optical_ports = {
            ContainerEquipmentPort.PortType.DIO,
            ContainerEquipmentPort.PortType.PON,
            ContainerEquipmentPort.PortType.SFP_1G,
            ContainerEquipmentPort.PortType.SFP_PLUS_10G,
            ContainerEquipmentPort.PortType.SFP28_25G,
            ContainerEquipmentPort.PortType.QSFP_PLUS_40G,
            ContainerEquipmentPort.PortType.QSFP28_100G,
            ContainerEquipmentPort.PortType.SC_APC,
            ContainerEquipmentPort.PortType.SC_UPC,
            ContainerEquipmentPort.PortType.LC,
        }
        copper_ports = {
            ContainerEquipmentPort.PortType.RJ45_100M,
            ContainerEquipmentPort.PortType.RJ45_1G,
            ContainerEquipmentPort.PortType.RJ45_2G5,
        }
        if source.port_type in optical_ports and destination.port_type in optical_ports:
            link_type = ContainerPortLink.LinkType.FIBER
        elif source.port_type in copper_ports and destination.port_type in copper_ports:
            link_type = ContainerPortLink.LinkType.COPPER
        elif (
            source.port_type == ContainerEquipmentPort.PortType.WIRELESS
            and destination.port_type == ContainerEquipmentPort.PortType.WIRELESS
        ):
            link_type = ContainerPortLink.LinkType.WIRELESS
        else:
            return JsonResponse(
                {"detail": "Portas incompatíveis. Ligue óptica com óptica, RJ45 com RJ45 ou wireless com wireless."},
                status=400,
            )
    default_loss = 0.1 if source is None else 0.5
    if request.data.get("loss_db"):
        try:
            loss_db = Decimal(str(request.data["loss_db"]).replace(",", "."))
        except (InvalidOperation, ValueError):
            return JsonResponse({"detail": "Perda óptica inválida."}, status=400)
    else:
        loss_db = default_loss
    link = ContainerPortLink.objects.create(
        container=container,
        source_port=source,
        destination_port=destination,
        cable=cable,
        cable_fiber=cable_fiber,
        link_type=link_type,
        notes=link_notes,
        loss_db=loss_db,
    )
    return JsonResponse({"link": {"id": link.id}}, status=201)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def container_port_link_detail(request, element_id, link_id):
    link = get_object_or_404(
        ContainerPortLink.objects.select_related("container", "source_port__equipment", "destination_port__equipment"),
        pk=link_id,
        container_id=element_id,
    )
    if not can_edit_company(request.user, link.container.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    if request.method == "DELETE":
        link.delete()
        return HttpResponse(status=204)
    if request.data.get("loss_db") is not None:
        try:
            link.loss_db = Decimal(str(request.data["loss_db"]))
        except (InvalidOperation, ValueError):
            return JsonResponse({"detail": "Perda óptica inválida."}, status=400)
        link.save(update_fields=["loss_db", "updated_at"])
    return JsonResponse({"link": {"id": link.id, "loss_db": float(link.loss_db)}})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_network_element(request):
    """
    Cria equipamento da rede.

    POST /api/map/elements/create/
    """

    serializer = NetworkElementSerializer(
        data=request.data
    )

    if serializer.is_valid():
        project = serializer.validated_data.get("project")
        company = serializer.validated_data.get("company")
        company_id = project.company_id if project else getattr(company, "id", None)
        if not can_edit_company(request.user, company_id):
            return JsonResponse(
                {"success": False, "error": "Seu acesso não permite editar esta empresa."},
                status=403,
            )

        # Serializa criações do mesmo projeto e torna o envio idempotente para
        # o mesmo tipo/nome/coordenada. Evita que duplo clique ou dupla
        # submissão gere dois ícones sobrepostos no mapa.
        with transaction.atomic():
            NetworkProject.objects.select_for_update().get(pk=project.pk)
            latitude = serializer.validated_data.get("latitude")
            longitude = serializer.validated_data.get("longitude")
            duplicate = None
            if latitude is not None and longitude is not None:
                duplicate = NetworkElement.objects.filter(
                    project=project,
                    element_type=serializer.validated_data.get("element_type"),
                    name__iexact=str(serializer.validated_data.get("name") or "").strip(),
                    point=Point(float(longitude), float(latitude), srid=4326),
                ).order_by("id").first()
            if duplicate is not None:
                return JsonResponse(
                    {
                        "success": True,
                        "id": duplicate.id,
                        "nome": duplicate.name,
                        "duplicate": True,
                    },
                    status=200,
                )
            element = serializer.save()

        return JsonResponse(
            {
                "success": True,
                "id": element.id,
                "nome": element.name,
                "duplicate": False,
            },
            status=201,
        )


    return JsonResponse(
        {
            "success": False,
            "errors": serializer.errors,
        },
        status=400,
    )



@api_view(["GET", "PATCH", "PUT", "DELETE"])
@permission_classes([IsAuthenticatedOrReadOnly])
def network_element_detail(request, element_id):
    """
    Consulta, atualiza ou exclui um elemento do mapa.

    GET/PATCH/PUT/DELETE /api/map/elements/<id>/
    """
    element = get_object_or_404(
        NetworkElement,
        pk=element_id,
    )
    if not can_view_company(request.user, element.company_id):
        return JsonResponse({"success": False, "error": "Item não disponível."}, status=403)

    if request.method == "GET":
        return JsonResponse(
            {
                "success": True,
                "element": element_detail_payload(element),
            },
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    if not can_edit_company(request.user, element.company_id):
        return JsonResponse({"success": False, "error": "Seu acesso é somente VIEW."}, status=403)

    if request.method == "DELETE":
        connected_cables = FiberCable.objects.filter(
            Q(origin=element) |
            Q(destination=element)
        )

        connected_count = connected_cables.count()

        if connected_count:
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        f"Este ponto está conectado a "
                        f"{connected_count} cabo(s). "
                        "Remova ou altere os cabos antes "
                        "de excluir o ponto."
                    ),
                },
                status=409,
                json_dumps_params={
                    "ensure_ascii": False,
                },
            )

        element_name = element.name
        element.delete()

        return JsonResponse(
            {
                "success": True,
                "deleted": {
                    "id": element_id,
                    "name": element_name,
                },
            },
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    serializer = NetworkElementSerializer(
        element,
        data=request.data,
        partial=(request.method == "PATCH"),
    )

    if not serializer.is_valid():
        return JsonResponse(
            {
                "success": False,
                "errors": serializer.errors,
            },
            status=400,
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    element = serializer.save()

    return JsonResponse(
        {
            "success": True,
            "element": element_detail_payload(element),
        },
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_network_element_position(request, element_id):
    """
    Atualiza somente a posição geográfica do elemento.

    PATCH /api/map/elements/<id>/position/
    """
    element = get_object_or_404(
        NetworkElement,
        pk=element_id,
    )
    if not can_edit_company(request.user, element.company_id):
        return JsonResponse({"success": False, "error": "Seu acesso é somente VIEW."}, status=403)

    try:
        latitude = float(
            request.data.get("latitude")
        )
        longitude = float(
            request.data.get("longitude")
        )
    except (TypeError, ValueError):
        return JsonResponse(
            {
                "success": False,
                "error": (
                    "Latitude e longitude são obrigatórias."
                ),
            },
            status=400,
        )

    if not -90 <= latitude <= 90:
        return JsonResponse(
            {
                "success": False,
                "error": "Latitude inválida.",
            },
            status=400,
        )

    if not -180 <= longitude <= 180:
        return JsonResponse(
            {
                "success": False,
                "error": "Longitude inválida.",
            },
            status=400,
        )

    element.point = Point(
        longitude,
        latitude,
        srid=4326,
    )

    element.save(
        update_fields=["point"]
    )

    connected_cables = FiberCable.objects.filter(
        Q(origin=element) | Q(destination=element)
    )
    for cable in connected_cables:
        lines = [list(line.coords) for line in cable.geometry]
        if not lines:
            continue
        if cable.origin_id == element.id:
            lines[0][0] = (longitude, latitude)
        if cable.destination_id == element.id:
            lines[-1][-1] = (longitude, latitude)
        cable.geometry = MultiLineString(
            *[LineString(line, srid=4326) for line in lines],
            srid=4326,
        )
        cable.save(update_fields=["geometry", "updated_at"])

    return JsonResponse(
        {
            "success": True,
            "element": {
                "id": element.id,
                "latitude": latitude,
                "longitude": longitude,
            },
        },
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def cable_models(request):
    """
    Lista os modelos de cabo disponíveis.

    GET /api/map/cable-models/
    """
    queryset = (
        CableModel.objects
        .select_related("company", "color_standard")
        .order_by("fiber_count", "name")
    )

    models = []

    for cable_model in queryset:
        models.append(
            {
                "id": cable_model.id,
                "name": cable_model.name,
                "manufacturer": cable_model.manufacturer,
                "model": cable_model.model,
                "construction": cable_model.construction,
                "fiber_count": cable_model.fiber_count,
                "tube_count": cable_model.tube_count,
                "fibers_per_tube": cable_model.fibers_per_tube,
                "company": (
                    {
                        "id": cable_model.company_id,
                        "name": str(cable_model.company),
                    }
                    if cable_model.company_id
                    else None
                ),
                "color_standard": (
                    {
                        "id": cable_model.color_standard_id,
                        "name": str(cable_model.color_standard),
                    }
                    if cable_model.color_standard_id
                    else None
                ),
            }
        )

    return JsonResponse(
        {
            "success": True,
            "count": len(models),
            "models": models,
        },
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_fiber_cable(request):
    """
    Cria um cabo de fibra a partir de coordenadas desenhadas no mapa.

    POST /api/map/cables/create/
    """
    data = request.data

    name = str(data.get("name", "")).strip()
    code = str(data.get("code", "")).strip()
    description = str(data.get("description", "")).strip()
    cable_type = str(data.get("cable_type", "")).strip()
    status_value = str(data.get("status", "no_data")).strip()
    coordinates = data.get("coordinates")
    try:
        project = NetworkProject.objects.get(
            pk=int(data.get("project_id")),
            enabled=True,
        )
    except (TypeError, ValueError, NetworkProject.DoesNotExist):
        return JsonResponse(
            {
                "success": False,
                "error": "Selecione um projeto válido antes de criar o cabo.",
            },
            status=400,
        )

    if not name:
        return JsonResponse(
            {
                "success": False,
                "error": "O nome do cabo é obrigatório.",
            },
            status=400,
        )

    valid_cable_types = {
        value
        for value, _label in FiberCable.CableType.choices
    }

    if cable_type not in valid_cable_types:
        return JsonResponse(
            {
                "success": False,
                "error": "Tipo de cabo inválido.",
                "valid_cable_types": sorted(valid_cable_types),
            },
            status=400,
        )

    cable_model = None
    cable_model_id = data.get("cable_model_id")
    if cable_model_id not in (None, ""):
        try:
            cable_model = CableModel.objects.get(pk=int(cable_model_id))
        except (TypeError, ValueError, CableModel.DoesNotExist):
            return JsonResponse(
                {"success": False, "error": "Modelo de cabo inválido."},
                status=400,
            )

    try:
        fiber_count = int(data.get("fiber_count", 12))
    except (TypeError, ValueError):
        fiber_count = 12
    if not 1 <= fiber_count <= 4096:
        return JsonResponse(
            {"success": False, "error": "Quantidade de fibras inválida."},
            status=400,
        )

    effective_fiber_count = cable_model.fiber_count if cable_model else fiber_count
    if cable_type == FiberCable.CableType.DROP and effective_fiber_count not in {1, 2}:
        return JsonResponse(
            {"success": False, "error": "Cabo DROP deve possuir somente 1 ou 2 fibras."},
            status=400,
        )

    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return JsonResponse(
            {
                "success": False,
                "error": (
                    "A geometria deve possuir pelo menos "
                    "duas coordenadas."
                ),
            },
            status=400,
        )

    normalized_coordinates = []

    try:
        for coordinate in coordinates:
            if (
                not isinstance(coordinate, (list, tuple))
                or len(coordinate) != 2
            ):
                raise ValueError

            longitude = float(coordinate[0])
            latitude = float(coordinate[1])

            if not -180 <= longitude <= 180:
                raise ValueError

            if not -90 <= latitude <= 90:
                raise ValueError

            normalized_coordinates.append(
                (longitude, latitude)
            )

    except (TypeError, ValueError):
        return JsonResponse(
            {
                "success": False,
                "error": (
                    "Coordenadas inválidas. Utilize pares "
                    "[longitude, latitude]."
                ),
            },
            status=400,
        )

    origin = None
    destination = None

    origin_id = data.get("origin_id")
    destination_id = data.get("destination_id")

    if origin_id not in (None, ""):
        try:
            origin = NetworkElement.objects.get(
                pk=int(origin_id),
                project=project,
            )
        except (TypeError, ValueError, NetworkElement.DoesNotExist):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Equipamento de origem inválido.",
                },
                status=400,
            )

    if destination_id not in (None, ""):
        try:
            destination = NetworkElement.objects.get(
                pk=int(destination_id),
                project=project,
            )
        except (TypeError, ValueError, NetworkElement.DoesNotExist):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Equipamento de destino inválido.",
                },
                status=400,
            )

    if origin is not None and origin.point:
        normalized_coordinates[0] = (
            origin.point.x,
            origin.point.y,
        )
    if destination is not None and destination.point:
        normalized_coordinates[-1] = (
            destination.point.x,
            destination.point.y,
        )

    company = project.company or (
        cable_model.company if cable_model else None
    )

    if company is None and origin is not None:
        company = origin.company

    if company is None and destination is not None:
        company = destination.company

    line = LineString(
        normalized_coordinates,
        srid=4326,
    )

    geometry = MultiLineString(
        line,
        srid=4326,
    )

    cable = FiberCable.objects.create(
        project=project,
        company=company,
        name=name,
        code=code,
        description=description,
        cable_type=cable_type,
        cable_model=cable_model,
        geometry=geometry,
        fiber_count=(
            cable_model.fiber_count if cable_model else fiber_count
        ),
        used_fibers=0,
        origin=origin,
        destination=destination,
        status=status_value or "no_data",
    )

    generate_structure = data.get(
        "generate_fibers",
        True,
    )

    structure = None
    structure_error = None

    existing_tube_count = cable.tubes.count()
    existing_fiber_count = cable.fibers.count()

    if generate_structure and cable_model:
        if existing_tube_count or existing_fiber_count:
            structure = {
                "tube_count": existing_tube_count,
                "fiber_count": existing_fiber_count,
                "already_existed": True,
            }
        else:
            try:
                result = generate_cable_fibers(cable)

                structure = {
                    **result,
                    "already_existed": False,
                }
            except FiberStructureError as exc:
                structure_error = str(exc)

    return JsonResponse(
        {
            "success": True,
            "cable": {
                "id": cable.id,
                "name": cable.name,
                "code": cable.code,
                "cable_type": cable.cable_type,
                "fiber_count": cable.fiber_count,
                "origin_id": cable.origin_id,
                "destination_id": cable.destination_id,
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": cable.geometry.coords,
                },
            },
            "fiber_structure": structure,
            "fiber_structure_error": structure_error,
        },
        status=201,
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


def cable_detail_payload(cable):
    return {
        "id": cable.id,
        "project_id": cable.project_id,
        "name": cable.name,
        "code": cable.code,
        "description": cable.description,
        "cable_type": cable.cable_type,
        "fiber_count": cable.fiber_count,
        "used_fibers": cable.used_fibers,
        "status": cable.status,
        "origin_id": cable.origin_id,
        "destination_id": cable.destination_id,
        "cable_model_id": cable.cable_model_id,
        "geometry": (
            {
                "type": "MultiLineString",
                "coordinates": cable.geometry.coords,
            }
            if cable.geometry
            else None
        ),
        "reserves": [
            {
                "id": reserve.id,
                "latitude": reserve.point.y,
                "longitude": reserve.point.x,
                "length_m": float(reserve.length_m),
                "label": reserve.label,
            }
            for reserve in cable.reserves.all()
        ],
    }


@api_view(["GET", "POST", "PATCH", "DELETE"])
@permission_classes([IsAuthenticatedOrReadOnly])
def cable_reserves(request, cable_id, reserve_id=None):
    cable = get_object_or_404(FiberCable, pk=cable_id)
    reserve = None
    if reserve_id is not None:
        reserve = get_object_or_404(CableReserve, pk=reserve_id, cable=cable)
    if request.method == "GET":
        return JsonResponse({"success": True, "reserves": cable_detail_payload(cable)["reserves"]})
    if request.method == "DELETE":
        reserve.delete()
        return JsonResponse({"success": True})
    try:
        latitude = float(request.data.get("latitude"))
        longitude = float(request.data.get("longitude"))
        length_m = float(request.data.get("length_m"))
        if not (0 < length_m <= 100000):
            raise ValueError
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "error": "Coordenadas e metragem da reserva são obrigatórias."}, status=400)
    values = {
        "point": Point(longitude, latitude, srid=4326),
        "length_m": length_m,
        "label": str(request.data.get("label", "")).strip(),
        "notes": str(request.data.get("notes", "")).strip(),
    }
    if reserve is None:
        reserve = CableReserve.objects.create(cable=cable, **values)
    else:
        for field, value in values.items():
            setattr(reserve, field, value)
        reserve.save()
    return JsonResponse({"success": True, "reserve": {"id": reserve.id}}, status=201 if request.method == "POST" else 200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def reserve_to_element(request, cable_id, reserve_id):
    cable = get_object_or_404(FiberCable, pk=cable_id)
    reserve = get_object_or_404(CableReserve, pk=reserve_id, cable=cable)
    element_type = str(request.data.get("element_type", "")).strip()
    element_subtype = str(request.data.get("element_subtype", "")).strip().lower()
    if element_type not in {
        NetworkElement.ElementType.CTO,
        NetworkElement.ElementType.SPLICE_BOX,
    }:
        return JsonResponse({"success": False, "error": "Escolha CTO ou CEO."}, status=400)
    name = str(request.data.get("name", "")).strip()
    code = str(request.data.get("code", "")).strip()
    if not name:
        return JsonResponse({"success": False, "error": "Informe o nome do elemento."}, status=400)

    raw = list(cable.geometry[0].coords)
    if len(raw) < 2:
        return JsonResponse({"success": False, "error": "Traçado do cabo inválido."}, status=400)
    target = (reserve.point.x, reserve.point.y)
    segment = min(
        range(len(raw) - 1),
        key=lambda index: (
            ((raw[index][0] + raw[index + 1][0]) / 2 - target[0]) ** 2
            + ((raw[index][1] + raw[index + 1][1]) / 2 - target[1]) ** 2
        ),
    )
    first = raw[: segment + 1] + [target]
    second = [target] + raw[segment + 1 :]
    element_data = {
        "project": cable.project,
        "company": cable.company,
        "name": name,
        "code": code,
        "element_type": element_type,
        "point": reserve.point,
        "status": "no_data",
        "enabled": True,
    }
    if element_subtype:
        element_data["metadata"] = {"import_subtype": element_subtype}
    if element_type == NetworkElement.ElementType.CTO:
        element = CTO.objects.create(capacity=8, splitter_ratio="1:8", **element_data)
        from apps.network_map.models import CTOSplitter
        from apps.network_map.serializers import sync_splitter_ports
        splitter = CTOSplitter.objects.create(cto=element, ratio="1:8", output_ports=8)
        sync_splitter_ports(splitter, 8)
    else:
        element = NetworkElement.objects.create(**element_data)
        from apps.network_map.serializers import sync_splice_box
        sync_splice_box(element, 1, 0, "1:8")

    old_destination = cable.destination
    cable.destination = element
    cable.geometry = MultiLineString(LineString(first, srid=4326), srid=4326)
    cable.save(update_fields=["destination", "geometry", "updated_at"])
    new_cable = FiberCable.objects.create(
        project=cable.project,
        company=cable.company,
        name=f"{cable.name} · trecho 2",
        code=f"{cable.code}-2" if cable.code else "",
        description=cable.description,
        cable_type=cable.cable_type,
        cable_model=cable.cable_model,
        geometry=MultiLineString(LineString(second, srid=4326), srid=4326),
        fiber_count=cable.fiber_count,
        origin=element,
        destination=old_destination,
        status=cable.status,
    )
    if new_cable.cable_model:
        try:
            generate_cable_fibers(new_cable)
        except FiberStructureError:
            pass
    reserve.delete()
    return JsonResponse({
        "success": True,
        "element": {"id": element.id, "name": element.name, "type": element_type},
        "cables": [cable.id, new_cable.id],
    }, status=201)


@api_view(["POST", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def splice_box_trays(request, element_id, tray_id=None):
    # MAP_V07534_OPTICAL_TRAYS: CRUD isolado das bandejas de CTO/CEO/CDO.
    element = get_object_or_404(
        scope_company_queryset(NetworkElement.objects, request.user),
        pk=element_id,
        element_type__in=[
            NetworkElement.ElementType.SPLICE_BOX,
            NetworkElement.ElementType.CTO,
        ],
    )
    if not can_edit_company(request.user, element.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)

    tray = None
    if tray_id is not None:
        tray = get_object_or_404(SpliceTray, pk=tray_id, splice_box=element)

    if request.method in {"PATCH", "DELETE"} and tray is None:
        return JsonResponse({"detail": "Informe a bandeja que será alterada."}, status=400)
    if request.method == "POST" and tray is not None:
        return JsonResponse({"detail": "Use PATCH para alterar uma bandeja existente."}, status=405)

    if request.method == "DELETE":
        if tray.splitters.exists() or tray.splices.exists():
            return JsonResponse(
                {"detail": "Remova as fusões e os splitters da bandeja antes de excluí-la."},
                status=409,
            )
        tray.delete()
        return JsonResponse({"success": True})

    try:
        capacity = int(request.data.get("capacity", tray.capacity if tray else 12))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Capacidade inválida."}, status=400)
    if not 1 <= capacity <= 288:
        return JsonResponse({"detail": "A capacidade deve ficar entre 1 e 288."}, status=400)

    if tray is None:
        try:
            number = int(request.data.get("number") or 0)
        except (TypeError, ValueError):
            number = 0
        if number <= 0:
            number = (element.splice_trays.order_by("-number").values_list("number", flat=True).first() or 0) + 1
        if element.splice_trays.filter(number=number).exists():
            return JsonResponse({"detail": "Já existe uma bandeja com este número."}, status=409)
        tray = SpliceTray.objects.create(
            splice_box=element,
            number=number,
            name=str(request.data.get("name") or f"Bandeja {number}").strip()[:100],
            capacity=capacity,
        )
        status_code = 201
    else:
        if "number" in request.data:
            try:
                number = int(request.data.get("number"))
            except (TypeError, ValueError):
                return JsonResponse({"detail": "Número da bandeja inválido."}, status=400)
            if number <= 0 or element.splice_trays.exclude(pk=tray.pk).filter(number=number).exists():
                return JsonResponse({"detail": "Número de bandeja inválido ou duplicado."}, status=409)
            tray.number = number
        if "name" in request.data:
            tray.name = str(request.data.get("name") or "").strip()[:100]
        tray.capacity = capacity
        tray.save(update_fields=["number", "name", "capacity", "updated_at"])
        status_code = 200

    return JsonResponse({
        "success": True,
        "tray": {
            "id": tray.id,
            "number": tray.number,
            "name": tray.name,
            "capacity": tray.capacity,
        },
    }, status=status_code)


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticatedOrReadOnly])
def splice_box_fibers(request, element_id, splice_id=None):
    element = get_object_or_404(
        NetworkElement,
        pk=element_id,
        element_type__in=[
            NetworkElement.ElementType.SPLICE_BOX,
            NetworkElement.ElementType.CTO,
        ],
    )
    # MAP_V07534_OPTICAL_WRITE_PERMISSION_FIBERS: leitura pode seguir a
    # política pública existente; toda mutação exige acesso de edição à empresa.
    if request.method != "GET" and not can_edit_company(request.user, element.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    if (
        request.method == "GET"
        and element.element_type == NetworkElement.ElementType.CTO
        and can_edit_company(request.user, element.company_id)
    ):
        cto = CTO.objects.filter(pk=element.pk).first()
        if cto and not cto.splice_trays.filter(splitters__isnull=False).exists():
            ensure_cto_default_splitters(cto, cto.capacity)

    if request.method == "DELETE":
        splice = get_object_or_404(FiberSplice, pk=splice_id, splice_box=element)
        fibers = [splice.input_fiber, splice.output_fiber]
        splice.delete()
        for fiber in fibers:
            still_connected = (
                FiberSplice.objects.filter(
                    Q(input_fiber=fiber) | Q(output_fiber=fiber)
                ).exists()
                or SpliceTraySplitter.objects.filter(input_fiber=fiber).exists()
                or SpliceTraySplitterPort.objects.filter(output_fiber=fiber).exists()
            )
            fiber.status = (
                FiberStrand.Status.USED
                if still_connected
                else FiberStrand.Status.FREE
            )
            fiber.save(update_fields=["status", "updated_at"])
        return JsonResponse({"success": True})
    # CEO/CDO mostra todos os cabos que realmente passam perto da caixa,
    # inclusive lotes antigos que ainda não possuíam CableElementPassage.
    # CTO continua restrita às relações explícitas para não “roubar” cabo
    # tronco de uma caixa de emenda próxima.
    nearby_cable_ids = []
    if element.element_type == NetworkElement.ElementType.SPLICE_BOX and element.point:
        try:
            element_metric = element.point.transform(3857, clone=True)
            for candidate in FiberCable.objects.filter(
                project=element.project,
                company=element.company,
                geometry__isnull=False,
            ).only("id", "geometry"):
                if candidate.geometry.transform(3857, clone=True).distance(element_metric) <= OPTICAL_BOX_CAPTURE_RADIUS_M:
                    nearby_cable_ids.append(candidate.id)
        except Exception:
            nearby_cable_ids = []
    connected = FiberCable.objects.filter(
        Q(origin=element)
        | Q(destination=element)
        | Q(element_passages__element=element)
        | Q(pk__in=nearby_cable_ids)
    ).distinct().prefetch_related("fibers__color", "element_passages")
    passage_by_cable = {
        passage.cable_id: passage.action
        for passage in element.cable_passages.select_related("cable").all()
    }

    def fiber_is_connected(fiber, exclude_splitter=None, exclude_port=None):
        if FiberSplice.objects.filter(
            splice_box=element,
        ).filter(
            Q(input_fiber=fiber) | Q(output_fiber=fiber)
        ).exists():
            return True
        splitter_links = SpliceTraySplitter.objects.filter(
            tray__splice_box=element,
            input_fiber=fiber,
        )
        if exclude_splitter is not None:
            splitter_links = splitter_links.exclude(pk=exclude_splitter)
        if splitter_links.exists():
            return True
        port_links = SpliceTraySplitterPort.objects.filter(
            splitter__tray__splice_box=element,
            output_fiber=fiber,
        )
        if exclude_port is not None:
            port_links = port_links.exclude(pk=exclude_port)
        return port_links.exists()
    if request.method == "GET":
        return JsonResponse({
            "success": True,
            "cables": [
                {
                    "id": cable.id,
                    "name": cable.name,
                    "origin_id": cable.origin_id,
                    "destination_id": cable.destination_id,
                    "relation_action": passage_by_cable.get(cable.id) or (
                        "connect" if cable.origin_id == element.id or cable.destination_id == element.id else "pass"
                    ),
                    "requires_cut": (
                        cable.origin_id != element.id and cable.destination_id != element.id
                    ),
                    "fibers": [
                        {
                            "id": fiber.id,
                            "number": fiber.number,
                            "color_name": fiber.color.name,
                            "color_hex": fiber.color.hex_color,
                            "status": fiber.status,
                            "budget": _fiber_budget_payload(fiber, element),
                        }
                        for fiber in cable.fibers.all()
                    ],
                }
                for cable in connected
            ],
            "splices": [
                {
                    "id": splice.id,
                    "tray_id": splice.tray_id,
                    "input_fiber_id": splice.input_fiber_id,
                    "output_fiber_id": splice.output_fiber_id,
                    "input": {
                        "cable": splice.input_fiber.cable.name,
                        "number": splice.input_fiber.number,
                        "color_name": splice.input_fiber.color.name,
                        "color_hex": splice.input_fiber.color.hex_color,
                    },
                    "output": {
                        "cable": splice.output_fiber.cable.name,
                        "number": splice.output_fiber.number,
                        "color_name": splice.output_fiber.color.name,
                        "color_hex": splice.output_fiber.color.hex_color,
                    },
                    "loss_db": FUSION_LOSS_DB,
                    "budget": _fiber_budget_payload(splice.output_fiber),
                }
                for splice in element.fiber_splices.select_related(
                    "input_fiber__cable",
                    "input_fiber__color",
                    "output_fiber__cable",
                    "output_fiber__color",
                ).all()
            ],
            "splitter_links": [
                {
                    "splitter_id": splitter.id,
                    "tray_id": splitter.tray_id,
                    "input_fiber_id": splitter.input_fiber_id,
                    "input_splitter_port_id": splitter.input_splitter_port_id,
                    "input_budget": (
                        _fiber_budget_payload(splitter.input_fiber, element)
                        if splitter.input_fiber_id
                        else _splitter_port_budget_payload(splitter.input_splitter_port)
                        if splitter.input_splitter_port_id
                        else None
                    ),
                    "ports": [
                        {
                            "id": port.id,
                            "number": port.number,
                            "output_fiber_id": port.output_fiber_id,
                            "loss_db": _splitter_output_loss_db(splitter.ratio, port.number),
                            "budget": _fiber_budget_payload(port.output_fiber) if port.output_fiber_id else None,
                        }
                        for port in splitter.ports.all()
                    ],
                }
                for splitter in SpliceTraySplitter.objects.filter(
                    tray__splice_box=element
                ).prefetch_related("ports")
            ],
        })
    connection_type = str(request.data.get("connection_type", "splice"))
    # Cabos apenas em passagem aparecem para revisão, mas suas fibras
    # só podem ser usadas depois do corte explícito na caixa.
    connected_ids = set(
        FiberCable.objects.filter(Q(origin=element) | Q(destination=element))
        .values_list("id", flat=True)
    )
    if connection_type == "splitter_input":
        splitter = get_object_or_404(
            SpliceTraySplitter,
            pk=request.data.get("splitter_id"),
            tray__splice_box=element,
        )
        fiber = get_object_or_404(FiberStrand, pk=request.data.get("fiber_id"))
        if fiber.cable_id not in connected_ids:
            return JsonResponse({"success": False, "error": "Fibra não pertence a um cabo conectado."}, status=400)
        if fiber_is_connected(fiber, exclude_splitter=splitter.id):
            return JsonResponse({"success": False, "error": "Esta fibra já está utilizada em outra ligação."}, status=409)
        splitter.input_fiber = fiber
        splitter.save(update_fields=["input_fiber", "updated_at"])
        fiber.status = FiberStrand.Status.USED
        fiber.save(update_fields=["status", "updated_at"])
        return JsonResponse({"success": True})
    if connection_type == "splitter_output":
        port = get_object_or_404(
            SpliceTraySplitterPort,
            pk=request.data.get("port_id"),
            splitter__tray__splice_box=element,
        )
        fiber = get_object_or_404(FiberStrand, pk=request.data.get("fiber_id"))
        if fiber.cable_id not in connected_ids:
            return JsonResponse({"success": False, "error": "Fibra não pertence a um cabo conectado."}, status=400)
        if fiber_is_connected(fiber, exclude_port=port.id):
            return JsonResponse({"success": False, "error": "Esta fibra já está utilizada em outra ligação."}, status=409)
        port.output_fiber = fiber
        port.save(update_fields=["output_fiber", "updated_at"])
        fiber.status = FiberStrand.Status.USED
        fiber.save(update_fields=["status", "updated_at"])
        return JsonResponse({"success": True})
    if connection_type == "splitter_cascade":
        splitter = get_object_or_404(
            SpliceTraySplitter,
            pk=request.data.get("splitter_id"),
            tray__splice_box=element,
        )
        source_port = get_object_or_404(
            SpliceTraySplitterPort,
            pk=request.data.get("source_port_id"),
            splitter__tray__splice_box=element,
        )
        if splitter.input_fiber_id or splitter.input_splitter_port_id:
            return JsonResponse({"success": False, "error": "Este splitter já tem uma entrada ligada."}, status=409)
        if source_port.output_fiber_id or SpliceTraySplitter.objects.filter(input_splitter_port=source_port).exists():
            return JsonResponse({"success": False, "error": "Esta saída já está utilizada em outra ligação."}, status=409)
        if source_port.splitter_id == splitter.id:
            return JsonResponse({"success": False, "error": "Um splitter não pode alimentar a si mesmo."}, status=400)
        visited = {splitter.id}
        current = source_port.splitter
        for _ in range(50):
            if current.id in visited:
                return JsonResponse({"success": False, "error": "Essa ligação criaria um laço entre splitters."}, status=400)
            visited.add(current.id)
            if not current.input_splitter_port_id:
                break
            current = current.input_splitter_port.splitter
        splitter.input_splitter_port = source_port
        splitter.save(update_fields=["input_splitter_port", "updated_at"])
        return JsonResponse({"success": True})
    if connection_type == "clear_splitter_input":
        splitter = get_object_or_404(
            SpliceTraySplitter,
            pk=request.data.get("splitter_id"),
            tray__splice_box=element,
        )
        splitter.input_fiber = None
        splitter.input_splitter_port = None
        splitter.save(update_fields=["input_fiber", "input_splitter_port", "updated_at"])
        return JsonResponse({"success": True})
    if connection_type == "clear_splitter_output":
        port = get_object_or_404(
            SpliceTraySplitterPort,
            pk=request.data.get("port_id"),
            splitter__tray__splice_box=element,
        )
        port.output_fiber = None
        port.save(update_fields=["output_fiber", "updated_at"])
        SpliceTraySplitter.objects.filter(input_splitter_port=port).update(input_splitter_port=None)
        return JsonResponse({"success": True})
    try:
        tray = element.splice_trays.get(pk=int(request.data.get("tray_id")))
        input_fiber = FiberStrand.objects.get(pk=int(request.data.get("input_fiber_id")))
        output_fiber = FiberStrand.objects.get(pk=int(request.data.get("output_fiber_id")))
    except (TypeError, ValueError, SpliceTray.DoesNotExist, FiberStrand.DoesNotExist):
        return JsonResponse({"success": False, "error": "Bandeja ou fibras inválidas."}, status=400)
    if input_fiber.cable_id not in connected_ids or output_fiber.cable_id not in connected_ids:
        return JsonResponse({"success": False, "error": "As fibras precisam pertencer a cabos conectados à caixa."}, status=400)
    if input_fiber.cable_id == output_fiber.cable_id:
        return JsonResponse({"success": False, "error": "A fusão deve ligar fibras de cabos diferentes."}, status=400)
    if fiber_is_connected(input_fiber) or fiber_is_connected(output_fiber):
        return JsonResponse({"success": False, "error": "Uma das fibras já está utilizada em outra ligação."}, status=409)
    try:
        splice = FiberSplice.objects.create(
            tray=tray,
            splice_box=element,
            input_fiber=input_fiber,
            output_fiber=output_fiber,
            loss_db=Decimal("0.10"),
        )
    except (ValueError, Exception) as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    for fiber in (input_fiber, output_fiber):
        fiber.status = FiberStrand.Status.USED
        fiber.save(update_fields=["status", "updated_at"])
    return JsonResponse({"success": True, "splice": {"id": splice.id}}, status=201)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticatedOrReadOnly])
def splice_box_layout(request, element_id):
    element = get_object_or_404(
        NetworkElement,
        pk=element_id,
        element_type__in=[
            NetworkElement.ElementType.SPLICE_BOX,
            NetworkElement.ElementType.CTO,
            NetworkElement.ElementType.RACK,
            NetworkElement.ElementType.TOWER,
        ],
    )
    # MAP_V07534_OPTICAL_WRITE_PERMISSION_LAYOUT: layout é dado editável da
    # empresa; impedir PATCH por usuário somente leitura.
    if request.method != "GET" and not can_edit_company(request.user, element.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    if request.method == "GET":
        return JsonResponse({
            "success": True,
            "layout": element.metadata.get("unifilar_layout", {}),
        })
    layout = request.data.get("layout")
    if not isinstance(layout, dict):
        return JsonResponse({"success": False, "error": "Layout inválido."}, status=400)
    metadata = dict(element.metadata or {})
    metadata["unifilar_layout"] = layout
    element.metadata = metadata
    element.save(update_fields=["metadata", "updated_at"])
    return JsonResponse({"success": True, "layout": layout})


@api_view(["POST", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def splice_box_splitters(request, element_id, splitter_id=None):
    element = get_object_or_404(
        NetworkElement,
        pk=element_id,
        element_type__in=[
            NetworkElement.ElementType.SPLICE_BOX,
            NetworkElement.ElementType.CTO,
        ],
    )
    # MAP_V07534_OPTICAL_WRITE_PERMISSION_SPLITTERS: POST/PATCH/DELETE são
    # operações destrutivas e precisam respeitar a empresa do elemento.
    if not can_edit_company(request.user, element.company_id):
        return JsonResponse({"detail": "Sem permissão para editar esta empresa."}, status=403)
    splitter = None
    if splitter_id is not None:
        splitter = get_object_or_404(
            SpliceTraySplitter,
            pk=splitter_id,
            tray__splice_box=element,
        )
    if request.method == "DELETE":
        splitter.delete()
        return JsonResponse({"success": True})
    ratio = str(request.data.get("ratio", "1:8"))
    if ratio in CTOSplitter.BALANCED_RATIOS:
        output_ports = int(ratio.split(":")[1])
    elif ratio in CTOSplitter.UNBALANCED_RATIOS:
        output_ports = 2
    else:
        return JsonResponse({"success": False, "error": "Configuração do splitter inválida."}, status=400)
    if splitter is None:
        tray = get_object_or_404(
            SpliceTray,
            pk=request.data.get("tray_id"),
            splice_box=element,
        )
        position = (tray.splitters.order_by("-position").values_list("position", flat=True).first() or 0) + 1
        splitter = SpliceTraySplitter.objects.create(
            tray=tray, position=position, ratio=ratio, output_ports=output_ports
        )
    else:
        splitter.ratio = ratio
        splitter.output_ports = output_ports
        splitter.save(update_fields=["ratio", "output_ports", "updated_at"])
    existing = set(splitter.ports.values_list("number", flat=True))
    SpliceTraySplitterPort.objects.bulk_create([
        SpliceTraySplitterPort(splitter=splitter, number=number)
        for number in range(1, output_ports + 1)
        if number not in existing
    ])
    splitter.ports.filter(number__gt=output_ports, output_fiber__isnull=True).delete()
    return JsonResponse({"success": True, "splitter_id": splitter.id}, status=201 if request.method == "POST" else 200)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def delete_fiber_cable(request, cable_id):
    """
    Exclui um cabo óptico.

    DELETE /api/map/cables/<id>/
    DELETE /api/map/cables/<id>/?force=1
    """
    cable = get_object_or_404(
        FiberCable,
        pk=cable_id,
    )

    if request.method == "GET":
        return JsonResponse(
            {"success": True, "cable": cable_detail_payload(cable)}
        )

    if request.method == "PATCH":
        data = request.data
        for field in ("name", "code", "description", "status"):
            if field in data:
                setattr(cable, field, str(data[field]).strip())

        if "cable_type" in data:
            cable_type = str(data["cable_type"]).strip()
            if cable_type not in dict(FiberCable.CableType.choices):
                return JsonResponse(
                    {"success": False, "error": "Tipo de cabo inválido."},
                    status=400,
                )
            cable.cable_type = cable_type

        if "fiber_count" in data:
            try:
                fiber_count = int(data["fiber_count"])
            except (TypeError, ValueError):
                fiber_count = 0
            if fiber_count < max(1, cable.used_fibers):
                return JsonResponse(
                    {
                        "success": False,
                        "error": "A capacidade não pode ser menor que as fibras usadas.",
                    },
                    status=400,
                )
            cable.fiber_count = fiber_count

        for field in ("origin_id", "destination_id"):
            if field not in data:
                continue
            value = data.get(field)
            element = None
            if value not in (None, ""):
                try:
                    element = NetworkElement.objects.get(
                        pk=int(value),
                        project=cable.project,
                    )
                except (TypeError, ValueError, NetworkElement.DoesNotExist):
                    return JsonResponse(
                        {
                            "success": False,
                            "error": "A conexão deve usar um elemento do mesmo projeto.",
                        },
                        status=400,
                    )
            setattr(cable, field, element.id if element else None)

        lines = [list(line.coords) for line in cable.geometry]
        if lines and cable.origin and cable.origin.point:
            lines[0][0] = (cable.origin.point.x, cable.origin.point.y)
        if lines and cable.destination and cable.destination.point:
            lines[-1][-1] = (
                cable.destination.point.x,
                cable.destination.point.y,
            )
        if lines:
            cable.geometry = MultiLineString(
                *[LineString(line, srid=4326) for line in lines],
                srid=4326,
            )
        cable.save()
        return JsonResponse(
            {"success": True, "cable": cable_detail_payload(cable)}
        )

    force_delete = str(
        request.query_params.get("force", "")
    ).strip().lower() in {
        "1",
        "true",
        "yes",
        "sim",
    }

    splice_objects = {}

    for fiber in cable.fibers.all():
        for relation_name in (
            "splice_inputs",
            "splice_outputs",
        ):
            for splice in getattr(fiber, relation_name).all():
                splice_key = (
                    splice._meta.label_lower,
                    splice.pk,
                )
                splice_objects[splice_key] = splice

    splice_count = len(splice_objects)

    if splice_count and not force_delete:
        return JsonResponse(
            {
                "success": False,
                "requires_force": True,
                "splice_count": splice_count,
                "error": (
                    f"Este cabo possui {splice_count} "
                    "fusão(ões). Confirme a exclusão "
                    "forçada para remover o cabo, "
                    "as fibras e as fusões vinculadas."
                ),
            },
            status=409,
            json_dumps_params={
                "ensure_ascii": False,
            },
        )

    deleted_splices = 0

    if force_delete:
        for splice in splice_objects.values():
            splice.delete()
            deleted_splices += 1

    cable_id_value = cable.id
    cable_name = cable.name

    cable.delete()

    return JsonResponse(
        {
            "success": True,
            "deleted": {
                "id": cable_id_value,
                "name": cable_name,
                "splices": deleted_splices,
            },
        },
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_cable_geometry(request, cable_id):
    """
    Atualiza a geometria de um cabo óptico.

    PUT/PATCH /api/map/cables/<id>/geometry/
    """
    cable = get_object_or_404(
        FiberCable,
        pk=cable_id,
    )

    coordinates = request.data.get("coordinates")

    if not isinstance(coordinates, list) or not coordinates:
        return JsonResponse(
            {
                "success": False,
                "error": "As coordenadas são obrigatórias.",
            },
            status=400,
        )

    # Aceita:
    # [
    #   [longitude, latitude],
    #   [longitude, latitude]
    # ]
    #
    # ou:
    #
    # [
    #   [
    #     [longitude, latitude],
    #     [longitude, latitude]
    #   ]
    # ]
    first_item = coordinates[0]

    is_single_line = (
        isinstance(first_item, (list, tuple))
        and len(first_item) >= 2
        and isinstance(first_item[0], (int, float))
        and isinstance(first_item[1], (int, float))
    )

    lines = (
        [coordinates]
        if is_single_line
        else coordinates
    )

    normalized_lines = []

    try:
        for line_coordinates in lines:
            if (
                not isinstance(line_coordinates, list)
                or len(line_coordinates) < 2
            ):
                raise ValueError(
                    "Cada trecho precisa ter pelo menos dois pontos."
                )

            normalized_line = []

            for point in line_coordinates:
                if (
                    not isinstance(point, (list, tuple))
                    or len(point) < 2
                ):
                    raise ValueError(
                        "Coordenada inválida."
                    )

                longitude = float(point[0])
                latitude = float(point[1])

                if not -180 <= longitude <= 180:
                    raise ValueError(
                        "Longitude fora do intervalo permitido."
                    )

                if not -90 <= latitude <= 90:
                    raise ValueError(
                        "Latitude fora do intervalo permitido."
                    )

                normalized_line.append(
                    (longitude, latitude)
                )

            normalized_lines.append(
                normalized_line
            )

    except (TypeError, ValueError) as exc:
        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=400,
        )

    geos_lines = [
        LineString(
            line_coordinates,
            srid=4326,
        )
        for line_coordinates in normalized_lines
    ]

    cable.geometry = MultiLineString(
        *geos_lines,
        srid=4326,
    )

    cable.save(
        update_fields=["geometry"]
    )

    return JsonResponse(
        {
            "success": True,
            "cable": {
                "id": cable.id,
                "name": cable.name,
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": cable.geometry.coords,
                },
            },
        },
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def cable_fibers(request, cable_id):
    """
    Lista tubos e fibras de um cabo.

    GET /api/map/cables/<id>/fibers/
    """
    cable = get_object_or_404(
        FiberCable.objects.select_related(
            "cable_model",
            "origin",
            "destination",
        ),
        pk=cable_id,
    )

    tubes = (
        cable.tubes
        .select_related("color")
        .prefetch_related("fibers__color")
        .order_by("number")
    )

    tube_data = []

    for tube in tubes:
        fibers = []

        for fiber in tube.fibers.all().order_by("position_in_tube"):
            fibers.append(
                {
                    "id": fiber.id,
                    "number": fiber.number,
                    "position_in_tube": fiber.position_in_tube,
                    "status": fiber.status,
                    "status_label": fiber.get_status_display(),
                    "usage": fiber.usage,
                    "notes": fiber.notes,
                    "color": {
                        "id": fiber.color_id,
                        "name": fiber.color.name,
                        "code": fiber.color.code,
                        "hex": fiber.color.hex_color,
                        "text": fiber.color.text_color,
                    },
                    "has_input_splice": fiber.splice_inputs.exists(),
                    "has_output_splice": fiber.splice_outputs.exists(),
                }
            )

        tube_data.append(
            {
                "id": tube.id,
                "number": tube.number,
                "identification": tube.identification,
                "color": (
                    {
                        "id": tube.color_id,
                        "name": tube.color.name,
                        "code": tube.color.code,
                        "hex": tube.color.hex_color,
                        "text": tube.color.text_color,
                    }
                    if tube.color
                    else None
                ),
                "fibers": fibers,
            }
        )

    return JsonResponse(
        {
            "success": True,
            "cable": {
                "id": cable.id,
                "name": cable.name,
                "code": cable.code,
                "fiber_count": cable.fiber_count,
                "used_fibers": cable.used_fibers,
                "model": (
                    cable.cable_model.model
                    if cable.cable_model
                    else None
                ),
                "origin": (
                    cable.origin.name
                    if cable.origin
                    else None
                ),
                "destination": (
                    cable.destination.name
                    if cable.destination
                    else None
                ),
            },
            "tubes": tube_data,
        },
        json_dumps_params={
            "ensure_ascii": False,
        },
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_fibers(request, cable_id):
    """
    Gera automaticamente tubos e fibras do cabo.

    POST /api/map/cables/<id>/generate-fibers/

    Body opcional:
        {
            "force": false
        }
    """
    cable = get_object_or_404(
        FiberCable,
        pk=cable_id,
    )

    force = request.data.get("force", False)

    if isinstance(force, str):
        force = force.strip().lower() in {
            "1",
            "true",
            "sim",
            "yes",
        }

    try:
        result = generate_cable_fibers(
            cable,
            force=bool(force),
        )
    except FiberStructureError as error:
        return JsonResponse(
            {
                "success": False,
                "error": str(error),
            },
            status=400,
        )

    return JsonResponse(
        {
            "success": True,
            "message": "Tubos e fibras gerados com sucesso.",
            "cable_id": result["cable"].id,
            "tube_count": result["tube_count"],
            "fiber_count": result["fiber_count"],
        },
        status=201,
    )
