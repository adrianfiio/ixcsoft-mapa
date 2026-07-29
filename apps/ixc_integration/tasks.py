from celery import shared_task
from django.core.cache import cache

from apps.ixc_integration.models import IXCConfiguration
from apps.ixc_integration.services.synchronization import IXCSynchronizationService


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def synchronize_ixc_configuration(self, configuration_id: int) -> int:
    lock_key = f"ixc-sync-running:{configuration_id}"
    if not cache.add(lock_key, self.request.id or "running", timeout=3600):
        return 0
    try:
        configuration = IXCConfiguration.objects.get(
            pk=configuration_id,
            enabled=True,
        )
        execution = IXCSynchronizationService(configuration).run_full_sync()
        return execution.pk
    finally:
        cache.delete(lock_key)


@shared_task
def synchronize_all_ixc_configurations() -> list[int]:
    task_ids = []
    for configuration_id in IXCConfiguration.objects.filter(
        enabled=True
    ).values_list("id", flat=True):
        result = synchronize_ixc_configuration.delay(configuration_id)
        task_ids.append(result.id)
    return task_ids
