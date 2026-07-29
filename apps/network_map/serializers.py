
from rest_framework import serializers
from .models import NetworkElement


class NetworkElementMapSerializer(serializers.ModelSerializer):

    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = NetworkElement
        fields = [
            "id",
            "name",
            "code",
            "element_type",
            "status",
            "enabled",
            "latitude",
            "longitude",
        ]

    def get_latitude(self, obj):
        if obj.point:
            return obj.point.y
        return None

    def get_longitude(self, obj):
        if obj.point:
            return obj.point.x
        return None


from django.contrib.gis.geos import Point


class NetworkElementSerializer(serializers.ModelSerializer):

    latitude = serializers.FloatField(
        write_only=True,
        required=False,
        allow_null=True,
    )

    longitude = serializers.FloatField(
        write_only=True,
        required=False,
        allow_null=True,
    )


    class Meta:
        model = NetworkElement
        fields = [
            "id",
            "name",
            "code",
            "element_type",
            "status",
            "enabled",
            "latitude",
            "longitude",
        ]


    def create(self, validated_data):

        latitude = validated_data.pop(
            "latitude",
            None
        )

        longitude = validated_data.pop(
            "longitude",
            None
        )


        if latitude is not None and longitude is not None:
            validated_data["point"] = Point(
                longitude,
                latitude,
                srid=4326
            )


        return NetworkElement.objects.create(
            **validated_data
        )


    def update(self, instance, validated_data):

        latitude = validated_data.pop(
            "latitude",
            None
        )

        longitude = validated_data.pop(
            "longitude",
            None
        )


        if latitude is not None and longitude is not None:
            instance.point = Point(
                longitude,
                latitude,
                srid=4326
            )


        for attr, value in validated_data.items():
            setattr(
                instance,
                attr,
                value
            )


        instance.save()

        return instance
