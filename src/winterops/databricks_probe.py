"""Read-only, profile-and-host-gated CLI checks with sanitized results."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from urllib.parse import urlsplit


def workspace_host(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or parsed.port not in (None, 443) or parsed.hostname.startswith("accounts.")):
        raise ValueError("Use an HTTPS workspace host without credentials, paths or query parameters")
    return "https://" + parsed.hostname.lower()


def probe(profile: str, host: str, *, include_jobs: bool = False, timeout: int = 30) -> dict:
    """Return statuses only. Never return subprocess output or credentials.

    Profiles are inventoried with --skip-validate before any remote check, so an
    unintended profile host cannot be contacted by this script. No compute is started.
    """
    if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", profile):
        raise ValueError("Supply a named CLI profile")
    target = workspace_host(host)
    if type(timeout) is not int or not 1 <= timeout <= 60:
        raise ValueError("Timeout must be an integer from 1 to 60 seconds per command")
    cli = shutil.which("databricks")
    result = {"status": "BLOCKED", "checks": {}, "reason": None}
    if cli is None:
        result["reason"] = "cli_not_installed"
        return result
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith("DATABRICKS_") or key.upper() == "DATABRICKS_CONFIG_FILE"}

    def command(*arguments):
        try:
            return subprocess.run([cli, *arguments], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=timeout,
                                  env=env, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return None

    inventory = command("auth", "profiles", "--skip-validate", "--output", "json")
    if inventory is None or inventory.returncode != 0:
        result["reason"] = "profile_inventory_unavailable"
        return result
    try:
        raw = json.loads(inventory.stdout)
        profiles = raw["profiles"] if isinstance(raw, dict) else raw
        selected = [item for item in profiles if item.get("name") == profile]
        if len(selected) != 1 or workspace_host(selected[0]["host"]) != target:
            result["reason"] = "profile_host_mismatch_or_missing"
            return result
    except (ValueError, KeyError, TypeError, AttributeError):
        result["reason"] = "profile_inventory_invalid"
        return result
    result["checks"]["profile_host_match"] = True
    env["DATABRICKS_HOST"] = target
    checks = [("current_user", ("current-user", "me")),
              ("workspace_list", ("workspace", "list", "/Workspace"))]
    if include_jobs:
        checks.append(("jobs_list", ("jobs", "list", "--limit", "1")))
    for name, arguments in checks:
        completed = command(*arguments, "--profile", profile, "--output", "json")
        result["checks"][name] = completed is not None and completed.returncode == 0
        if not result["checks"][name]:
            result["reason"] = name + "_unavailable"
            return result
    result["status"] = "PASS"
    return result
