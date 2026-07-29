from django import forms
from django.contrib.gis.geos import Point

from .models import NetworkElement


class NetworkElementForm(forms.ModelForm):
    latitude = forms.DecimalField(
        label="Latitude",
        max_digits=10,
        decimal_places=7,
        required=False,
        min_value=-90,
        max_value=90,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "placeholder": "-23.5505000",
                "step": "0.0000001",
            }
        ),
    )

    longitude = forms.DecimalField(
        label="Longitude",
        max_digits=10,
        decimal_places=7,
        required=False,
        min_value=-180,
        max_value=180,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "placeholder": "-46.6333000",
                "step": "0.0000001",
            }
        ),
    )

    class Meta:
        model = NetworkElement
        fields = [
            "name",
            "code",
            "element_type",
            "status",
            "description",
            "latitude",
            "longitude",
            "enabled",
        ]

        labels = {
            "name": "Nome",
            "code": "Código",
            "element_type": "Tipo",
            "status": "Status",
            "description": "Descrição",
            "enabled": "Ativo",
        }

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex.: OLT AFService 01",
                    "autofocus": True,
                }
            ),
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex.: OLT-001",
                }
            ),
            "element_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Informações adicionais sobre o equipamento",
                }
            ),
            "enabled": forms.CheckboxInput(
                attrs={
                    "class": "checkbox-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.point:
            self.fields["latitude"].initial = self.instance.point.y
            self.fields["longitude"].initial = self.instance.point.x

    def clean(self):
        cleaned_data = super().clean()

        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")

        if latitude is not None and longitude is None:
            self.add_error(
                "longitude",
                "Informe a longitude junto com a latitude.",
            )

        if longitude is not None and latitude is None:
            self.add_error(
                "latitude",
                "Informe a latitude junto com a longitude.",
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        latitude = self.cleaned_data.get("latitude")
        longitude = self.cleaned_data.get("longitude")

        if latitude is not None and longitude is not None:
            instance.point = Point(
                float(longitude),
                float(latitude),
                srid=4326,
            )
        else:
            instance.point = None

        if commit:
            instance.save()
            self.save_m2m()

        return instance
