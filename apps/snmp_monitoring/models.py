from __future__ import annotations

import re
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q

from apps.core.crypto import SecretCipher
from apps.core.enums import OperationalStatus, Severity
from apps.core.models import CompanyScopedModel


_HEX_COLOR = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Informe uma cor hexadecimal no formato #RRGGBB.",
)


def _generate_influx_id():
    return uuid.uuid4().hex


def normalize_interface_name(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


class SNMPMonitoringProfile(CompanyScopedModel):
    """Configuração SNMP de um ativo de mapa ou equipamento interno.

    Perfis antigos continuam podendo apontar para ``NetworkElement``. Para
    switches, roteadores, firewalls, servidores, APs e rádios internos de
    Rack/Torre, o alvo passa a ser ``ContainerEquipment``. OLT é bloqueada
    nesta integração porque possui fluxo próprio e OIDs específicos.
    """

    class SNMPVersion(models.TextChoices):
        V2C = "2c", "SNMP v2c"

    class AggregatePolicy(models.TextChoices):
        BOUND_PORTS = "bound_ports", "Somente portas vinculadas"
        ALL_INTERFACES = "all_interfaces", "Todas as interfaces detectadas"
        NO_AGGREGATE = "no_aggregate", "Não alterar status agregado"

    element = models.OneToOneField(
        "network_map.NetworkElement",
        on_delete=models.CASCADE,
        related_name="snmp_monitoring",
        null=True,
        blank=True,
    )
    equipment = models.OneToOneField(
        "network_map.ContainerEquipment",
        on_delete=models.CASCADE,
        related_name="snmp_monitoring",
        null=True,
        blank=True,
    )
    enabled = models.BooleanField(default=True)
    management_ip = models.GenericIPAddressField()
    port = models.PositiveIntegerField(
        default=161,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
    )
    snmp_version = models.CharField(
        max_length=10,
        choices=SNMPVersion.choices,
        default=SNMPVersion.V2C,
    )
    community_encrypted = models.TextField(blank=True)
    polling_interval_seconds = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(3600)],
    )
    aggregate_policy = models.CharField(
        max_length=24,
        choices=AggregatePolicy.choices,
        default=AggregatePolicy.BOUND_PORTS,
    )
    influx_id = models.CharField(
        max_length=32,
        unique=True,
        editable=False,
        default=_generate_influx_id,
    )
    last_poll_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_poll_message = models.TextField(blank=True)
    last_status = models.CharField(
        max_length=20,
        choices=OperationalStatus.choices,
        default=OperationalStatus.NO_DATA,
    )

    class Meta:
        verbose_name = "Monitoramento SNMP"
        verbose_name_plural = "Monitoramentos SNMP"
        indexes = [
            models.Index(fields=["enabled"]),
            models.Index(fields=["company", "last_status"], name="snmp_prof_company_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(element__isnull=False, equipment__isnull=True)
                    | Q(element__isnull=True, equipment__isnull=False)
                ),
                name="snmp_profile_exactly_one_target",
            ),
        ]

    def __str__(self):
        return f"SNMP · {self.target_name} ({self.management_ip})"

    @property
    def target(self):
        return self.equipment or self.element

    @property
    def target_name(self) -> str:
        target = self.target
        return getattr(target, "name", "Ativo sem alvo")

    @property
    def target_element(self):
        if self.element_id:
            return self.element
        if self.equipment_id:
            return self.equipment.container
        return None

    @property
    def is_olt(self) -> bool:
        if self.equipment_id:
            return str(self.equipment.equipment_type).lower() == "olt"
        if self.element_id:
            return str(self.element.element_type).lower() == "olt"
        return False

    def clean(self):
        super().clean()
        if bool(self.element_id) == bool(self.equipment_id):
            raise ValidationError("Selecione exatamente um alvo: elemento ou equipamento interno.")
        if self.is_olt:
            raise ValidationError(
                "OLT não usa este monitoramento universal. Configure-a pela integração específica de OLT."
            )
        target = self.target
        if target and self.company_id and target.company_id != self.company_id:
            raise ValidationError("O alvo pertence a outra empresa.")

    def save(self, *args, **kwargs):
        target = self.target
        if target and not self.company_id:
            self.company_id = target.company_id
        self.full_clean()
        super().save(*args, **kwargs)

    def set_community(self, raw_value):
        self.community_encrypted = SecretCipher().encrypt(raw_value) if raw_value else ""

    def get_community(self):
        return SecretCipher().decrypt(self.community_encrypted) if self.community_encrypted else ""

    @property
    def conf_filename(self):
        return f"element_{self.influx_id}.conf"


