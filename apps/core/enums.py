from django.db import models


class OperationalStatus(models.TextChoices):
    NORMAL = "normal", "Normal"
    WARNING = "warning", "Atenção"
    DEGRADED = "degraded", "Degradado"
    OFFLINE = "offline", "Offline"
    RECOVERING = "recovering", "Recuperando"
    NO_DATA = "no_data", "Sem dados"


class Severity(models.TextChoices):
    INFO = "info", "Informação"
    WARNING = "warning", "Aviso"
    AVERAGE = "average", "Média"
    HIGH = "high", "Alta"
    DISASTER = "disaster", "Desastre"
