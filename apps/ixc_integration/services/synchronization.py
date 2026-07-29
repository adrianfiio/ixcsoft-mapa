from __future__ import annotations

from dataclasses import dataclass
from django.db import transaction
from django.utils import timezone

from apps.ixc_integration.models import IXCConfiguration, IXCSyncExecution
from apps.ixc_integration.repositories.customers import CustomerRepository
from apps.ixc_integration.repositories.fiber import FiberAssignmentRepository
from apps.ixc_integration.repositories.map import IXCMapRepository
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
        return self._sync_table(
            "cliente",
            lambda record: CustomerRepository.upsert_customer(record, self.configuration.company),
        )

    def sync_logins(self) -> SyncStats:
        return self._sync_table(
            "radusuarios",
            lambda record: CustomerRepository.upsert_login(record, self.configuration.company),
        )

    def sync_contracts(self) -> SyncStats:
        return self._sync_table(
            "cliente_contrato",
            lambda record: CustomerRepository.upsert_contract(
                record,
                self.configuration.company,
                self.configuration.sync_active_contracts_only,
            ),
        )

    def sync_fiber_assignments(self) -> SyncStats:
        return self._sync_table(
            "radpop_radio_cliente_fibra",
            lambda record: FiberAssignmentRepository.upsert(record, self.configuration.company),
        )

    def sync_projects(self) -> SyncStats:
        return self._sync_table(
            "df_projeto",
            lambda record: IXCMapRepository.upsert_project(record, self.configuration.company),
        )

    def sync_ctos(self) -> SyncStats:
        return self._sync_table(
            "rad_caixa_ftth",
            lambda record: IXCMapRepository.upsert_cto(record, self.configuration.company),
        )

    def sync_map_elements(self) -> SyncStats:
        return self._sync_table(
            "df_elemento",
            lambda record: IXCMapRepository.upsert_element(record, self.configuration.company),
        )

    def run_full_sync(self) -> IXCSyncExecution:
        execution = self._execution()
        total = SyncStats()
        try:
            # A ordem é importante: fibra depende de clientes/logins existentes.
            if self.configuration.sync_customers:
                total.add(self.sync_customers())
            if self.configuration.sync_pppoe:
                total.add(self.sync_contracts())
                total.add(self.sync_logins())
                total.add(self.sync_fiber_assignments())
            if self.configuration.sync_projects or self.configuration.sync_ctos:
                total.add(self.sync_projects())
            if self.configuration.sync_ctos:
                total.add(self.sync_ctos())
            if self.configuration.sync_map_elements:
                total.add(self.sync_map_elements())

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
