import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07554ContractTests(unittest.TestCase):
    def test_access_0002_is_a_dependency_preserving_noop(self):
        py = content("apps/access/migrations/0002_add_ftth_fields.py")
        self.assertIn('("access", "0001_initial")', py)
        self.assertIn("operations = []", py)
        self.assertNotIn("migrations.AddField(", py)

    def test_access_0001_still_creates_all_twelve_ftth_fields_directly(self):
        py = content("apps/access/migrations/0001_initial.py")
        for field in (
            "ixc_customer_id", "ixc_contract_id", "onu_mac", "cto_ixc_id",
            "ftth_port", "concentrator_id", "concentrator",
            "interface_transmission", "connection_type",
            "last_connection_start", "last_connection_end", "disconnect_reason",
        ):
            self.assertIn(f"'{field}'", py)

    def test_network_map_0003_creates_company_columns_for_real(self):
        py = content("apps/network_map/migrations/0003_sync_company_fields_state.py")
        self.assertIn("database_operations=[", py)
        # antes do hotfix era "database_operations=[],\n" (lista vazia) —
        # garante que não regride pro estado antigo, só-state.
        self.assertNotIn("database_operations=[],", py)
        for model in ("fibercable", "networkelement", "networkroute"):
            self.assertIn(f'model_name="{model}"', py)
        self.assertEqual(py.count('name="company"'), 6)  # 3 database_operations + 3 state_operations

    def test_no_other_migration_lost_its_dependency_on_access_0002(self):
        for path in (
            "apps/billing/migrations/0001_initial.py",
            "apps/ixc_integration/migrations/0007_purge_nic_fibra_test_data.py",
            "apps/network_map/migrations/0007_ctosplitter_ctosplitterport.py",
        ):
            self.assertIn('"access", "0002_add_ftth_fields"', content(path))

    def test_version_is_current_and_platform_untouched(self):
        settings = content("config/settings.py")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.61")', settings)
        self.assertIn('"0.83.1"', settings)
        self.assertIn("v0.75.61", content("VERSIONS.md"))

    def test_no_new_migration_files_only_fixed_existing_ones(self):
        access_migrations = sorted(p.name for p in (ROOT / "apps/access/migrations").glob("0*.py"))
        network_map_migrations = sorted(p.name for p in (ROOT / "apps/network_map/migrations").glob("0*.py"))
        self.assertIn("0002_add_ftth_fields.py", access_migrations)
        self.assertEqual(len(access_migrations), 2)
        self.assertIn("0003_sync_company_fields_state.py", network_map_migrations)
        self.assertEqual(len(network_map_migrations), 32)


if __name__ == "__main__":
    unittest.main(verbosity=2)
