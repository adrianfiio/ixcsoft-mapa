from django import forms

from apps.access.models import AccessPoint

from .models import Customer, PaymentMethod


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = (
            "name",
            "document",
            "email",
            "phone",
            "address",
            "status",
            "monthly_amount",
            "due_day",
            "billing_active",
            "access_point",
            "notes",
        )
        labels = {
            "name": "Nome",
            "document": "CPF/CNPJ",
            "email": "E-mail",
            "phone": "Telefone",
            "address": "Endereço",
            "status": "Situação",
            "monthly_amount": "Mensalidade (R$)",
            "due_day": "Dia de vencimento",
            "billing_active": "Gerar mensalidade automaticamente",
            "access_point": "Vincular a um ponto de acesso (opcional)",
            "notes": "Observações",
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["access_point"].required = False
        self.fields["access_point"].empty_label = "— nenhum —"
        queryset = AccessPoint.objects.none()
        if company is not None:
            queryset = AccessPoint.objects.filter(company=company).order_by("customer_name")
        self.fields["access_point"].queryset = queryset


class PaymentRecordForm(forms.Form):
    amount = forms.DecimalField(label="Valor pago (R$)", max_digits=10, decimal_places=2, min_value=0.01)
    method = forms.ChoiceField(label="Forma de pagamento", choices=PaymentMethod.choices)
    note = forms.CharField(label="Observação", required=False, widget=forms.Textarea(attrs={"rows": 2}))
