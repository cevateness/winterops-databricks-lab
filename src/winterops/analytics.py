"""Bounded SQL plans and offline reference counts; importing never runs Spark."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from importlib.resources import files
from pathlib import PurePosixPath
import re
from string import Template
from typing import Iterable, Mapping

from winterops.quality import QualitySnapshot, validate_snapshot


@dataclass(frozen=True)
class SourceScope:
    """An exact source version and a half-open, timezone-naive window."""

    source_file_sha256: str
    source_file_name: str = "snowplow-2026-01-12_2026-01-18.csv"
    source_file_path: str = "/Volumes/workspace/default/winterops_raw/snowplow-2026-01-12_2026-01-18.csv"
    source_dataset: str = "windsor_snowplow_activity"
    start_unzoned: datetime = datetime(2026, 1, 12)
    end_unzoned: datetime = datetime(2026, 1, 19)

    def __post_init__(self):
        if not isinstance(self.source_file_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", self.source_file_sha256
        ):
            raise ValueError("Supply the exact lowercase, 64-character source-file SHA-256")
        for value in (self.source_file_name, self.source_file_path, self.source_dataset):
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_./-]+", value):
                raise ValueError("Source identifiers must contain only letters, digits, _, ., / or -")
        path = PurePosixPath(self.source_file_path)
        if (not self.source_file_path.startswith("/Volumes/") or ".." in path.parts
                or path.name != self.source_file_name or not path.name.endswith(".csv")
                or PurePosixPath(self.source_file_name).name != self.source_file_name):
            raise ValueError("Source must identify one CSV filename and its matching Volume path")
        for bound in (self.start_unzoned, self.end_unzoned):
            if not isinstance(bound, datetime) or bound.tzinfo is not None:
                raise ValueError("Window boundaries must be naive datetimes; no timezone inference")
            if bound.time() != datetime.min.time():
                raise ValueError("Use midnight boundaries for the source-local/naive window")
        if not timedelta(0) < self.end_unzoned - self.start_unzoned <= timedelta(days=7):
            raise ValueError("This learning slice must span more than zero and at most seven days")

    def matches(self, row: Mapping[str, object]) -> bool:
        return all(row.get(key) == getattr(self, key) for key in (
            "source_dataset", "source_file_name", "source_file_path", "source_file_sha256"
        ))


@dataclass(frozen=True)
class AnalyticsConfig:
    scope: SourceScope
    expected: QualitySnapshot
    catalog: str = "workspace"
    schema: str = "default"

    def __post_init__(self):
        for identifier in (self.catalog, self.schema):
            if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
                raise ValueError("Catalog/schema must be simple SQL identifiers")
        QualitySnapshot.from_mapping(asdict(self.expected))
        errors = validate_snapshot(self.expected)
        if errors:
            raise ValueError("Invalid expected snapshot: " + "; ".join(errors))
        if self.expected.source_file != self.scope.source_file_name:
            raise ValueError("Expected snapshot belongs to a different source filename")
        if self.expected.bronze_rows <= 0 or self.expected.valid_rows <= 0:
            raise ValueError("Refuse an empty source or a source without valid observations")

    def table(self, suffix: str) -> str:
        names = {
            "bronze": "winterops_bronze_windsor_activity",
            "silver": "winterops_silver_windsor_week_sample",
            "valid": "winterops_silver_windsor_valid",
            "quarantine": "winterops_silver_windsor_quarantine",
            "hourly": "winterops_gold_windsor_hourly_observations",
        }
        return f"`{self.catalog}`.`{self.schema}`.`{names[suffix]}`"


SILVER_TYPES = {
    "source_dataset": "string", "source_file_name": "string",
    "source_file_path": "string", "source_file_sha256": "string",
    "record_sha256": "string", "truck_id": "string",
    "event_time_unzoned": "timestamp_ntz", "latitude": "double", "longitude": "double",
    "plow_active": "boolean", "spreader_active": "boolean", "engine_active": "boolean",
    "payload_occurrences": "bigint", "has_repeated_payload": "boolean",
    "is_repeated_header": "boolean", "quality_status": "string", "quality_issues": "string",
}


def validate_silver_schema(actual: Mapping[str, str]) -> None:
    """Fail before DDL if Spark's schema differs from the existing Silver contract."""
    problems = [f"{name} must be {kind}, found {actual.get(name, 'missing')}"
                for name, kind in SILVER_TYPES.items() if actual.get(name) != kind]
    if problems:
        raise ValueError("Silver schema mismatch: " + "; ".join(problems))


