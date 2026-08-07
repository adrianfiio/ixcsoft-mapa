import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07561ContractTests(unittest.TestCase):
    def test_candidate_cables_accepts_metadata_only_linked_cables(self):
        # "+ Vincular" só grava o cabo em dio.metadata
        # (_save_linked_cable_ids) -- nenhum ContainerPortLink existe
        # ainda, e o cabo pode não ter origin/destination apontando pra
        # este container (só está sendo fundido aqui, não nasce/termina
        # aqui). Sem extra_ids, o cabo recém-vinculado sumia da lista
        # "CABOS VINCULADOS" -- confirmado ao vivo antes desta correção.
        py = content("apps/network_map/api/dio_fusion_v07537.py")
        start = py.index("def _candidate_cables")
        end = py.index("def _linked_cable_ids", start)
        block = py[start:end]
        self.assertIn("def _candidate_cables(container: NetworkElement, extra_ids=()):", block)
        self.assertIn("Q(id__in=list(extra_ids))", block)

    def test_payload_and_action_dispatcher_both_pass_linked_ids_as_extra(self):
        py = content("apps/network_map/api/dio_fusion_v07537.py")
        # _payload() (GET, alimenta a listagem)
        payload_start = py.index("def _payload(container")
        payload_end = py.index("def dio_fusion_matrix_v07537", payload_start)
        payload_block = py[payload_start:payload_end]
        self.assertIn(
            "candidates = list(_candidate_cables(container, extra_ids=linked_ids))",
            payload_block,
        )
        # dispatcher de ações (attach_cable/detach_cable/auto_fuse/create_fusion)
        # -- confirmado ao vivo: sem isso, auto_fuse batia em "No FiberCable
        # matches the given query." mesmo com o cabo já aparecendo na lista.
        view_start = py.index("def dio_fusion_matrix_v07537")
        view_end = py.index("if action ==", view_start)
        view_block = py[view_start:view_end]
        self.assertIn(
            "candidates = _candidate_cables(container, extra_ids=linked_ids)",
            view_block,
        )

    def test_fiber_row_grid_never_forces_a_fixed_minimum_that_overflows(self):
        # map-rack-maintenance-v07549.css é quem realmente vence (carrega
        # depois de map-dio-fusion-v07538.css, mesmo seletor + !important)
        # -- "repeat(12, 30px) !important" fixo nunca encolhia, cortando as
        # últimas fibras por baixo do overflow:hidden do card. Confirmado
        # ao vivo: 12/12 fibras visíveis numa linha só depois da correção.
        winning_css = content("static/css/map-rack-maintenance-v07549.css")
        self.assertIn(
            "grid-template-columns: repeat(12, 1fr) !important;",
            winning_css,
        )
        self.assertNotIn("repeat(12, 30px)", winning_css)

        base_css = content("static/css/map-dio-fusion-v07538.css")
        self.assertIn("grid-template-columns: repeat(12, 1fr);", base_css)
        self.assertIn("min-width: 0;", base_css)

    def test_version_is_current_and_no_migration(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.64")', content("config/settings.py"))
        self.assertIn('"0.83.1"', content("config/settings.py"))
        self.assertIn("v0.75.64", content("VERSIONS.md"))
        migrations_dir = ROOT / "apps" / "network_map" / "migrations"
        self.assertEqual(len(list(migrations_dir.glob("0*.py"))), 32)


if __name__ == "__main__":
    unittest.main(verbosity=2)
