from rest_framework import serializers

from apps.ixc_integration.models import IXCConfiguration, IXCSyncExecution
from apps.ixc_integration.customer_models import IXCCustomer, IXCLogin


class IXCConfigurationSerializer(serializers.ModelSerializer):
    api_token = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = IXCConfiguration
        exclude = ["api_token_encrypted"]

    def create(self, validated_data):
        token = validated_data.pop("api_token", "")
        instance = super().create(validated_data)
        if token:
            instance.api_token_encrypted = token
            instance.save(update_fields=["api_token_encrypted"])
        return instance

    def update(self, instance, validated_data):
        token = validated_data.pop("api_token", None)
        instance = super().update(instance, validated_data)
        if token is not None:
            instance.api_token_encrypted = token
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
