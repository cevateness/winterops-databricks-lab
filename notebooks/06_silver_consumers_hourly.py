# Databricks notebook source
# MAGIC %md
# MAGIC # Exact-version Silver consumers and hourly observations
# MAGIC Run from the repository's Databricks Git folder with src/ and fixtures available.
# MAGIC Default behavior prints SQL only. Applying requires prior user approval of
# MAGIC the exact workspace, source hash, expected evidence, and three view names.
# MAGIC `mode=validate` runs source and candidate-consumer checks using read-only
# MAGIC queries; it does not create temporary or persistent views. It still uses compute.
# MAGIC This notebook never rewrites Bronze/Silver or creates/schedules a job.

# COMMAND ----------
from pathlib import Path
import json
import sys

for candidate in (Path.cwd(), *Path.cwd().parents):
    if (candidate / "src" / "winterops" / "analytics.py").is_file():
        sys.path.insert(0, str(candidate / "src"))
        REPO_ROOT = candidate
        break
else:
    raise RuntimeError("Open the repository Git folder so src/ and aggregate fixtures are available")

from winterops.analytics import AnalyticsConfig, SourceScope, run_plan, validate_plan
from winterops.quality import QualitySnapshot

dbutils.widgets.text("source_file_sha256", "")
dbutils.widgets.dropdown("mode", "render", ["render", "validate", "apply"])
dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "default")

# This entrypoint intentionally targets the reported January week only.
# The fixture contains reported aggregates, not a raw dataset or a known file hash.
expected = QualitySnapshot.from_mapping(json.loads(
    (REPO_ROOT / "data/fixtures/windsor_week_2026_01_12_18_summary.json").read_text(encoding="utf-8")
))
scope = SourceScope(dbutils.widgets.get("source_file_sha256"))
config = AnalyticsConfig(scope, expected, dbutils.widgets.get("catalog"), dbutils.widgets.get("schema"))
# A previously saved apply_views widget is deliberately ignored; use the explicit mode.
mode = dbutils.widgets.get("mode")
if mode not in {"render", "validate", "apply"}:
    raise ValueError("mode must be render, validate or apply")
if mode == "validate":
    plan = validate_plan(spark, config)
else:
    plan = run_plan(spark, config, apply=mode == "apply")
print(plan.render(read_only=mode == "validate"))
print({"render": "DRY RUN: no Spark queries or view writes were executed.",
       "validate": "Read-only validation passed; no views were created or replaced.",
       "apply": "Views applied and checks passed."}[mode])
