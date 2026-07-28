from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.olt_integration.models import OLT, PONPort, ONU
from apps.network_map.models import CTO, NetworkRoute, NetworkElement, FiberCable
from apps.alerts.models import AlertEvent
from .serializers import (
    OLTSerializer,
    PONPortSerializer,
    ONUSerializer,
    CTOSerializer,
    NetworkRouteSerializer,
    NetworkElementSerializer,
    FiberCableSerializer,
    AlertEventSerializer,
)


class BaseViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]


class OLTViewSet(BaseViewSet):
    queryset = OLT.objects.all()
    serializer_class = OLTSerializer
    filterset_fields = ["vendor", "enabled", "status"]
    search_fields = ["name", "hostname", "management_ip", "model", "serial_number"]
    ordering_fields = ["name", "last_seen_at", "last_poll_at"]


class PONPortViewSet(BaseViewSet):
    queryset = PONPort.objects.select_related("olt").all()
    serializer_class = PONPortSerializer
    filterset_fields = ["olt", "status", "slot", "port"]
    search_fields = ["interface_name", "description", "olt__name"]


class ONUViewSet(BaseViewSet):
    queryset = ONU.objects.select_related("pon_port", "pon_port__olt").all()
    serializer_class = ONUSerializer
    filterset_fields = ["pon_port", "operational_status", "los", "registration_status"]
    search_fields = ["serial_number", "mac_address", "model"]
    ordering_fields = ["onu_id", "rx_power", "last_collected_at"]


class CTOViewSet(BaseViewSet):
    queryset = CTO.objects.select_related("route").all()
    serializer_class = CTOSerializer
    filterset_fields = ["status", "route", "enabled"]
    search_fields = ["name", "code", "ixc_box_id"]
    ordering_fields = ["name", "status", "last_evaluated_at"]


class NetworkRouteViewSet(BaseViewSet):
    queryset = NetworkRoute.objects.all()
    serializer_class = NetworkRouteSerializer
    filterset_fields = ["status", "enabled"]
    search_fields = ["name", "code"]


class NetworkElementViewSet(BaseViewSet):
    queryset = NetworkElement.objects.all()
    serializer_class = NetworkElementSerializer
    filterset_fields = ["element_type", "status", "enabled"]
    search_fields = ["name", "code"]


class FiberCableViewSet(BaseViewSet):
    queryset = FiberCable.objects.select_related("origin", "destination", "route").all()
    serializer_class = FiberCableSerializer
    filterset_fields = ["cable_type", "status", "route"]
    search_fields = ["name", "code"]


class AlertEventViewSet(BaseViewSet):
    queryset = AlertEvent.objects.select_related("rule", "olt", "pon_port", "onu", "cto", "route").all()
    serializer_class = AlertEventSerializer
    filterset_fields = ["state", "severity", "scope", "cto", "route", "olt"]
    search_fields = ["title", "message", "fingerprint"]
    ordering_fields = ["opened_at", "severity", "state"]