@dataclass(frozen=True)
class SqlPlan:
    preflight: tuple[str, ...]
    views: tuple[str, ...]
    postflight: tuple[str, ...]

    def render(self) -> str:
        sections = []
        for label, statements in (("PREFLIGHT: all must pass before DDL", self.preflight),
                                  ("EXPLICIT VIEW PUBLICATION", self.views),
                                  ("POSTFLIGHT: reconciliation", self.postflight)):
            sections.append("-- " + label + "\n" + ";\n\n".join(statements) + ";")
        return "\n\n".join(sections) + "\n"


def build_plan(config: AnalyticsConfig) -> SqlPlan:
    """Render reviewed templates; no auth, network, Spark, or database writes."""
    scope = config.scope
    substitutions = {name + "_table": config.table(name) for name in (
        "bronze", "silver", "valid", "quarantine", "hourly"
    )}
    # Values were restricted above; none can inject SQL quotes, comments or statements.
    substitutions["source_filter"] = " AND ".join(
        f"{name} = '{getattr(scope, name)}'" for name in (
            "source_dataset", "source_file_name", "source_file_path", "source_file_sha256"
        )
    )
    substitutions["window_filter"] = (
        f"event_time_unzoned >= TIMESTAMP_NTZ '{scope.start_unzoned:%Y-%m-%d %H:%M:%S}' "
        f"AND event_time_unzoned < TIMESTAMP_NTZ '{scope.end_unzoned:%Y-%m-%d %H:%M:%S}'"
    )
    for name in ("bronze_rows", "silver_rows", "header_rows", "valid_rows", "other_invalid_rows",
                 "distinct_truck_ids", "plow_active_observations", "spreader_active_observations"):
        substitutions[name] = str(getattr(config.expected, name))

    def sql(filename):
        template = files("winterops").joinpath("sql", filename).read_text(encoding="utf-8")
        return Template(template).substitute(substitutions).strip()

    return SqlPlan(
        preflight=(sql("analytics_preflight.sql"), sql("analytics_payload_checks.sql")),
        views=tuple(sql(name) for name in ("silver_valid.sql", "silver_quarantine.sql", "gold_hourly.sql")),
        postflight=(sql("analytics_postflight.sql"),),
    )


def run_plan(spark, config: AnalyticsConfig, *, apply: bool = False) -> SqlPlan:
    """Dry-run by default. Explicit apply creates views, never source tables/jobs.

    Call only after workspace approval. Stop at the first failed check; DDL for
    multiple views is not transactional. Rerun after resolving a partial failure.
    """
    if type(apply) is not bool:
        raise TypeError("apply must be a Boolean")
    plan = build_plan(config)
    if not apply:
        return plan
    actual = {field.name: field.dataType.simpleString()
              for field in spark.table(config.table("silver")).schema.fields}
    validate_silver_schema(actual)
    for statement in plan.preflight:
        spark.sql(statement).collect()  # Force assertions before any view DDL.
    for statement in plan.views:
        spark.sql(statement).collect()
    for statement in plan.postflight:
        spark.sql(statement).collect()
    return plan


def hourly_observations(rows: Iterable[Mapping[str, object]], scope: SourceScope) -> list[dict]:
    """Offline reference for projected Silver rows; preserves duplicate observations.

    This is not Spark execution or a parser for the original Windsor telemetry.
    """
    groups = defaultdict(list)
    for row in rows:
        if not scope.matches(row):
            continue
        quality = row.get("quality_status")
        if quality not in {"VALID", "HEADER", "INVALID"}:
            raise ValueError("Unknown/null Silver quality classification")
        if quality != "VALID":
            continue
        event = row.get("event_time_unzoned")
        if isinstance(event, str):
            event = datetime.fromisoformat(event)
        if not isinstance(event, datetime) or event.tzinfo is not None:
            raise ValueError("VALID event_time_unzoned must be a naive datetime")
        if not scope.start_unzoned <= event < scope.end_unzoned:
            raise ValueError("VALID observation lies outside the approved window")
        if not isinstance(row.get("truck_id"), str) or not row["truck_id"].strip():
            raise ValueError("VALID observation is missing truck_id")
        for name in ("plow_active", "spreader_active", "has_repeated_payload"):
            if type(row.get(name)) is not bool:
                raise ValueError(f"VALID {name} must be Boolean")
        groups[event.replace(minute=0, second=0, microsecond=0)].append(row)
    return [{
        "source_local_naive_hour": hour,
        "observation_count": len(values),
        "plow_active_observation_count": sum(row["plow_active"] for row in values),
        "spreader_active_observation_count": sum(row["spreader_active"] for row in values),
        "distinct_truck_count": len({row["truck_id"] for row in values}),
        "repeated_payload_observation_count": sum(row["has_repeated_payload"] for row in values),
    } for hour, values in sorted(groups.items())]