class SNMPInterfaceState(CompanyScopedModel):
    class Status(models.TextChoices):
        UP = "up", "UP"
        DOWN = "down", "DOWN"
        TESTING = "testing", "Testando"
        UNKNOWN = "unknown", "Desconhecido"
        DORMANT = "dormant", "Dormente"
        NOT_PRESENT = "not_present", "Não presente"
        LOWER_LAYER_DOWN = "lower_layer_down", "Camada inferior DOWN"
        OTHER = "other", "Outro"

    profile = models.ForeignKey(
        SNMPMonitoringProfile,
        on_delete=models.CASCADE,
        related_name="interface_states",
    )
    interface_key = models.CharField(max_length=260)
    if_name = models.CharField(max_length=255)
    if_index = models.PositiveIntegerField(null=True, blank=True)
    if_alias = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.UNKNOWN)
    raw_status = models.IntegerField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("profile", "if_index", "if_name")
        constraints = [
            models.UniqueConstraint(
                fields=("profile", "interface_key"),
                name="unique_snmp_interface_state_per_profile",
            ),
        ]
        indexes = [
            models.Index(fields=("profile", "status"), name="snmp_state_profile_status_idx"),
            models.Index(fields=("company", "last_seen_at"), name="snmp_state_company_seen_idx"),
        ]
        verbose_name = "Estado de interface SNMP"
        verbose_name_plural = "Estados de interfaces SNMP"

    @staticmethod
    def build_key(if_name: str, if_index: int | None = None) -> str:
        if if_index not in (None, ""):
            return f"index:{int(if_index)}"
        return f"name:{normalize_interface_name(if_name)}"

    def save(self, *args, **kwargs):
        self.company_id = self.company_id or self.profile.company_id
        self.interface_key = self.build_key(self.if_name, self.if_index)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.profile.target_name} · {self.if_name} · {self.get_status_display()}"


class SNMPPortBinding(CompanyScopedModel):
    class Role(models.TextChoices):
        BACKBONE = "backbone", "Backbone"
        UPLINK = "uplink", "Uplink"
        ACCESS = "access", "Acesso"
        WIRELESS = "wireless", "Wireless/PTP"
        MANAGEMENT = "management", "Gerência"
        OTHER = "other", "Outro"

    class Status(models.TextChoices):
        UP = "up", "UP"
        DOWN = "down", "DOWN"
        UNKNOWN = "unknown", "Sem dados"
        OTHER = "other", "Outro"

    profile = models.ForeignKey(
        SNMPMonitoringProfile,
        on_delete=models.CASCADE,
        related_name="port_bindings",
    )
    equipment_port = models.OneToOneField(
        "network_map.ContainerEquipmentPort",
        on_delete=models.SET_NULL,
        related_name="snmp_binding",
        null=True,
        blank=True,
    )
    label = models.CharField(max_length=160, blank=True)
    if_name = models.CharField(max_length=255)
    if_index = models.PositiveIntegerField(null=True, blank=True)
    role = models.CharField(max_length=24, choices=Role.choices, default=Role.OTHER)
    enabled = models.BooleanField(default=True)
    expected_up = models.BooleanField(default=True)
    alert_enabled = models.BooleanField(default=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.HIGH)
    outage_persistence_seconds = models.PositiveIntegerField(default=30)
    recovery_seconds = models.PositiveIntegerField(default=30)
    last_status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNKNOWN)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    down_since = models.DateTimeField(null=True, blank=True)
    up_since = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("profile", "role", "if_index", "if_name")
        constraints = [
            models.UniqueConstraint(
                fields=("profile", "if_name"),
                name="unique_snmp_if_name_per_profile",
            ),
            models.UniqueConstraint(
                fields=("profile", "if_index"),
                condition=Q(if_index__isnull=False),
                name="unique_snmp_if_index_per_profile",
            ),
        ]
        indexes = [
            models.Index(fields=("profile", "enabled", "last_status"), name="snmp_bind_profile_status_idx"),
            models.Index(fields=("company", "role", "last_status"), name="snmp_bind_company_role_idx"),
        ]
        verbose_name = "Vínculo de porta SNMP"
        verbose_name_plural = "Vínculos de portas SNMP"

    def clean(self):
        super().clean()
        if self.equipment_port_id:
            if not self.profile.equipment_id:
                raise ValidationError("Porta interna só pode ser vinculada a perfil de equipamento interno.")
            if self.equipment_port.equipment_id != self.profile.equipment_id:
                raise ValidationError("A porta selecionada não pertence ao equipamento monitorado.")

    def save(self, *args, **kwargs):
        self.company_id = self.company_id or self.profile.company_id
        self.if_name = str(self.if_name or "").strip()
        if not self.label:
            self.label = self.equipment_port.label if self.equipment_port_id else self.if_name
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def target_element(self):
        return self.profile.target_element

    @property
    def display_name(self):
        port = self.equipment_port.label if self.equipment_port_id else self.label
        return f"{self.profile.target_name} · {port or self.if_name}"

    def __str__(self):
        return self.display_name


