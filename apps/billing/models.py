from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import CompanyScopedModel, TimeStampedModel


class PaymentMethod(models.TextChoices):
    CASH = "cash", "Dinheiro"
    PIX = "pix", "PIX"
    TRANSFER = "transfer", "Transferência"
    CARD = "card", "Cartão"
    GATEWAY = "gateway", "Gateway de pagamento"
    OTHER = "other", "Outro"


class GatewayProvider(models.TextChoices):
    NONE = "none", "Nenhum (cobrança manual)"
    EFI = "efi", "Efí"
    INTER = "inter", "Inter"
    MERCADO_PAGO = "mercado_pago", "Mercado Pago"


class Customer(CompanyScopedModel):
    """Cliente cadastrado para controle financeiro.

    Não depende de integração com ERP nem de já existir um AccessPoint —
    a empresa pode não ter ERP nenhum. O vínculo com AccessPoint é
    opcional, só para quem já usa o mapa/ERP.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        INACTIVE = "inactive", "Inativo"
        SUSPENDED = "suspended", "Suspenso"

    name = models.CharField(max_length=180, verbose_name="Nome")
    document = models.CharField(max_length=30, blank=True, verbose_name="CPF/CNPJ")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True, verbose_name="Telefone")
    address = models.CharField(max_length=255, blank=True, verbose_name="Endereço")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    access_point = models.ForeignKey(
        "access.AccessPoint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Ponto de acesso vinculado",
        help_text="Opcional — vincula este cliente a um cadastro já existente no mapa/ERP.",
    )
    monthly_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Mensalidade",
        help_text="Deixe em branco se este cliente não tem cobrança recorrente.",
    )
    due_day = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        verbose_name="Dia de vencimento",
    )
    billing_active = models.BooleanField(
        default=True,
        verbose_name="Gerar mensalidade automaticamente",
    )
    notes = models.TextField(blank=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["company", "status"], name="billing_customer_status_idx"),
            models.Index(fields=["company", "billing_active"], name="billing_customer_active_idx"),
        ]

    def __str__(self):
        return self.name


class Invoice(CompanyScopedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PAID = "paid", "Paga"
        OVERDUE = "overdue", "Atrasada"
        CANCELED = "canceled", "Cancelada"

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="invoices"
    )
    reference_month = models.DateField(
        verbose_name="Mês de referência",
        help_text="Sempre o dia 1 do mês cobrado.",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField(verbose_name="Vencimento")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, blank=True
    )
    # Reservado para integração futura com gateway de pagamento (Efí,
    # Inter, Mercado Pago) — não integrado nesta rodada, só evita ter que
    # redesenhar o schema quando isso for implementado.
    gateway_provider = models.CharField(
        max_length=20, choices=GatewayProvider.choices, default=GatewayProvider.NONE
    )
    gateway_charge_id = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Fatura"
        verbose_name_plural = "Faturas"
        ordering = ["-reference_month"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "reference_month"],
                name="unique_invoice_customer_month",
            )
        ]
        indexes = [
            models.Index(fields=["company", "status"], name="billing_invoice_status_idx"),
            models.Index(fields=["customer", "status"], name="billing_invoice_customer_idx"),
            models.Index(fields=["status", "due_date"], name="billing_invoice_due_idx"),
        ]

    def __str__(self):
        return f"{self.customer} · {self.reference_month:%m/%Y}"

    def save(self, *args, **kwargs):
        if self.customer_id and not self.company_id:
            self.company_id = self.customer.company_id
        super().save(*args, **kwargs)

    @property
    def paid_amount(self):
        total = self.payments.aggregate(total=models.Sum("amount"))["total"]
        return total or 0

    @property
    def balance(self):
        return self.amount - self.paid_amount


class Payment(TimeStampedModel):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(default=timezone.now)
    method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    note = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        verbose_name = "Pagamento"
        verbose_name_plural = "Pagamentos"
        ordering = ["-paid_at"]

    def __str__(self):
        return f"{self.amount} · {self.paid_at:%d/%m/%Y}"
