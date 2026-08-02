from django.core.management.base import BaseCommand

from apps.network_map.map_master_models import MapIconStyle


ICONS = {
    ("cto", ""): {
        "display_name": "CTO",
        "svg_markup": '<rect x="4" y="6" width="24" height="18" rx="4"/><path d="M8 11h16M8 16h16M11 24v4m10-4v4"/>',
        "border_color": "#f6c744",
        "background_color": "#332b10",
        "size_px": 28,
    },
    ("splice_box", "ceo"): {
        "display_name": "CEO",
        "svg_markup": '<path d="M11 2h10l7 8v12l-7 8H11l-7-8V10z"/><path d="M10 10h12M10 16h12M10 22h12"/>',
        "border_color": "#59d4ff",
        "background_color": "#0b2b3c",
        "size_px": 28,
    },
    ("splice_box", "cdo"): {
        "display_name": "CDO",
        "svg_markup": '<rect x="8" y="2" width="16" height="28" rx="7"/><path d="M11 9h10M11 15h10M11 21h10"/><circle cx="16" cy="27" r="1.5"/>',
        "border_color": "#a78bfa",
        "background_color": "#24173f",
        "size_px": 27,
    },
    ("rack", ""): {
        "display_name": "Rack",
        "svg_markup": '<rect x="7" y="2" width="18" height="28" rx="3"/><path d="M11 8h10M11 14h10M11 20h10M11 26h10"/>',
        "border_color": "#7dd3fc",
        "background_color": "#10283a",
        "size_px": 30,
    },
    ("tower", ""): {
        "display_name": "Torre",
        "svg_markup": '<path d="M16 2 8 30m8-28 8 28M11 20h10M12.5 14h7M14 8h4M6 30h20"/>',
        "border_color": "#fb923c",
        "background_color": "#3a2010",
        "size_px": 30,
    },
    ("pole", ""): {
        "display_name": "Poste",
        "svg_markup": '<path d="M16 3v27M8 9h16M11 30h10M10 9l6 7 6-7"/>',
        "border_color": "#cbd5e1",
        "background_color": "#1e293b",
        "size_px": 27,
    },
    ("other", "pto"): {
        "display_name": "PTO",
        "svg_markup": '<rect x="5" y="7" width="22" height="18" rx="4"/><circle cx="12" cy="16" r="3"/><circle cx="20" cy="16" r="3"/>',
        "border_color": "#34d399",
        "background_color": "#0d3529",
        "size_px": 26,
    },
}


class Command(BaseCommand):
    help = "Cria os estilos iniciais de ícones configuráveis do mapa."

    def add_arguments(self, parser):
        parser.add_argument("--company-id", type=int, default=None)
        parser.add_argument("--replace", action="store_true")

    def handle(self, *args, **options):
        company_model = MapIconStyle._meta.get_field("company").remote_field.model
        companies = company_model.objects.all()
        if options["company_id"]:
            companies = companies.filter(pk=options["company_id"])
        created = updated = 0
        for company in companies:
            for (element_type, subtype), defaults in ICONS.items():
                lookup = {
                    "company": company,
                    "element_type": element_type,
                    "subtype": subtype,
                }
                if options["replace"]:
                    _obj, was_created = MapIconStyle.objects.update_or_create(**lookup, defaults=defaults)
                else:
                    _obj, was_created = MapIconStyle.objects.get_or_create(**lookup, defaults=defaults)
                created += int(was_created)
                updated += int(not was_created and options["replace"])
        self.stdout.write(self.style.SUCCESS(f"Ícones: {created} criados, {updated} atualizados."))
