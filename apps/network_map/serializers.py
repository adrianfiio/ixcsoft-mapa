
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


CTO_CAPACITY_RATIOS = {
    8: CTOSplitter.Ratio.ONE_TO_8,
    16: CTOSplitter.Ratio.ONE_TO_16,
}


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
    internal_equipment = serializers.ListField(
        child=serializers.CharField(max_length=180),
        write_only=True,
        required=False,
    )
    element_subtype = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=40,
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
            "splitter_input_cable_id",
            "splitter_input_fiber_id",
            "internal_equipment",
            "element_subtype",
        ]


    def validate_cto_capacity(self, value):
        value = int(value)
        if value not in CTO_CAPACITY_RATIOS:
            raise serializers.ValidationError("A CTO deve possuir capacidade de 8 ou 16 portas.")
        return value


    def create(self, validated_data):
        cto_capacity = int(validated_data.pop("cto_capacity", 8))
        validated_data.pop("splitter_ratio", None)
        validated_data.pop("splitter_ports", None)
        validated_data.pop("splitter_input_cable_id", None)
        validated_data.pop("splitter_input_fiber_id", None)
        splitter_ratio = CTO_CAPACITY_RATIOS[cto_capacity]
        splitter_ports = cto_capacity
        internal_equipment = validated_data.pop("internal_equipment", [])
        element_subtype = validated_data.pop("element_subtype", "")

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
            sync_splice_box(cto, 1, 1, splitter_ratio)
            return cto

        if element_subtype:
            validated_data["metadata"] = {**validated_data.get("metadata", {}), "import_subtype": element_subtype}
        element = NetworkElement.objects.create(**validated_data)
        if internal_equipment:
            element.metadata = {**element.metadata, "internal_equipment": internal_equipment}
            element.save(update_fields=["metadata", "updated_at"])
        if element.element_type == NetworkElement.ElementType.SPLICE_BOX:
            # Uma única bandeja implícita por CEO — splitters são adicionados
            # livremente no diagrama de Fusões, sem pré-configuração aqui.
            sync_splice_box(element, 1, 0, CTOSplitter.Ratio.ONE_TO_8)
        return element


    def update(self, instance, validated_data):
        cto_capacity = validated_data.pop("cto_capacity", None)
        validated_data.pop("splitter_ratio", None)
        validated_data.pop("splitter_ports", None)
        validated_data.pop("splitter_input_cable_id", None)
        validated_data.pop("splitter_input_fiber_id", None)
        internal_equipment = validated_data.pop("internal_equipment", None)
        element_subtype = validated_data.pop("element_subtype", None)

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


        if element_subtype is not None:
            instance.metadata = {**instance.metadata, "import_subtype": element_subtype}
        instance.save()
        if internal_equipment is not None:
            instance.metadata = {**instance.metadata, "internal_equipment": internal_equipment}
            instance.save(update_fields=["metadata", "updated_at"])

        if isinstance(instance, CTO):
            cto = instance
        else:
            try:
                cto = instance.cto
            except CTO.DoesNotExist:
                cto = None

        if cto is not None and cto_capacity is not None:
            target_capacity = int(cto_capacity)
            target_ratio = CTO_CAPACITY_RATIOS[target_capacity]
            busy_commercial = CTOSplitterPort.objects.filter(
                splitter__cto=cto, number__gt=target_capacity
            ).exclude(status=CTOSplitterPort.Status.FREE).exists()
            busy_graphical = SpliceTraySplitterPort.objects.filter(
                splitter__tray__splice_box=cto,
                number__gt=target_capacity,
                output_fiber__isnull=False,
            ).exists()
            busy_cascade = SpliceTraySplitter.objects.filter(
                tray__splice_box=cto,
                input_splitter_port__number__gt=target_capacity,
            ).exists()
            if busy_commercial or busy_graphical or busy_cascade:
                raise serializers.ValidationError({
                    "cto_capacity": "Existem ligações nas portas acima da nova capacidade. Remova essas ligações antes de reduzir a CTO."
                })
            cto.capacity = target_capacity
            cto.splitter_ratio = target_ratio
            cto.save(update_fields=["capacity", "splitter_ratio", "updated_at"])
            splitter, _created = CTOSplitter.objects.get_or_create(
                cto=cto,
                position=1,
                defaults={
                    "name": "Splitter 1",
                    "ratio": target_ratio,
                    "output_ports": target_capacity,
                },
            )
            splitter.ratio = target_ratio
            splitter.input_cable = None
            splitter.input_fiber = None
            splitter.save(update_fields=["ratio", "input_cable", "input_fiber", "updated_at"])
            sync_splitter_ports(splitter, target_capacity)
            sync_splice_box(cto, 1, 1, target_ratio)
        if (
            instance.element_type == NetworkElement.ElementType.SPLICE_BOX
            and not instance.splice_trays.exists()
        ):
            # Elemento antigo sem bandeja (não deveria acontecer para
            # elementos criados após a v0.36.0, mas garante que o diagrama
            # de Fusões sempre tenha uma bandeja implícita para os splitters.
            sync_splice_box(instance, 1, 0, CTOSplitter.Ratio.ONE_TO_8)

        return instance
