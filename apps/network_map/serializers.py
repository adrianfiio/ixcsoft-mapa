
from rest_framework import serializers
from .models import (
    CTO,
    CTOSplitter,
    CTOSplitterPort,
    NetworkElement,
    NetworkProject,
)


def sync_splitter_ports(splitter, output_ports):
    output_ports = max(1, min(int(output_ports), 128))
    splitter.output_ports = output_ports
    splitter.save(update_fields=["output_ports", "updated_at"])
    existing = set(splitter.ports.values_list("number", flat=True))
    CTOSplitterPort.objects.bulk_create(
        [
            CTOSplitterPort(splitter=splitter, number=number)
            for number in range(1, output_ports + 1)
            if number not in existing
        ]
    )
    splitter.ports.filter(
        number__gt=output_ports,
        status=CTOSplitterPort.Status.FREE,
    ).delete()


class NetworkElementMapSerializer(serializers.ModelSerializer):

    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = NetworkElement
        fields = [
            "id",
            "name",
            "code",
            "project",
            "element_type",
            "status",
            "enabled",
            "description",
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
    project = serializers.PrimaryKeyRelatedField(
        queryset=NetworkProject.objects.filter(enabled=True),
        required=True,
    )
    cto_capacity = serializers.IntegerField(
        write_only=True,
        required=False,
        min_value=1,
        max_value=128,
        default=8,
    )
    splitter_ratio = serializers.ChoiceField(
        write_only=True,
        required=False,
        choices=CTOSplitter.Ratio.choices,
        default=CTOSplitter.Ratio.ONE_TO_8,
    )
    splitter_ports = serializers.IntegerField(
        write_only=True,
        required=False,
        min_value=1,
        max_value=128,
        default=8,
    )

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
            "project",
            "element_type",
            "status",
            "enabled",
            "description",
            "latitude",
            "longitude",
            "cto_capacity",
            "splitter_ratio",
            "splitter_ports",
        ]


    def create(self, validated_data):
        cto_capacity = validated_data.pop("cto_capacity", 8)
        splitter_ratio = validated_data.pop(
            "splitter_ratio",
            CTOSplitter.Ratio.ONE_TO_8,
        )
        splitter_ports = validated_data.pop("splitter_ports", 8)

        latitude = validated_data.pop(
            "latitude",
            None
        )

        longitude = validated_data.pop(
            "longitude",
            None
        )


        project = validated_data["project"]
        validated_data["company"] = project.company

        if latitude is not None and longitude is not None:
            validated_data["point"] = Point(
                longitude,
                latitude,
                srid=4326
            )


        if validated_data.get("element_type") == NetworkElement.ElementType.CTO:
            cto = CTO.objects.create(
                capacity=cto_capacity,
                splitter_ratio=splitter_ratio,
                **validated_data,
            )
            splitter = CTOSplitter.objects.create(
                cto=cto,
                name="Splitter 1",
                ratio=splitter_ratio,
                output_ports=splitter_ports,
            )
            sync_splitter_ports(splitter, splitter_ports)
            return cto

        return NetworkElement.objects.create(**validated_data)


    def update(self, instance, validated_data):
        cto_capacity = validated_data.pop("cto_capacity", None)
        splitter_ratio = validated_data.pop("splitter_ratio", None)
        splitter_ports = validated_data.pop("splitter_ports", None)

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

        if isinstance(instance, CTO):
            cto = instance
        else:
            try:
                cto = instance.cto
            except CTO.DoesNotExist:
                cto = None

        if cto is not None:
            if cto_capacity is not None:
                cto.capacity = cto_capacity
            if splitter_ratio is not None:
                cto.splitter_ratio = splitter_ratio
            cto.save()
            splitter, _created = CTOSplitter.objects.get_or_create(
                cto=cto,
                position=1,
                defaults={
                    "name": "Splitter 1",
                    "ratio": splitter_ratio or CTOSplitter.Ratio.ONE_TO_8,
                    "output_ports": splitter_ports or cto.capacity,
                },
            )
            if splitter_ratio is not None:
                splitter.ratio = splitter_ratio
                splitter.save(update_fields=["ratio", "updated_at"])
            if splitter_ports is not None:
                sync_splitter_ports(splitter, splitter_ports)

        return instance
