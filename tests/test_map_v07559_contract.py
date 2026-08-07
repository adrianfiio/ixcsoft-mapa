import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def content(path):
    return (ROOT / path).read_text(encoding="utf-8")


class MapV07559ContractTests(unittest.TestCase):
    def test_auto_fuse_label_forced_white_and_visible(self):
        css = content("static/css/map-dio-fusion-v07538.css")
        self.assertIn("[data-dio-auto-fuse-v07538] span {", css)
        start = css.index("[data-dio-auto-fuse-v07538] span {")
        end = css.index("}", start)
        block = css[start:end]
        self.assertIn("display: inline !important;", block)
        self.assertIn("color: #fff !important;", block)

    def test_version_is_current_and_no_migration(self):
        self.assertIn('MAP_VERSION = os.getenv("MAP_VERSION", "0.75.61")', content("config/settings.py"))
        self.assertIn('"0.83.1"', content("config/settings.py"))
        self.assertIn("v0.75.61", content("VERSIONS.md"))
        migrations_dir = ROOT / "apps" / "network_map" / "migrations"
        self.assertEqual(len(list(migrations_dir.glob("0*.py"))), 32)


if __name__ == "__main__":
    unittest.main(verbosity=2)
