import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07563ContractTests(unittest.TestCase):
    def test_single_click_on_fused_port_does_nothing(self):
        # MAP_V07563_DIO_DOUBLE_CLICK_REMOVE_FUSION: um clique simples
        # numa porta já fundida chamava renderWorkspace() (reconstrução
        # completa do DOM) sem mudar nada de verdade -- esse reflow no
        # meio dos 2 cliques de um duplo clique impedia o navegador de
        # disparar o evento dblclick de verdade. Confirmado ao vivo:
        # 0 de 2 dblclick antes da correção, 1 de 2 depois, e a fusão
        # sendo removida de ponta a ponta (status "Fusão rompida.").
        js = content("static/js/map-dio-fusion-v07538.js")
        start = js.index('const portButton = event.target.closest("[data-dio-port-v07538]");')
        end = js.index("if (event.target.closest(\"[data-dio-auto-fuse-v07538]\"))", start)
        block = js[start:end]
        self.assertIn("if (port?.fusion) return;", block)
        self.assertNotIn("if (!port?.fusion && state.selectedFiberId)", block)
        self.assertIn("if (state.selectedFiberId) await createFusion(portId);", block)

    def test_version_is_current_and_no_migration(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.76.0")', content("config/settings.py"))
        self.assertIn('"0.84.0"', content("config/settings.py"))
        self.assertIn("v0.76.0", content("VERSIONS.md"))
        migrations_dir = ROOT / "apps" / "network_map" / "migrations"
        self.assertEqual(len(list(migrations_dir.glob("0*.py"))), 33)


if __name__ == "__main__":
    unittest.main(verbosity=2)
