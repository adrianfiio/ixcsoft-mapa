from django.core.management.base import BaseCommand

from apps.snmp_monitoring import services
from apps.snmp_monitoring.docker_control import reload_telegraf
from apps.snmp_monitoring.models import SNMPMonitoringProfile
from apps.snmp_monitoring.tasks import apply_snmp_monitoring_profile, poll_snmp_status


class Command(BaseCommand):
    help = "Regenera os .conf do Telegraf e opcionalmente agenda uma consulta SNMP."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Grava todos os arquivos agora e envia um único SIGHUP ao Telegraf.",
        )
        parser.add_argument("--poll", action="store_true", help="Agenda uma consulta após regenerar.")

    def handle(self, *args, **options):
        profiles = list(SNMPMonitoringProfile.objects.select_related("element", "equipment"))
        ids = [profile.id for profile in profiles]
        if options["sync"]:
            for profile in profiles:
                if profile.enabled:
                    services.write_conf(profile)
                else:
                    services.remove_conf_by_influx_id(profile.influx_id)
            reload_telegraf()
        else:
            for profile_id in ids:
                apply_snmp_monitoring_profile.delay(profile_id)
        if options["poll"] and ids:
            poll_snmp_status.delay(ids)
        self.stdout.write(self.style.SUCCESS(f"{len(ids)} perfil(is) encaminhado(s) para regeneração."))
