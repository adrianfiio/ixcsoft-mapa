from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.ixc_integration.models import IXCConfiguration, IXCSyncExecution
from apps.ixc_integration.customer_models import IXCCustomer, IXCLogin
from apps.ixc_integration.services.configuration import build_client
from apps.ixc_integration.tasks import synchronize_ixc_configuration
from .serializers import (
    IXCConfigurationSerializer,
    IXCSyncExecutionSerializer,
    IXCCustomerSerializer,
    IXCLoginSerializer,
)


class IXCConfigurationViewSet(viewsets.ModelViewSet):
    queryset = IXCConfiguration.objects.all()
    serializer_class = IXCConfigurationSerializer

    @action(detail=True, methods=["post"], url_path="test-connection")
    def test_connection(self, request, pk=None):
        configuration = self.get_object()
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
        task = synchronize_ixc_configuration.delay(configuration.pk)
        return Response(
            {"queued": True, "task_id": task.id},
            status=status.HTTP_202_ACCEPTED,
        )


class IXCSyncExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IXCSyncExecution.objects.select_related("configuration").all()
    serializer_class = IXCSyncExecutionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["configuration", "status"]
    ordering_fields = ["started_at", "finished_at"]


class IXCCustomerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IXCCustomer.objects.all()
    serializer_class = IXCCustomerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["active"]
    search_fields = ["name", "document", "ixc_customer_id"]


class IXCLoginViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IXCLogin.objects.select_related("customer", "cto", "onu").all()
    serializer_class = IXCLoginSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["online", "status", "cto"]
    search_fields = ["username", "ixc_login_id", "customer__name"]
