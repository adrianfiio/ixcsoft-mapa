from __future__ import annotations

from dataclasses import dataclass
from django.db import transaction
from django.utils import timezone

from apps.ixc_integration.models import IXCConfiguration, IXCSyncExecution
from apps.ixc_integration.repositories.customers import CustomerRepository
from apps.ixc_integration.repositories.fiber import FiberAssignmentRepository
from .configuration import build_client


@dataclass
class SyncStats:
    received: int = 0
    created: int = 0
    updated: int = 0
    failed: int = 0

    def add(self, other: "SyncStats") -> None:
        self.received += other.received
        self.created += other.created
        self.updated += other.updated
        self.failed += other.failed


class IXCSynchronizationService:
    def __init__(self, configuration: IXCConfiguration) -> None:
        self.configuration = configuration
        self.client = build_client(configuration)

    def _execution(self) -> IXCSyncExecution:
        return IXCSyncExecution.objects.create(
            configuration=self.configuration,
            started_at=timezone.now(),
        )

    def _sync_table(self, table: str, handler) -> SyncStats:
        stats = SyncStats()
        for record in self.client.iter_records(table, per_page=100):
            stats.received += 1
            try:
                with transaction.atomic():
                    _, created = handler(record)
                stats.created += int(created)
                stats.updated += int(not created)
            except Exception:
                stats.failed += 1
        return stats

    def sync_customers(self) -> SyncStats:
        return self._sync_table("cliente", CustomerRepository.upsert_customer)

    def sync_logins(self) -> SyncStats:
        return self._sync_table("radusuarios", CustomerRepository.upsert_login)

    def sync_fiber_assignments(self) -> SyncStats:
        return self._sync_table(
            "radpop_radio_cliente_fibra",
            FiberAssignmentRepository.upsert,
        )

    def run_full_sync(self) -> IXCSyncExecution:
        execution = self._execution()
        total = SyncStats()
        try:
            # A ordem é importante: fibra depende de clientes/logins existentes.
            total.add(self.sync_customers())
            total.add(self.sync_logins())
            total.add(self.sync_fiber_assignments())

            execution.records_received = total.received
            execution.records_created = total.created
            execution.records_updated = total.updated
            execution.records_failed = total.failed
            execution.status = (
                IXCSyncExecution.Status.PARTIAL
                if execution.records_failed
                else IXCSyncExecution.Status.SUCCESS
            )
            self.configuration.last_sync_status = execution.status
            self.configuration.last_sync_message = (
                f"Recebidos: {total.received}; criados: {total.created}; "
                f"atualizados: {total.updated}; falhas: {total.failed}"
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
