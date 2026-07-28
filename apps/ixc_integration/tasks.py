from celery import shared_task

from apps.ixc_integration.models import IXCConfiguration
from apps.ixc_integration.services.synchronization import IXCSynchronizationService


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def synchronize_ixc_configuration(self, configuration_id: int) -> int:
    configuration = IXCConfiguration.objects.get(
        pk=configuration_id,
        enabled=True,
    )
    execution = IXCSynchronizationService(configuration).run_full_sync()
    return execution.pk


@shared_task
def synchronize_all_ixc_configurations() -> list[int]:
    task_ids = []
    for configuration_id in IXCConfiguration.objects.filter(
        enabled=True
    ).values_list("id", flat=True):
        result = synchronize_ixc_configuration.delay(configuration_id)
        task_ids.append(result.id)
    return task_ids
