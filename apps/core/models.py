from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CompanyScopedModel(TimeStampedModel):
    company = models.ForeignKey(
        "core.Company",
        on_delete=models.CASCADE,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


class NamedModel(TimeStampedModel):
    name = models.CharField(max_length=180, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Company(TimeStampedModel):
    name = models.CharField(max_length=180)
    trade_name = models.CharField(max_length=180, blank=True)
    document = models.CharField(max_length=30, blank=True)
    slug = models.SlugField(max_length=180, unique=True)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ["name"]

    def __str__(self):
        return self.trade_name or self.name