class MonitoredNetworkLink(CompanyScopedModel):
    class LinkType(models.TextChoices):
        BACKBONE = "backbone", "Backbone óptico"
        FIBER = "fiber", "Fibra óptica"
        COPPER = "copper", "Cobre"
        WIRELESS = "wireless", "PTP wireless"

    project = models.ForeignKey(
        "network_map.NetworkProject",
        on_delete=models.CASCADE,
        related_name="monitored_links",
    )
    name = models.CharField(max_length=180)
    code = models.CharField(max_length=100, blank=True)
    link_type = models.CharField(max_length=20, choices=LinkType.choices)
    source_element = models.ForeignKey(
        "network_map.NetworkElement",
        on_delete=models.CASCADE,
        related_name="monitored_links_as_source",
    )
    destination_element = models.ForeignKey(
        "network_map.NetworkElement",
        on_delete=models.CASCADE,
        related_name="monitored_links_as_destination",
    )
    source_binding = models.ForeignKey(
        SNMPPortBinding,
        on_delete=models.SET_NULL,
        related_name="source_links",
        null=True,
        blank=True,
    )
    destination_binding = models.ForeignKey(
        SNMPPortBinding,
        on_delete=models.SET_NULL,
        related_name="destination_links",
        null=True,
        blank=True,
    )
    cable = models.OneToOneField(
        "network_map.FiberCable",
        on_delete=models.SET_NULL,
        related_name="monitored_link",
        null=True,
        blank=True,
    )
    enabled = models.BooleanField(default=True)
    require_both_endpoints = models.BooleanField(default=True)
    alert_enabled = models.BooleanField(default=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.HIGH)
    normal_color = models.CharField(max_length=7, default="#38bdf8", validators=[_HEX_COLOR])
    down_color = models.CharField(max_length=7, default="#ef4444", validators=[_HEX_COLOR])
    dash_array = models.CharField(max_length=40, blank=True)
    weight = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(2), MaxValueValidator(12)],
    )
    outage_persistence_seconds = models.PositiveIntegerField(default=30)
    recovery_seconds = models.PositiveIntegerField(default=30)
    status = models.CharField(
        max_length=20,
        choices=OperationalStatus.choices,
        default=OperationalStatus.NO_DATA,
    )
    candidate_status = models.CharField(
        max_length=20,
        choices=OperationalStatus.choices,
        blank=True,
    )
    candidate_since = models.DateTimeField(null=True, blank=True)
    status_changed_at = models.DateTimeField(null=True, blank=True)
    last_evaluated_at = models.DateTimeField(null=True, blank=True)
    last_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("project", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("project", "code"),
                condition=~Q(code=""),
                name="unique_monitored_link_code_per_project",
            ),
            models.CheckConstraint(
                condition=~Q(source_element=models.F("destination_element")),
                name="monitored_link_distinct_elements",
            ),
        ]
        indexes = [
            models.Index(fields=("project", "enabled", "status"), name="snmp_link_project_status_idx"),
            models.Index(fields=("company", "status", "status_changed_at"), name="snmp_link_company_status_idx"),
        ]
        verbose_name = "Enlace monitorado"
        verbose_name_plural = "Enlaces monitorados"

    def clean(self):
        super().clean()
        if self.source_element_id and self.destination_element_id:
            if self.source_element.company_id != self.destination_element.company_id:
                raise ValidationError("As duas pontas devem pertencer à mesma empresa.")
            if self.source_element.project_id != self.destination_element.project_id:
                raise ValidationError("As duas pontas devem pertencer ao mesmo projeto.")
            if self.project_id and self.source_element.project_id != self.project_id:
                raise ValidationError("As pontas não pertencem ao projeto escolhido.")
        for field_name, binding, element in (
            ("source_binding", self.source_binding, self.source_element),
            ("destination_binding", self.destination_binding, self.destination_element),
        ):
            if binding and binding.profile.is_olt:
                raise ValidationError({field_name: "OLT não é suportada por este monitoramento universal."})
            if binding and binding.target_element and element and binding.target_element.pk != element.pk:
                raise ValidationError({field_name: "A porta monitorada não pertence à estrutura selecionada."})
        if self.link_type in {self.LinkType.BACKBONE, self.LinkType.FIBER} and not self.cable_id:
            raise ValidationError("Enlace backbone/fibra precisa estar associado a um cabo óptico.")
        if self.link_type == self.LinkType.WIRELESS and self.cable_id:
            raise ValidationError("Enlace PTP wireless não deve estar associado a cabo óptico.")
        if self.cable_id:
            if self.cable.company_id != self.company_id:
                raise ValidationError("O cabo pertence a outra empresa.")
            if self.cable.project_id != self.project_id:
                raise ValidationError("O cabo pertence a outro projeto.")
        if self.link_type == self.LinkType.WIRELESS and not self.dash_array:
            self.dash_array = "12 10"

    def save(self, *args, **kwargs):
        if self.project_id and not self.company_id:
            self.company_id = self.project.company_id
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def endpoint_bindings(self):
        return [item for item in (self.source_binding, self.destination_binding) if item]

    @property
    def display_color(self):
        return self.down_color if self.status == OperationalStatus.OFFLINE else self.normal_color

    def __str__(self):
        return f"{self.name} · {self.get_status_display()}"
