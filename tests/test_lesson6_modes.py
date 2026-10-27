"""Exercise notebook mode dispatch with fake widgets/Spark; never contacts Databricks."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_analytics

ROOT = Path(__file__).resolve().parents[1]


class Lesson6ModeTests(unittest.TestCase):
    def run_notebook(self, values):
        values = dict(values, source_file_sha256="a" * 64)
        widgets = SimpleNamespace(
            text=lambda name, default: values.setdefault(name, default),
            dropdown=lambda name, default, choices: values.setdefault(name, default),
            get=values.__getitem__,
        )
        engine = test_analytics.FakeSpark()
        output = io.StringIO()
        code = (ROOT / "notebooks/06_silver_consumers_hourly.py").read_text(encoding="utf-8")
        with patch("pathlib.Path.cwd", return_value=ROOT), redirect_stdout(output):
            exec(compile(code, "06_silver_consumers_hourly.py", "exec"),
                 {"spark": engine, "dbutils": SimpleNamespace(widgets=widgets)})
        return engine, output.getvalue()

    def test_default_render_ignores_a_saved_legacy_apply_widget(self):
        engine, output = self.run_notebook({"apply_views": "true"})
        self.assertEqual(engine.statements, [])
        self.assertEqual(engine.views, {})
        self.assertIn("DRY RUN", output)

    def test_validate_mode_runs_queries_without_ddl(self):
        engine, output = self.run_notebook({"mode": "validate", "apply_views": "true"})
        self.assertEqual(len(engine.statements), 3)
        self.assertEqual(engine.views, {})
        self.assertNotIn("CREATE OR REPLACE VIEW", output)
        self.assertIn("Read-only validation passed", output)

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            self.run_notebook({"mode": "unexpected"})

    def test_cli_validation_only_emits_no_publication_statements(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts/render_analytics_sql.py"),
             "--source-file-sha256", "a" * 64,
             "--expected-summary", str(ROOT / "data/fixtures/windsor_week_2026_01_12_18_summary.json"),
             "--validation-only"], capture_output=True, text=True, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("READ-ONLY: candidate", completed.stdout)
        self.assertNotIn("CREATE OR REPLACE VIEW", completed.stdout)


if __name__ == "__main__":
    unittest.main()
