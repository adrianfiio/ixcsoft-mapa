from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

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
    for configuration in IXCConfiguration.objects.filter(enabled=True):
        due_at = (
            configuration.last_sync_at
            + timedelta(minutes=configuration.sync_interval_minutes)
            if configuration.last_sync_at
            else None
        )
        if due_at and due_at > timezone.now():
            continue
        configuration_id = configuration.id
        result = synchronize_ixc_configuration.delay(configuration_id)
        task_ids.append(result.id)
    return task_ids


@shared_task
def synchronize_ixc_pppoe_statuses() -> list[int]:
    execution_ids = []
    for configuration in IXCConfiguration.objects.filter(enabled=True, sync_pppoe=True):
        lock_key = f"ixc-sync-running:{configuration.id}"
        if not cache.add(lock_key, "running", timeout=290):
            continue
        try:
            execution = IXCSynchronizationService(configuration).run_pppoe_status_sync()
            execution_ids.append(execution.id)
        finally:
            cache.delete(lock_key)
    return execution_ids
