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


class CompanySubscription(TimeStampedModel):
    """Assinatura da empresa (Provedor ISP ou Projetista) junto à
    plataforma — quem é cobrado aqui é a própria empresa cliente da
    AFService, não os assinantes de internet de cada provedor. Gerida
    exclusivamente pelo Superadmin.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Ativa"
        BLOCKED = "blocked", "Bloqueada"
        CANCELED = "canceled", "Cancelada"

    company = models.OneToOneField(
        "core.Company", on_delete=models.CASCADE, related_name="subscription"
    )
    monthly_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Mensalidade",
        help_text="Deixe em branco se esta empresa não tem cobrança recorrente.",
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
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    # Enquanto no futuro (maior que agora), o acesso ao sistema não é
    # bloqueado mesmo com status BLOCKED/CANCELED — é a "liberação de
    # confiança" (services.request_trust_release) e também usado pelo
    # Superadmin pra dar um prazo antes de bloquear de verdade.
    access_grace_until = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Assinatura da empresa"
        verbose_name_plural = "Assinaturas das empresas"

    def __str__(self):
        return f"{self.company} · {self.get_status_display()}"


class TrustRelease(TimeStampedModel):
    """Registro de "liberação de confiança" pedida pela própria empresa
    — concede mais 2 dias de acesso mesmo com a assinatura bloqueada/
    cancelada. Limitado a 1 uso por mês corrido, validado no backend
    (`services.request_trust_release`)."""

    company = models.ForeignKey(
        "core.Company", on_delete=models.CASCADE, related_name="trust_releases"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    granted_until = models.DateTimeField()

    class Meta:
        verbose_name = "Liberação de confiança"
        verbose_name_plural = "Liberações de confiança"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "created_at"], name="billing_trust_company_idx"),
        ]

    def __str__(self):
        return f"{self.company} · {self.created_at:%d/%m/%Y}"


class Invoice(CompanyScopedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PAID = "paid", "Paga"
        OVERDUE = "overdue", "Atrasada"
        CANCELED = "canceled", "Cancelada"

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
                fields=["company", "reference_month"],
                name="unique_invoice_company_month",
            )
        ]
        indexes = [
            models.Index(fields=["company", "status"], name="billing_invoice_status_idx"),
            models.Index(fields=["status", "due_date"], name="billing_invoice_due_idx"),
        ]

    def __str__(self):
        return f"{self.company} · {self.reference_month:%m/%Y}"

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


class CompanyPaymentGatewayConfiguration(TimeStampedModel):
    """Guarda a credencial do gateway de pagamento escolhido por empresa,
    gerenciada pelo Superadmin. Só armazenamento — nenhuma chamada real
    de API/webhook acontece a partir daqui nesta rodada (mesma decisão
    já tomada na v0.74.0 sobre `Invoice.gateway_provider`).

    `credentials_encrypted` guarda um JSON criptografado (via
    `apps.core.crypto.SecretCipher`, mesmo padrão de
    `CompanyEmailConfiguration.password_encrypted`) com as chaves que o
    provedor escolhido precisar (client_id/client_secret/access_token) —
    de propósito genérico, pra não exigir nova migration quando a
    integração real de cada gateway definir os campos exatos."""

    company = models.OneToOneField(
        "core.Company", on_delete=models.CASCADE, related_name="payment_gateway"
    )
    provider = models.CharField(
        max_length=20, choices=GatewayProvider.choices, default=GatewayProvider.NONE
    )
    credentials_encrypted = models.TextField(blank=True, editable=False)
    sandbox_mode = models.BooleanField(default=True, verbose_name="Ambiente de testes (sandbox)")
    enabled = models.BooleanField(default=False, verbose_name="Integração ativa")

    class Meta:
        verbose_name = "Configuração de gateway de pagamento"
        verbose_name_plural = "Configurações de gateway de pagamento"

    def __str__(self):
        return f"{self.company} · {self.get_provider_display()}"
