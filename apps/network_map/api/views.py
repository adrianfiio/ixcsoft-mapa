from decimal import Decimal

from django.contrib.gis.geos import LineString, MultiLineString, Point
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from apps.access.models import AccessPoint
from apps.network_map.models import (
    CableModel,
    CTO,
    FiberCable,
    FiberStrand,
    NetworkElement,
    NetworkProject,
)
from apps.network_map.serializers import NetworkElementSerializer
from apps.network_map.services import (
    FiberStructureError,
    generate_cable_fibers,
)


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
    queryset = (
        AccessPoint.objects.filter(
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
        .iterator(chunk_size=1000)
    )

    for access_point in queryset:
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
    project_id = request.GET.get("project_id")
    if project_id:
        queryset = queryset.filter(project_id=project_id)

    for element in queryset:

        if not element.point:
            continue

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
    project_id = request.GET.get("project_id")
    if project_id:
        queryset = queryset.filter(project_id=project_id)

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
                    "origem": (
                        cable.origin.name
                        if cable.origin
                        else None
                    ),
                    "destino": (
                        cable.destination.name
                        if cable.destination
                        else None
                    ),
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
        "latitude": element.point.y if element.point else None,
        "longitude": element.point.x if element.point else None,
        "cto": None,
    }
    try:
        cto = element.cto
    except CTO.DoesNotExist:
        cto = None
    if cto is not None:
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
    return payload


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

        element = serializer.save()

        return JsonResponse(
            {
                "success": True,
                "id": element.id,
                "nome": element.name,
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
        "geometry": {
            "type": "MultiLineString",
            "coordinates": cable.geometry.coords,
        },
    }


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
            "splice_input",
            "splice_output",
        ):
            try:
                splice = getattr(
                    fiber,
                    relation_name,
                )
            except ObjectDoesNotExist:
                continue

            if splice is None:
                continue

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
                    "has_input_splice": hasattr(
                        fiber,
                        "splice_input",
                    ),
                    "has_output_splice": hasattr(
                        fiber,
                        "splice_output",
                    ),
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
