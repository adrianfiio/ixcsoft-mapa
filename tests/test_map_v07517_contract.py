from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MapV07517ContractTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_versions(self):
        settings = self.read("config/settings.py")
        compose = self.read("docker-compose.yml")
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.17")', settings)
        self.assertIn('MAP_VERSION: ${MAP_VERSION:-0.75.17}', compose)
        self.assertIn("| Mapa | v0.75.17 |", self.read("README.md"))
        self.assertIn("| Mapa | v0.75.17 |", self.read("VERSIONS.md"))

    def test_ptp_company_id_fixed(self):
        backend = self.read("apps/network_map/api/ptp_links.py")
        self.assertIn("MAP_V07517_PTP_COMPANY_ID_FIX", backend)
        # não deve mais existir nenhum acesso direto a .company_id numa
        # instância de ContainerEquipmentPort/ContainerPortLink
        self.assertNotIn("source.company_id", backend)
        self.assertNotIn("destination.company_id", backend)
        self.assertNotIn("link.company_id", backend)
        self.assertIn("source.equipment.company_id", backend)
        self.assertIn("link.container.company_id", backend)
        self.assertIn("equipment__company_id=source.equipment.company_id", backend)

    def test_dio_conflict_message_is_specific(self):
        backend = self.read("apps/network_map/api/views.py")
        self.assertIn("MAP_V07517_DIO_CONFLICT_MESSAGE", backend)
        self.assertIn("role_label", backend)
        self.assertNotIn('{"detail": "Uma das portas já está em uso."}', backend)

    def test_no_migrations(self):
        release = self.read("docs/releases/map/map-v0.75.17.md")
        self.assertIn("Sem migrations", release)


if __name__ == "__main__":
    unittest.main()
