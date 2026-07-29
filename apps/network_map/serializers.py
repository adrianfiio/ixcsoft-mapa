
from rest_framework import serializers
from .models import (
    CTO,
    CTOSplitter,
    CTOSplitterPort,
    FiberCable,
    FiberStrand,
    NetworkElement,
    NetworkProject,
    SpliceTray,
    SpliceTraySplitter,
    SpliceTraySplitterPort,
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


def sync_splice_box(element, tray_count, splitters_per_tray, ratio):
    tray_count = max(1, min(int(tray_count), 24))
    splitters_per_tray = max(0, min(int(splitters_per_tray), 8))
    for number in range(1, tray_count + 1):
        tray, _ = SpliceTray.objects.get_or_create(
            splice_box=element,
            number=number,
            defaults={"name": f"Bandeja {number}", "capacity": 12},
        )
        for position in range(1, splitters_per_tray + 1):
            SpliceTraySplitter.objects.update_or_create(
                tray=tray,
                position=position,
                defaults={
                    "ratio": ratio,
                    "output_ports": int(ratio.split(":")[1]),
                },
            )
            splitter = tray.splitters.get(position=position)
            existing_ports = set(splitter.ports.values_list("number", flat=True))
            SpliceTraySplitterPort.objects.bulk_create([
                SpliceTraySplitterPort(splitter=splitter, number=number)
                for number in range(1, splitter.output_ports + 1)
                if number not in existing_ports
            ])
            splitter.ports.filter(number__gt=splitter.output_ports).delete()
        tray.splitters.filter(position__gt=splitters_per_tray).delete()
    element.splice_trays.filter(number__gt=tray_count).delete()


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
    splitter_input_cable_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True
    )
    splitter_input_fiber_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True
    )
    ceo_tray_count = serializers.IntegerField(write_only=True, required=False, min_value=1, max_value=24, default=1)
    ceo_splitters_per_tray = serializers.IntegerField(write_only=True, required=False, min_value=0, max_value=8, default=0)
    ceo_splitter_ratio = serializers.ChoiceField(write_only=True, required=False, choices=CTOSplitter.Ratio.choices, default=CTOSplitter.Ratio.ONE_TO_8)

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
            "splitter_input_cable_id",
            "splitter_input_fiber_id",
            "ceo_tray_count",
            "ceo_splitters_per_tray",
            "ceo_splitter_ratio",
        ]


    def create(self, validated_data):
        cto_capacity = validated_data.pop("cto_capacity", 8)
        splitter_ratio = validated_data.pop(
            "splitter_ratio",
            CTOSplitter.Ratio.ONE_TO_8,
        )
        splitter_ports = validated_data.pop("splitter_ports", 8)
        validated_data.pop("splitter_input_cable_id", None)
        validated_data.pop("splitter_input_fiber_id", None)
        ceo_tray_count = validated_data.pop("ceo_tray_count", 1)
        ceo_splitters = validated_data.pop("ceo_splitters_per_tray", 0)
        ceo_ratio = validated_data.pop("ceo_splitter_ratio", CTOSplitter.Ratio.ONE_TO_8)

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

        element = NetworkElement.objects.create(**validated_data)
        if element.element_type == NetworkElement.ElementType.SPLICE_BOX:
            sync_splice_box(element, ceo_tray_count, ceo_splitters, ceo_ratio)
        return element


    def update(self, instance, validated_data):
        cto_capacity = validated_data.pop("cto_capacity", None)
        splitter_ratio = validated_data.pop("splitter_ratio", None)
        splitter_ports = validated_data.pop("splitter_ports", None)
        input_cable_id = validated_data.pop("splitter_input_cable_id", None)
        input_fiber_id = validated_data.pop("splitter_input_fiber_id", None)
        ceo_tray_count = validated_data.pop("ceo_tray_count", None)
        ceo_splitters = validated_data.pop("ceo_splitters_per_tray", None)
        ceo_ratio = validated_data.pop("ceo_splitter_ratio", None)

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
            if input_cable_id is not None:
                previous_fiber = splitter.input_fiber
                try:
                    input_cable = FiberCable.objects.get(
                        pk=input_cable_id,
                        project=cto.project,
                    )
                except FiberCable.DoesNotExist:
                    raise serializers.ValidationError({
                        "splitter_input_cable_id": "Cabo não pertence ao projeto."
                    })
                if not (
                    input_cable.origin_id == cto.id
                    or input_cable.destination_id == cto.id
                ):
                    raise serializers.ValidationError({
                        "splitter_input_cable_id": "O cabo não está conectado a esta CTO."
                    })
                splitter.input_cable = input_cable
                splitter.input_fiber = None
                if previous_fiber is not None:
                    previous_fiber.status = FiberStrand.Status.FREE
                    previous_fiber.destination_element = None
                    previous_fiber.usage = ""
                    previous_fiber.save(update_fields=[
                        "status", "destination_element", "usage", "updated_at"
                    ])
                    previous_cable = previous_fiber.cable
                    previous_cable.used_fibers = previous_cable.fibers.filter(
                        status=FiberStrand.Status.USED
                    ).count()
                    previous_cable.save(update_fields=["used_fibers", "updated_at"])
            if input_fiber_id is not None:
                try:
                    input_fiber = FiberStrand.objects.select_related("cable").get(
                        pk=input_fiber_id,
                        cable=splitter.input_cable,
                    )
                except FiberStrand.DoesNotExist:
                    raise serializers.ValidationError({
                        "splitter_input_fiber_id": "Fibra não pertence ao cabo selecionado."
                    })
                splitter.input_fiber = input_fiber
                input_fiber.status = FiberStrand.Status.USED
                input_fiber.destination_element = cto
                input_fiber.usage = f"Entrada do {splitter.name} em {cto.name}"
                input_fiber.save(update_fields=[
                    "status", "destination_element", "usage", "updated_at"
                ])
                input_cable = input_fiber.cable
                input_cable.used_fibers = input_cable.fibers.filter(
                    status=FiberStrand.Status.USED
                ).count()
                input_cable.save(update_fields=["used_fibers", "updated_at"])
            if input_cable_id is not None or input_fiber_id is not None:
                splitter.save(update_fields=[
                    "input_cable", "input_fiber", "updated_at"
                ])
        if instance.element_type == NetworkElement.ElementType.SPLICE_BOX and ceo_tray_count is not None:
            sync_splice_box(
                instance,
                ceo_tray_count,
                ceo_splitters if ceo_splitters is not None else 0,
                ceo_ratio or CTOSplitter.Ratio.ONE_TO_8,
            )

        return instance
