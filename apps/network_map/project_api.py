import io
import uuid
import zipfile
from xml.etree import ElementTree

from django.contrib.gis.geos import LineString, MultiLineString, Point
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.permissions import AllowAny

from apps.core.models import Company
from apps.network_map.models import (
    CTO,
    NetworkElement,
    NetworkProject,
    NetworkRoute,
)


def project_payload(project):
    return {
        "id": project.id,
        "name": project.name,
        "code": project.code,
        "description": project.description,
        "status": project.status,
        "status_label": project.get_status_display(),
        "color": project.color,
        "enabled": project.enabled,
        "company_id": project.company_id,
        "element_count": project.elements.count(),
        "cable_count": project.cables.count(),
        "route_count": project.routes.count(),
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticatedOrReadOnly])
def projects(request):
    if request.method == "GET":
        queryset = NetworkProject.objects.filter(enabled=True).order_by("name")
        return JsonResponse(
            {
                "success": True,
                "projects": [project_payload(item) for item in queryset],
            }
        )

    name = str(request.data.get("name", "")).strip()
    code = str(request.data.get("code", "")).strip()
    description = str(request.data.get("description", "")).strip()
    status_value = str(request.data.get("status", "planning")).strip()
    color = str(request.data.get("color", "#2dd4bf")).strip()

    if not name or not code:
        return JsonResponse(
            {"success": False, "error": "Nome e código são obrigatórios."},
            status=400,
        )
    if NetworkProject.objects.filter(code__iexact=code).exists():
        return JsonResponse(
            {"success": False, "error": "Já existe um projeto com esse código."},
            status=409,
        )
    if status_value not in dict(NetworkProject.Status.choices):
        return JsonResponse(
            {"success": False, "error": "Status de projeto inválido."},
            status=400,
        )
    if len(color) != 7 or not color.startswith("#"):
        color = "#2dd4bf"

    company = None
    company_id = request.data.get("company_id")
    if company_id:
        company = get_object_or_404(Company, pk=company_id)

    project = NetworkProject.objects.create(
        company=company,
        name=name,
        code=code,
        description=description,
        status=status_value,
        color=color,
        created_by=request.user,
    )
    return JsonResponse(
        {"success": True, "project": project_payload(project)},
        status=201,
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticatedOrReadOnly])
def project_detail(request, project_id):
    project = get_object_or_404(NetworkProject, pk=project_id)

    if request.method == "GET":
        return JsonResponse({"success": True, "project": project_payload(project)})

    if request.method == "DELETE":
        if project.elements.exists() or project.cables.exists() or project.routes.exists():
            return JsonResponse(
                {
                    "success": False,
                    "error": "O projeto possui estrutura. Arquive-o em vez de excluir.",
                },
                status=409,
            )
        project.delete()
        return JsonResponse({"success": True})

    for field in ("name", "description", "color"):
        if field in request.data:
            setattr(project, field, str(request.data[field]).strip())
    if "status" in request.data:
        status_value = str(request.data["status"]).strip()
        if status_value not in dict(NetworkProject.Status.choices):
            return JsonResponse(
                {"success": False, "error": "Status inválido."},
                status=400,
            )
        project.status = status_value
    project.save()
    return JsonResponse({"success": True, "project": project_payload(project)})


def read_kml(upload):
    content = upload.read()
    if len(content) > 20 * 1024 * 1024:
        raise ValueError("O arquivo excede o limite de 20 MB.")

    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = [
                item for item in archive.infolist()
                if item.filename.lower().endswith(".kml")
                and item.file_size <= 50 * 1024 * 1024
            ]
            if not members:
                raise ValueError("O KMZ não contém um arquivo KML válido.")
            content = archive.read(members[0])

    try:
        return ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise ValueError("KML inválido ou corrompido.") from exc


def coordinate_pairs(text):
    pairs = []
    for raw_value in (text or "").replace("\n", " ").split():
        values = raw_value.split(",")
        if len(values) < 2:
            continue
        longitude = float(values[0])
        latitude = float(values[1])
        if -180 <= longitude <= 180 and -90 <= latitude <= 90:
            pairs.append((longitude, latitude))
    return pairs


def imported_element_type(name):
    normalized = name.casefold()
    if "cto" in normalized:
        return NetworkElement.ElementType.CTO
    if "ceo" in normalized or "emenda" in normalized:
        return NetworkElement.ElementType.SPLICE_BOX
    if "poste" in normalized:
        return NetworkElement.ElementType.POLE
    return NetworkElement.ElementType.OTHER


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_project_file(request, project_id):
    project = get_object_or_404(NetworkProject, pk=project_id, enabled=True)
    upload = request.FILES.get("file")
    if upload is None:
        return JsonResponse(
            {"success": False, "error": "Selecione um arquivo KML ou KMZ."},
            status=400,
        )

    try:
        root = read_kml(upload)
        point_count = 0
        route_count = 0

        with transaction.atomic():
            for placemark in root.findall(".//{*}Placemark"):
                name_node = placemark.find("./{*}name")
                name = (
                    name_node.text.strip()
                    if name_node is not None and name_node.text
                    else f"Importado {point_count + route_count + 1}"
                )

                point_node = placemark.find(".//{*}Point/{*}coordinates")
                if point_node is not None:
                    coordinates = coordinate_pairs(point_node.text)
                    if coordinates:
                        longitude, latitude = coordinates[0]
                        element_type = imported_element_type(name)
                        element_model = (
                            CTO
                            if element_type == NetworkElement.ElementType.CTO
                            else NetworkElement
                        )
                        element_model.objects.create(
                            project=project,
                            company=project.company,
                            name=name,
                            code=f"IMP-{uuid.uuid4().hex[:8].upper()}",
                            element_type=element_type,
                            point=Point(longitude, latitude, srid=4326),
                        )
                        point_count += 1

                line_node = placemark.find(".//{*}LineString/{*}coordinates")
                if line_node is not None:
                    coordinates = coordinate_pairs(line_node.text)
                    if len(coordinates) >= 2:
                        line = LineString(coordinates, srid=4326)
                        NetworkRoute.objects.create(
                            project=project,
                            company=project.company,
                            name=name,
                            code=f"KML-{uuid.uuid4().hex[:8].upper()}",
                            geometry=MultiLineString(line, srid=4326),
                        )
                        route_count += 1

        return JsonResponse(
            {
                "success": True,
                "imported": {"elements": point_count, "routes": route_count},
            }
        )
    except (ValueError, TypeError) as exc:
        return JsonResponse(
            {"success": False, "error": str(exc)},
            status=400,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def project_routes_geojson(request):
    project_id = request.GET.get("project_id")
    queryset = NetworkRoute.objects.filter(geometry__isnull=False)
    if project_id:
        queryset = queryset.filter(project_id=project_id)

    features = []
    for route in queryset:
        features.append(
            {
                "type": "Feature",
                "id": route.id,
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": route.geometry.coords,
                },
                "properties": {
                    "id": route.id,
                    "nome": route.name,
                    "codigo": route.code,
                    "status": route.status,
                    "project_id": route.project_id,
                    "imported": True,
                },
            }
        )
    return JsonResponse(
        {"type": "FeatureCollection", "count": len(features), "features": features}
    )
