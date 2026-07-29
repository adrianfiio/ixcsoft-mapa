from django.conf import settings
from django.db import connection
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic import TemplateView
from redis import Redis

from apps.access.models import AccessPoint
from apps.alerts.models import AlertEvent
from apps.ixc_integration.models import IXCCustomer, IXCSyncExecution
from apps.network_map.models import CTO, NetworkElement
from apps.core.enums import OperationalStatus
from apps.olt_integration.models import OLT, ONU


class DashboardView(TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        access_summary = AccessPoint.objects.aggregate(
            total=Count("id"),
            online=Count("id", filter=Q(status=AccessPoint.Status.ONLINE)),
            offline=Count("id", filter=Q(status=AccessPoint.Status.OFFLINE)),
            unknown=Count("id", filter=Q(status=AccessPoint.Status.UNKNOWN)),
            geolocated=Count(
                "id",
                filter=Q(latitude__isnull=False, longitude__isnull=False),
            ),
        )
        onu_summary = ONU.objects.aggregate(
            total=Count("id"),
            online=Count(
                "id",
                filter=Q(operational_status=OperationalStatus.NORMAL),
            ),
            offline=Count(
                "id",
                filter=Q(operational_status=OperationalStatus.OFFLINE),
            ),
            los=Count("id", filter=Q(los=True)),
        )
        active_alert_states = [
            AlertEvent.State.OPEN,
            AlertEvent.State.ACKNOWLEDGED,
            AlertEvent.State.RECOVERING,
        ]

        context.update(
            {
                "app_version": settings.APP_VERSION,
                "access": access_summary,
                "onus": onu_summary,
                "customer_count": IXCCustomer.objects.count(),
                "olt_count": OLT.objects.count(),
                "element_count": NetworkElement.objects.count(),
                "cto_count": CTO.objects.count(),
                "active_alert_count": AlertEvent.objects.filter(
                    state__in=active_alert_states
                ).count(),
                "recent_alerts": AlertEvent.objects.filter(
                    state__in=active_alert_states
                ).select_related("rule")[:5],
                "latest_sync": IXCSyncExecution.objects.order_by(
                    "-started_at", "-created_at"
                ).first(),
            }
        )
        return context


def liveness_check(request):
    return JsonResponse(
        {
            "status": "ok",
            "version": settings.APP_VERSION,
            "timestamp": timezone.now().isoformat(),
        }
    )


def readiness_check(request):
    services = {"database": False, "redis": False}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            services["database"] = cursor.fetchone()[0] == 1
    except Exception:
        services["database"] = False

    try:
        redis_client = Redis.from_url(settings.CELERY_BROKER_URL)
        services["redis"] = bool(redis_client.ping())
    except Exception:
        services["redis"] = False

    healthy = all(services.values())
    return JsonResponse(
        {
            "status": "ok" if healthy else "degraded",
            "version": settings.APP_VERSION,
            "timestamp": timezone.now().isoformat(),
            "services": services,
        },
        status=200 if healthy else 503,
    )


# Compatibilidade com o endpoint anterior.
health_check = readiness_check
