from django import forms

from .models import CompanySubscription, GatewayProvider, PaymentMethod


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = CompanySubscription
        fields = ("monthly_amount", "due_day", "billing_active", "notes")
        labels = {
            "monthly_amount": "Mensalidade (R$)",
            "due_day": "Dia de vencimento",
            "billing_active": "Gerar mensalidade automaticamente",
            "notes": "Observações",
        }


class ManualInvoiceForm(forms.Form):
    """"Lançar cobrança manual" — fatura avulsa, fora do ciclo mensal
    automático (que já cobre a mensalidade recorrente sozinho)."""

    amount = forms.DecimalField(label="Valor (R$)", max_digits=10, decimal_places=2, min_value=0.01)
    due_date = forms.DateField(label="Vencimento", widget=forms.DateInput(attrs={"type": "date"}))
    notes = forms.CharField(label="Observação", required=False, widget=forms.Textarea(attrs={"rows": 2}))


class PaymentRecordForm(forms.Form):
    amount = forms.DecimalField(label="Valor pago (R$)", max_digits=10, decimal_places=2, min_value=0.01)
    method = forms.ChoiceField(label="Forma de pagamento", choices=PaymentMethod.choices)
    note = forms.CharField(label="Observação", required=False, widget=forms.Textarea(attrs={"rows": 2}))


class GatewaySettingsForm(forms.Form):
    """Só guarda a credencial (criptografada) — nenhuma chamada real ao
    gateway acontece a partir daqui nesta rodada. Os 3 campos genéricos
    cobrem o que a maioria dos gateways pede; o que não se aplicar ao
    provedor escolhido fica em branco."""

    provider = forms.ChoiceField(label="Gateway", choices=GatewayProvider.choices)
    sandbox_mode = forms.BooleanField(label="Ambiente de testes (sandbox)", required=False, initial=True)
    enabled = forms.BooleanField(label="Integração ativa", required=False)
    client_id = forms.CharField(label="Client ID", required=False)
    client_secret = forms.CharField(label="Client Secret", required=False, widget=forms.PasswordInput(render_value=False))
    access_token = forms.CharField(label="Token de acesso", required=False, widget=forms.PasswordInput(render_value=False))
