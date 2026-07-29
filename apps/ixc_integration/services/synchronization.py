from __future__ import annotations

from dataclasses import dataclass
from django.db import transaction
from django.utils import timezone

from apps.ixc_integration.models import IXCConfiguration, IXCSyncExecution
from apps.ixc_integration.repositories.customers import CustomerRepository
from apps.ixc_integration.repositories.fiber import FiberAssignmentRepository
from apps.ixc_integration.repositories.map import IXCMapRepository
from apps.access.services.ixc_sync import sync_radusuarios
from apps.access.models import AccessPoint
from apps.ixc_integration.models import IXCContract, IXCCustomer
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

    def _update_progress(self, stage: str, stats: SyncStats | None = None, errors=None) -> None:
        self.execution.current_stage = stage
        if stats is not None:
            results = dict(self.execution.stage_results)
            results[stage] = {
                "received": stats.received,
                "created": stats.created,
                "updated": stats.updated,
                "failed": stats.failed,
                "errors": (errors or [])[:5],
            }
            self.execution.stage_results = results
            self.execution.records_received = sum(item["received"] for item in results.values())
            self.execution.records_created = sum(item["created"] for item in results.values())
            self.execution.records_updated = sum(item["updated"] for item in results.values())
            self.execution.records_failed = sum(item["failed"] for item in results.values())
        self.execution.save()

    def _sync_table(self, table: str, handler, stage: str) -> SyncStats:
        stats = SyncStats()
        errors = []
        self._update_progress(stage)
        for record in self.client.iter_records(table, per_page=100):
            stats.received += 1
            try:
                with transaction.atomic():
                    _, created = handler(record)
                stats.created += int(created)
                stats.updated += int(not created)
            except Exception as exc:
                stats.failed += 1
                if len(errors) < 5:
                    errors.append(str(exc))
            if stats.received % 100 == 0:
                self._update_progress(stage, stats, errors)
        self._update_progress(stage, stats, errors)
        return stats

    def sync_customers(self) -> SyncStats:
        return self._sync_table(
            "cliente",
            lambda record: CustomerRepository.upsert_customer(record, self.configuration.company),
            "Clientes",
        )

    def sync_logins(self) -> SyncStats:
        return self._sync_table(
            "radusuarios",
            lambda record: CustomerRepository.upsert_login(record, self.configuration.company),
            "Logins PPPoE",
        )

    def sync_contracts(self) -> SyncStats:
        return self._sync_table(
            "cliente_contrato",
            lambda record: CustomerRepository.upsert_contract(
                record,
                self.configuration.company,
                self.configuration.sync_active_contracts_only,
            ),
            "Contratos ativos",
        )

    def sync_fiber_assignments(self) -> SyncStats:
        return self._sync_table(
            "radpop_radio_cliente_fibra",
            lambda record: FiberAssignmentRepository.upsert(record, self.configuration.company),
            "Vínculos de fibra/ONU",
        )

    def sync_projects(self) -> SyncStats:
        return self._sync_table(
            "df_projeto",
            lambda record: IXCMapRepository.upsert_project(record, self.configuration.company),
            "Projetos",
        )

    def sync_ctos(self) -> SyncStats:
        return self._sync_table(
            "rad_caixa_ftth",
            lambda record: IXCMapRepository.upsert_cto(record, self.configuration.company),
            "CTOs e caixas",
        )

    def sync_map_elements(self) -> SyncStats:
        return self._sync_table(
            "df_elemento",
            lambda record: IXCMapRepository.upsert_element(record, self.configuration.company),
            "Elementos do mapa",
        )

    def sync_access_points(self) -> SyncStats:
        stage = "Acessos PPPoE ativos"
        self._update_progress(stage)
        result = sync_radusuarios(self.client, self.configuration.company)
        stats = SyncStats(
            received=sum(result.values()),
            created=result["created"],
            updated=result["updated"] + result["deleted"] + result["ignored"],
        )
        if self.configuration.sync_active_contracts_only:
            active_contract_ids = IXCContract.objects.filter(
                company=self.configuration.company,
                active=True,
            ).values_list("ixc_contract_id", flat=True)
            AccessPoint.objects.filter(
                company=self.configuration.company,
                source="ixc",
            ).exclude(ixc_contract_id__in=active_contract_ids).delete()
        self._update_progress(stage, stats)
        return stats

    def run_full_sync(self) -> IXCSyncExecution:
        execution = self._execution()
        self.execution = execution
        total = SyncStats()
        try:
            # A ordem é importante: fibra depende de clientes/logins existentes.
            if self.configuration.sync_customers:
                total.add(self.sync_customers())
            if self.configuration.sync_pppoe:
                total.add(self.sync_contracts())
                total.add(self.sync_logins())
                total.add(self.sync_fiber_assignments())
                total.add(self.sync_access_points())
            if self.configuration.sync_projects or self.configuration.sync_ctos:
                total.add(self.sync_projects())
            if self.configuration.sync_ctos:
                total.add(self.sync_ctos())
            if self.configuration.sync_map_elements:
                total.add(self.sync_map_elements())
            if self.configuration.sync_active_contracts_only:
                IXCCustomer.objects.filter(company=self.configuration.company).exclude(
                    contracts__active=True
                ).delete()

            execution.records_received = total.received
            execution.records_created = total.created
            execution.records_updated = total.updated
            execution.records_failed = total.failed
            execution.status = (
                IXCSyncExecution.Status.PARTIAL
                if execution.records_failed
                else IXCSyncExecution.Status.SUCCESS
            )
            execution.current_stage = "Concluído"
            self.configuration.last_sync_status = execution.status
            self.configuration.last_sync_message = (
                f"Recebidos: {total.received}; criados: {total.created}; "
                f"atualizados: {total.updated}; falhas: {total.failed}"
            )
        except Exception as exc:
            execution.status = IXCSyncExecution.Status.FAILED
            execution.error_message = str(exc)
            execution.current_stage = "Falha"
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
