import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07533OpticalCleanupContractTests(unittest.TestCase):
    """Contrato congelado da v0.75.33: remoção da integração experimental
    CTO/CEO/CDO-no-motor-do-Rack/Torre. Não editar depois de criado -- como
    os demais testes de contrato por versão, pode legitimamente ficar
    desatualizado em versões futuras (só test_map_v0750_static.py é
    recoletado pelo discovery contínuo)."""

    def test_cto_and_splice_box_do_not_use_open_container_workspace(self):
        editor = content("static/js/map-editor.js")
        self.assertIn(
            'const opening = ["rack", "tower"].includes(p.tipo)',
            editor,
        )
        self.assertIn(
            '? openContainerWorkspace(p.id)',
            editor,
        )
        self.assertIn(
            '? Promise.resolve(notify("Editor óptico temporariamente desativado para reconstrução."))',
            editor,
        )
        self.assertIn(
            'fusions: ["cto", "splice_box"].includes(p.tipo)',
            editor,
        )
        self.assertIn(
            '? () => notify("Editor óptico temporariamente desativado para reconstrução.")',
            editor,
        )

    def test_rack_and_tower_still_use_correct_workspace(self):
        editor = content("static/js/map-editor.js")
        master = content("static/js/map-master-suite.js")
        self.assertIn('["rack", "tower"].includes(p.tipo)', editor)
        self.assertIn("async function openContainerWorkspace(id)", master)
        self.assertIn("function ensureContainerWorkspace()", master)

    def test_map_cto_suite_js_not_included_in_templates_and_deleted(self):
        template = content("templates/map.html")
        self.assertNotIn("map-cto-suite.js", template)
        self.assertFalse((ROOT / "static/js/map-cto-suite.js").exists())

    def test_rack_tower_template_has_equipment_panel(self):
        master = content("static/js/map-master-suite.js")
        self.assertIn('<section data-panel="equipment" class="master-container-panel"></section>', master)

    def test_render_equipment_list_handles_missing_panel_safely(self):
        master = content("static/js/map-master-suite.js")
        marker = "function renderEquipmentList() {"
        start = master.index(marker)
        # Analisa só o corpo desta função (até a próxima "\n    }\n" no
        # mesmo nível de indentação de 4 espaços do módulo), pra não
        # depender de contagem manual de linhas se o arquivo mudar acima.
        end = master.index("\n    }\n", start)
        body = master[start:end]
        self.assertIn("if (!panel) {", body)
        self.assertIn("console.error(", body)
        self.assertIn("return;", body)

    def test_no_destructive_migration_added(self):
        migrations_dir = ROOT / "apps" / "network_map" / "migrations"
        for path in migrations_dir.glob("*.py"):
            if path.name == "__init__.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            source = ast.dump(tree)
            self.assertNotIn("DeleteModel", source, f"{path.name} apaga um model inteiro")
            self.assertNotIn("RemoveField", source, f"{path.name} remove um campo existente")

    def test_reset_optical_test_data_supports_dry_run_and_confirm(self):
        command = content("apps/network_map/management/commands/reset_optical_test_data.py")
        self.assertIn('"--dry-run"', command)
        self.assertIn('"--confirm"', command)
        self.assertIn("transaction.atomic()", command)
        # Nunca apaga splitters/bandejas/fusões reais de CTO/CEO/CDO.
        self.assertNotIn("CTOSplitter.objects", command[command.index("with transaction.atomic()"):])
        self.assertNotIn("SpliceTray.objects", command[command.index("with transaction.atomic()"):])
        self.assertNotIn("FiberSplice.objects", command[command.index("with transaction.atomic()"):])


if __name__ == "__main__":
    unittest.main()
