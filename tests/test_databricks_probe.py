"""Mocked CLI tests; never authenticate or contact a Databricks workspace."""
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from winterops.databricks_probe import probe, workspace_host


class ProbeTests(unittest.TestCase):
    HOST = "https://workspace.example"

    def completed(self, content=None, code=0):
        return SimpleNamespace(returncode=code, stdout=json.dumps(content), stderr="SENSITIVE ERROR")

    def inventory(self, host=HOST):
        return self.completed({"profiles": [{"name": "winterops", "host": host}]})

    def test_host_rejects_credentials_paths_accounts_and_query(self):
        for value in ("http://workspace.example", "https://user:secret@workspace.example",
                      "https://workspace.example/sql", "https://workspace.example?token=secret",
                      "https://accounts.cloud.databricks.com", "https://workspace.example:8443"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                workspace_host(value)
        self.assertEqual(workspace_host("https://WORKSPACE.example/"), self.HOST)

    @patch("winterops.databricks_probe.shutil.which", return_value=None)
    def test_no_cli_is_blocked(self, _):
        self.assertEqual(probe("winterops", self.HOST)["reason"], "cli_not_installed")

    @patch("winterops.databricks_probe.shutil.which", return_value="databricks")
    @patch("winterops.databricks_probe.subprocess.run")
    def test_mismatched_profile_stops_before_remote_commands(self, run, _):
        run.return_value = self.inventory("https://other.example")
        self.assertEqual(probe("winterops", self.HOST)["reason"], "profile_host_mismatch_or_missing")
        self.assertEqual(run.call_count, 1)
        self.assertIn("--skip-validate", run.call_args.args[0])

    @patch("winterops.databricks_probe.shutil.which", return_value="databricks")
    @patch("winterops.databricks_probe.subprocess.run")
    def test_default_checks_are_read_only_scoped_and_hide_output(self, run, _):
        run.side_effect = [self.inventory(), self.completed({"token": "SENSITIVE"}), self.completed()]
        with patch.dict("os.environ", {"DATABRICKS_TOKEN": "SENSITIVE", "DATABRICKS_HOST": "wrong"}):
            result = probe("winterops", self.HOST)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(run.call_count, 3)
        for call in run.call_args_list:
            self.assertNotIn("DATABRICKS_TOKEN", call.kwargs["env"])
            self.assertLessEqual(call.kwargs["timeout"], 60)
        self.assertEqual(run.call_args_list[1].args[0][1:3], ["current-user", "me"])
        self.assertEqual(run.call_args_list[2].args[0][1:4], ["workspace", "list", "/Workspace"])
        self.assertNotIn("SENSITIVE", json.dumps(result))

    @patch("winterops.databricks_probe.shutil.which", return_value="databricks")
    @patch("winterops.databricks_probe.subprocess.run")
    def test_failure_is_sanitized_and_skips_remaining_checks(self, run, _):
        run.side_effect = [self.inventory(), self.completed({"token": "SENSITIVE"}, code=1)]
        result = probe("winterops", self.HOST, include_jobs=True)
        self.assertEqual(result["reason"], "current_user_unavailable")
        self.assertEqual(run.call_count, 2)
        self.assertNotIn("SENSITIVE", json.dumps(result))

    @patch("winterops.databricks_probe.shutil.which", return_value="databricks")
    @patch("winterops.databricks_probe.subprocess.run")
    def test_timeout_is_blocked(self, run, _):
        run.side_effect = [self.inventory(), subprocess.TimeoutExpired("databricks", 30)]
        self.assertEqual(probe("winterops", self.HOST)["reason"], "current_user_unavailable")

    @patch("winterops.databricks_probe.shutil.which", return_value="databricks")
    @patch("winterops.databricks_probe.subprocess.run")
    def test_jobs_probe_is_explicit_and_limited(self, run, _):
        run.side_effect = [self.inventory(), self.completed(), self.completed(), self.completed()]
        self.assertEqual(probe("winterops", self.HOST, include_jobs=True)["status"], "PASS")
        self.assertEqual(run.call_args.args[0][1:5], ["jobs", "list", "--limit", "1"])

    @patch("winterops.databricks_probe.shutil.which", return_value="databricks")
    @patch("winterops.databricks_probe.subprocess.run")
    def test_bad_inventory_never_runs_remote_checks(self, run, _):
        for content in ({"unexpected": []}, None, ["invalid entry"]):
            with self.subTest(content=content):
                run.reset_mock()
                run.return_value = self.completed(content)
                self.assertEqual(probe("winterops", self.HOST)["status"], "BLOCKED")
                self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
