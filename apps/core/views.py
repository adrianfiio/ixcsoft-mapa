from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from redis import Redis
from django.conf import settings

def health_check(request):
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
            "timestamp": timezone.now().isoformat(),
            "services": services,
            "version": "0.1.0",
        },
        status=200 if healthy else 503,
    )
