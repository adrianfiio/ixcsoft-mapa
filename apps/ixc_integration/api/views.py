from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from apps.core.access import can_edit_company, scope_company_queryset

from apps.ixc_integration.models import IXCConfiguration, IXCSyncExecution
from apps.ixc_integration.customer_models import IXCCustomer, IXCLogin
from apps.ixc_integration.fiber_models import IXCFiberAssignment
from apps.ixc_integration.services.configuration import build_client
from apps.ixc_integration.tasks import synchronize_ixc_configuration
from .serializers import (
    IXCConfigurationSerializer,
    IXCSyncExecutionSerializer,
    IXCCustomerSerializer,
    IXCLoginSerializer,
    IXCFiberAssignmentSerializer,
)


class CompanyScopedAPIViewMixin:
    permission_classes = [IsAuthenticated]
    company_field = "company_id"

    def get_queryset(self):
        return scope_company_queryset(
            super().get_queryset(),
            self.request.user,
            self.company_field,
        )


class IXCConfigurationViewSet(CompanyScopedAPIViewMixin, viewsets.ModelViewSet):
    queryset = IXCConfiguration.objects.all()
    serializer_class = IXCConfigurationSerializer

    def perform_create(self, serializer):
        company = serializer.validated_data.get("company")
        if not company or not can_edit_company(self.request.user, company.id):
            raise PermissionDenied("Empresa não permitida.")
        serializer.save()

    def perform_update(self, serializer):
        if not can_edit_company(self.request.user, self.get_object().company_id):
            raise PermissionDenied("Seu acesso é somente VIEW.")
        serializer.save()

    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, pk=None):
        configuration = self.get_object()
        if not can_edit_company(request.user, configuration.company_id):
            raise PermissionDenied("Seu acesso é somente VIEW.")
        try:
            result = build_client(configuration).test_connection()
            return Response(result)
        except Exception as exc:
            return Response(
                {"ok": False, "error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"], url_path="synchronize")
    def synchronize(self, request, pk=None):
        configuration = self.get_object()
        if not can_edit_company(request.user, configuration.company_id):
            raise PermissionDenied("Seu acesso é somente VIEW.")
        task = synchronize_ixc_configuration.delay(configuration.pk)
        return Response(
            {"queued": True, "task_id": task.id},
            status=status.HTTP_202_ACCEPTED,
        )


class IXCSyncExecutionViewSet(CompanyScopedAPIViewMixin, viewsets.ReadOnlyModelViewSet):
    queryset = IXCSyncExecution.objects.select_related("configuration").all()
    serializer_class = IXCSyncExecutionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["configuration", "status"]
    ordering_fields = ["started_at", "finished_at"]
    company_field = "configuration__company_id"


class IXCCustomerViewSet(CompanyScopedAPIViewMixin, viewsets.ReadOnlyModelViewSet):
    queryset = IXCCustomer.objects.all()
    serializer_class = IXCCustomerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["active"]
    search_fields = ["name", "document", "ixc_customer_id"]


class IXCLoginViewSet(CompanyScopedAPIViewMixin, viewsets.ReadOnlyModelViewSet):
    queryset = IXCLogin.objects.select_related("customer", "cto", "onu").all()
    serializer_class = IXCLoginSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["online", "status", "cto"]
    search_fields = ["username", "ixc_login_id", "customer__name"]


class IXCFiberAssignmentViewSet(CompanyScopedAPIViewMixin, viewsets.ReadOnlyModelViewSet):
    queryset = IXCFiberAssignment.objects.select_related("login", "cto", "onu").all()
    serializer_class = IXCFiberAssignmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["ixc_project_id", "ixc_cto_id", "ixc_login_id", "cto", "onu"]
    search_fields = ["name", "mac_address", "pon_id", "city", "neighborhood"]
    ordering_fields = ["name", "last_synced_at", "rx_power"]
