from __future__ import annotations

from dataclasses import dataclass
from django.db import transaction
from django.utils import timezone

from apps.ixc_integration.models import IXCConfiguration, IXCSyncExecution
from apps.ixc_integration.repositories.customers import CustomerRepository
from .configuration import build_client


@dataclass
class SyncStats:
    received: int = 0
    created: int = 0
    updated: int = 0
    failed: int = 0


class IXCSynchronizationService:
    def __init__(self, configuration: IXCConfiguration) -> None:
        self.configuration = configuration
        self.client = build_client(configuration)

    def _execution(self) -> IXCSyncExecution:
        return IXCSyncExecution.objects.create(
            configuration=self.configuration,
            started_at=timezone.now(),
        )

    def sync_customers(self) -> SyncStats:
        stats = SyncStats()
        for record in self.client.iter_records("cliente", per_page=100):
            stats.received += 1
            try:
                with transaction.atomic():
                    _, created = CustomerRepository.upsert_customer(record)
                stats.created += int(created)
                stats.updated += int(not created)
            except Exception:
                stats.failed += 1
        return stats

    def sync_logins(self) -> SyncStats:
        stats = SyncStats()
        for record in self.client.iter_records("radusuarios", per_page=100):
            stats.received += 1
            try:
                with transaction.atomic():
                    _, created = CustomerRepository.upsert_login(record)
                stats.created += int(created)
                stats.updated += int(not created)
            except Exception:
                stats.failed += 1
        return stats

    def run_full_sync(self) -> IXCSyncExecution:
        execution = self._execution()
        try:
            customers = self.sync_customers()
            logins = self.sync_logins()
            execution.records_received = customers.received + logins.received
            execution.records_created = customers.created + logins.created
            execution.records_updated = customers.updated + logins.updated
            execution.records_failed = customers.failed + logins.failed
            execution.status = (
                IXCSyncExecution.Status.PARTIAL
                if execution.records_failed
                else IXCSyncExecution.Status.SUCCESS
            )
            self.configuration.last_sync_status = execution.status
            self.configuration.last_sync_message = (
                f"Recebidos: {execution.records_received}; "
                f"falhas: {execution.records_failed}"
            )
        except Exception as exc:
            execution.status = IXCSyncExecution.Status.FAILED
            execution.error_message = str(exc)
            self.configuration.last_sync_status = execution.status
            self.configuration.last_sync_message = str(exc)
        finally:
            now = timezone.now()
            execution.finished_at = now
            execution.save()
            self.configuration.last_sync_at = now
            self.configuration.save(
                update_fields=[
                    "last_sync_at",
                    "last_sync_status",
                    "last_sync_message",
                    "updated_at",
                ]
            )
        return execution
