from rest_framework import serializers

from apps.ixc_integration.models import IXCConfiguration, IXCSyncExecution
from apps.ixc_integration.customer_models import IXCCustomer, IXCLogin
from apps.ixc_integration.fiber_models import IXCFiberAssignment
from apps.ixc_integration.services.secrets import encrypt_secret


class IXCConfigurationSerializer(serializers.ModelSerializer):
    api_token = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = IXCConfiguration
        exclude = ["api_token_encrypted"]

    def create(self, validated_data):
        token = validated_data.pop("api_token", "")
        instance = super().create(validated_data)
        if token:
            instance.api_token_encrypted = encrypt_secret(token)
            instance.save(update_fields=["api_token_encrypted"])
        return instance

    def update(self, instance, validated_data):
        token = validated_data.pop("api_token", None)
        instance = super().update(instance, validated_data)
        if token:
            instance.api_token_encrypted = encrypt_secret(token)
            instance.save(update_fields=["api_token_encrypted"])
        return instance


class IXCSyncExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = IXCSyncExecution
        fields = "__all__"


class IXCCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = IXCCustomer
        fields = "__all__"


class IXCLoginSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = IXCLogin
        fields = "__all__"


class IXCFiberAssignmentSerializer(serializers.ModelSerializer):
    login_username = serializers.CharField(source="login.username", read_only=True)
    cto_name = serializers.CharField(source="cto.name", read_only=True)

    class Meta:
        model = IXCFiberAssignment
        fields = "__all__"
