from rest_framework import serializers
from apps.olt_integration.models import OLT, PONPort, ONU
from apps.network_map.models import CTO, NetworkRoute, NetworkElement, FiberCable
from apps.alerts.models import AlertEvent


class OLTSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLT
        exclude = [
            "snmp_community_encrypted",
            "snmp_auth_key_encrypted",
            "snmp_priv_key_encrypted",
        ]


class PONPortSerializer(serializers.ModelSerializer):
    olt_name = serializers.CharField(source="olt.name", read_only=True)

    class Meta:
        model = PONPort
        fields = "__all__"


class ONUSerializer(serializers.ModelSerializer):
    pon = serializers.CharField(source="pon_port.__str__", read_only=True)

    class Meta:
        model = ONU
        fields = "__all__"


class CTOSerializer(serializers.ModelSerializer):
    longitude = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()

    class Meta:
        model = CTO
        fields = "__all__"

    def get_longitude(self, obj):
        return obj.point.x if obj.point else None

    def get_latitude(self, obj):
        return obj.point.y if obj.point else None


class NetworkRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkRoute
        fields = "__all__"


class NetworkElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetworkElement
        fields = "__all__"


class FiberCableSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiberCable
        fields = "__all__"


class AlertEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertEvent
        fields = "__all__"
        read_only_fields = ["fingerprint", "opened_at", "closed_at"]
