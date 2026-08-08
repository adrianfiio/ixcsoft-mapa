from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.permissions import AllowAny

from apps.core.models import Company
from apps.core.access import (
    can_edit_company,
    can_view_company,
    editable_company_ids,
    scope_company_queryset,
)
from apps.network_map.models import (
    NetworkProject,
    NetworkRoute,
)


def project_payload(project, user=None):
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
        "can_edit": can_edit_company(user, project.company_id),
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticatedOrReadOnly])
def projects(request):
    if request.method == "GET":
        queryset = scope_company_queryset(
            NetworkProject.objects.filter(enabled=True),
            request.user,
        ).order_by("name")
        return JsonResponse(
            {
                "success": True,
                "projects": [project_payload(item, request.user) for item in queryset],
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
        if not can_edit_company(request.user, company.id):
            return JsonResponse(
                {"success": False, "error": "Você não pode editar esta empresa."},
                status=403,
            )
    elif not request.user.is_superuser:
        allowed = editable_company_ids(request.user)
        if len(allowed) != 1:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Selecione a empresa responsável pelo projeto.",
                },
                status=400,
            )
        company = get_object_or_404(Company, pk=allowed[0])

    duplicate_query = NetworkProject.objects.filter(code__iexact=code)
    duplicate_query = (
        duplicate_query.filter(company=company)
        if company
        else duplicate_query.filter(company__isnull=True)
    )
    if duplicate_query.exists():
        return JsonResponse(
            {"success": False, "error": "Já existe um projeto com esse código nesta empresa."},
            status=409,
        )

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
        {"success": True, "project": project_payload(project, request.user)},
        status=201,
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticatedOrReadOnly])
def project_detail(request, project_id):
    project = get_object_or_404(NetworkProject, pk=project_id)
    if not can_view_company(request.user, project.company_id):
        return JsonResponse(
            {"success": False, "error": "Projeto não disponível para este usuário."},
            status=403,
        )

    if request.method == "GET":
        return JsonResponse({"success": True, "project": project_payload(project, request.user)})

    if not can_edit_company(request.user, project.company_id):
        return JsonResponse(
            {"success": False, "error": "Seu acesso é somente VIEW."},
            status=403,
        )

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
    return JsonResponse({"success": True, "project": project_payload(project, request.user)})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticatedOrReadOnly])
def project_routes_geojson(request):
    if request.method == "POST":
        project_id = request.data.get("project_id")
        if not project_id:
            return JsonResponse(
                {"success": False, "error": "Informe project_id."},
                status=400,
            )
        project = get_object_or_404(
            scope_company_queryset(NetworkProject.objects.all(), request.user),
            pk=project_id,
        )
        if not can_edit_company(request.user, project.company_id):
            return JsonResponse(
                {"success": False, "error": "Sem permissão para editar esta empresa."},
                status=403,
            )
        name = str(request.data.get("name") or "").strip()
        if not name:
            return JsonResponse(
                {"success": False, "error": "Nome da rota é obrigatório."},
                status=400,
            )
        requested_code = str(request.data.get("code") or "").strip()
        route_slug = slugify(requested_code or name).upper() or "ROTA"
        prefix = slugify(project.code).upper()
        base_code = f"{prefix}-{route_slug}"[:80] if prefix else route_slug[:80]
        candidate = base_code
        suffix = 2
        while NetworkRoute.objects.filter(
            company=project.company,
            code__iexact=candidate,
        ).exists():
            tail = f"-{suffix}"
            candidate = f"{base_code[:80-len(tail)]}{tail}"
            suffix += 1
        route = NetworkRoute.objects.create(
            company=project.company,
            project=project,
            name=name,
            code=candidate,
        )
        return JsonResponse({
            "success": True,
            "route": {
                "id": route.id,
                "name": route.name,
                "code": route.code,
                "status": route.status,
                "project_id": route.project_id,
            },
        }, status=201)

    project_id = request.GET.get("project_id")
    queryset = NetworkRoute.objects.all()
    if project_id:
        queryset = queryset.filter(project_id=project_id)
    queryset = scope_company_queryset(queryset, request.user)

    features = []
    for route in queryset:
        features.append(
            {
                "type": "Feature",
                "id": route.id,
                "geometry": (
                    {
                        "type": "MultiLineString",
                        "coordinates": route.geometry.coords,
                    }
                    if route.geometry
                    else None
                ),
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
