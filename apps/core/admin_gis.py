from django import forms
from django.contrib.gis.admin import GISModelAdmin
from django.contrib.gis.geos import Point


class GeoPointAdminForm(forms.ModelForm):
    latitude = forms.DecimalField(
        label="Latitude",
        required=False,
        min_value=-90,
        max_value=90,
        decimal_places=7,
        max_digits=10,
        help_text="Informe manualmente, use o GPS ou busque um endereço.",
    )
    longitude = forms.DecimalField(
        label="Longitude",
        required=False,
        min_value=-180,
        max_value=180,
        decimal_places=7,
        max_digits=10,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.point:
            self.fields["latitude"].initial = self.instance.point.y
            self.fields["longitude"].initial = self.instance.point.x

    def clean(self):
        cleaned = super().clean()
        latitude = cleaned.get("latitude")
        longitude = cleaned.get("longitude")
        if (latitude is None) != (longitude is None):
            raise forms.ValidationError("Informe latitude e longitude juntas.")
        if latitude is not None:
            point = Point(float(longitude), float(latitude), srid=4326)
            cleaned["point"] = point
            self.instance.point = point
        return cleaned

    class Media:
        js = ("js/admin-location.js",)


class AFServiceGISAdmin(GISModelAdmin):
    """Mapa administrativo centrado na região operacional padrão."""

    gis_widget_kwargs = {
        "attrs": {
            "default_lon": -50.7586,
            "default_lat": -24.4480,
            "default_zoom": 14,
        }
    }
