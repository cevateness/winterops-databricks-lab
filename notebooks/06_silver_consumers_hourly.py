# Databricks notebook source
# MAGIC %md
# MAGIC # Exact-version Silver consumers and hourly observations
# MAGIC Run from the repository's Databricks Git folder with src/ and fixtures available.
# MAGIC Default behavior prints SQL only. Applying requires prior user approval of
# MAGIC the exact workspace, source hash, expected evidence, and three view names.
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

from winterops.analytics import AnalyticsConfig, SourceScope, run_plan
from winterops.quality import QualitySnapshot

dbutils.widgets.text("source_file_sha256", "")
dbutils.widgets.dropdown("apply_views", "false", ["false", "true"])
dbutils.widgets.text("catalog", "workspace")
dbutils.widgets.text("schema", "default")

# This entrypoint intentionally targets the reported January week only.
# The fixture contains reported aggregates, not a raw dataset or a known file hash.
expected = QualitySnapshot.from_mapping(json.loads(
    (REPO_ROOT / "data/fixtures/windsor_week_2026_01_12_18_summary.json").read_text(encoding="utf-8")
))
scope = SourceScope(dbutils.widgets.get("source_file_sha256"))
config = AnalyticsConfig(scope, expected, dbutils.widgets.get("catalog"), dbutils.widgets.get("schema"))
plan = run_plan(spark, config, apply=dbutils.widgets.get("apply_views") == "true")
print(plan.render())
print("Views applied and checks passed." if dbutils.widgets.get("apply_views") == "true"
      else "DRY RUN: no Spark queries or view writes were executed.")
