"""Read-only Gold analytical products and synthetic/offline reference calculations.

Rendering/importing never executes SQL, authenticates, or creates objects. Public
outputs contain aggregates, never truck identifiers, record hashes or trajectories.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from importlib.resources import files
import re
from string import Template
from typing import Iterable, Mapping

from winterops.analytics import AnalyticsConfig, SourceScope, hourly_observations, validate_silver_schema

PRODUCT_NAMES = (
    "daily_activity", "equipment_hourly", "equipment_daily", "fleet_overview",
    "fleet_daily_participation", "fleet_observation_frequency",
    "fleet_gap_distribution", "fleet_reporting_days",
)
GOLD_TYPES = {
    "source_dataset": "string", "source_file_name": "string", "source_file_sha256": "string",
    "source_local_naive_hour": "timestamp_ntz", "observation_count": "bigint",
    "plow_active_observation_count": "bigint", "spreader_active_observation_count": "bigint",
    "distinct_truck_count": "bigint", "repeated_payload_observation_count": "bigint",
}


def validate_product_schemas(valid: Mapping[str, str], gold: Mapping[str, str]) -> None:
    """Metadata-only schema gate for a separately approved runtime caller."""
    validate_silver_schema(valid)
    if any(gold.get(name) != kind for name, kind in GOLD_TYPES.items()):
        raise ValueError("Published Gold schema does not match required NTZ/count types")


@dataclass(frozen=True)
class DiagnosticSettings:
    """Review thresholds, not established observation cadence or fleet capacity."""

    long_gap_seconds: int = 1800
    dense_hour_observations: int = 1000

    def __post_init__(self):
        if type(self.long_gap_seconds) is not int or not 1 <= self.long_gap_seconds <= 604800:
            raise ValueError("long_gap_seconds must be an integer in [1, 604800]")
        if type(self.dense_hour_observations) is not int or not 1 <= self.dense_hour_observations <= 1000000000:
            raise ValueError("dense_hour_observations must be an integer in [1, 1000000000]")


def ntz_clock_index_sql(column: str) -> str:
    """Calendar-field index, in microseconds; not an instant or Unix timestamp.

    DATE differences and string fields deliberately avoid TIMESTAMP coercion by
    timestampdiff/unix functions when the source timezone is unknown.
    """
    if not re.fullmatch(r"[a-z_]+", column):
        raise ValueError("Clock expression requires a fixed column identifier")
    text = f"CAST({column} AS STRING)"
    return (
        f"(CAST(datediff(CAST(substring({text}, 1, 10) AS DATE), DATE '2000-01-01') AS BIGINT) * 86400000000"
        f" + CAST(substring({text}, 12, 2) AS BIGINT) * 3600000000"
        f" + CAST(substring({text}, 15, 2) AS BIGINT) * 60000000"
        f" + CAST(CAST(substring({text}, 18, 9) AS DECIMAL(8,6)) * 1000000 AS BIGINT))"
    )


@dataclass(frozen=True)
class ProductsPlan:
    preflight: tuple[str, ...]
    queries: tuple[tuple[str, str], ...]

    def query(self, name: str) -> str:
        try:
            return dict(self.queries)[name]
        except KeyError:
            raise ValueError("Unknown analytical product") from None

    def render(self, product: str | None = None) -> str:
        selected = self.queries if product is None else ((product, self.query(product)),)
        sections = [("SOURCE/PER-HOUR GUARD", self.preflight[0]),
                    ("PRODUCT RECONCILIATION", self.preflight[1]), *selected]
        return "-- READ-ONLY PLAN; requires separate workspace/compute approval.\n\n" + "\n\n".join(
            "-- " + name + "\n" + sql + ";" for name, sql in sections
        ) + "\n"


def build_products(config: AnalyticsConfig, settings: DiagnosticSettings = DiagnosticSettings()) -> ProductsPlan:
    """Build SELECT-only queries over the existing published valid and hourly views."""
    scope = config.scope
    substitutions = {
        "valid_table": config.table("valid"), "gold_table": config.table("hourly"),
        "valid_filter": " AND ".join(f"{key} = '{getattr(scope, key)}'" for key in
            ("source_dataset", "source_file_name", "source_file_path", "source_file_sha256")),
        # Gold has no file-path column. Path binding is checked through valid Silver.
        "gold_filter": " AND ".join(f"{key} = '{getattr(scope, key)}'" for key in
            ("source_dataset", "source_file_name", "source_file_sha256")),
        "start": scope.start_unzoned.strftime("%Y-%m-%d %H:%M:%S"),
        "end": scope.end_unzoned.strftime("%Y-%m-%d %H:%M:%S"),
        "clock_index": ntz_clock_index_sql("event_time_unzoned"),
        "long_gap_seconds": str(settings.long_gap_seconds),
        "dense_hour_observations": str(settings.dense_hour_observations),
        "valid_rows": str(config.expected.valid_rows),
        "valid_trucks": str(config.expected.distinct_truck_ids),
        "plow_rows": str(config.expected.plow_active_observations),
        "spreader_rows": str(config.expected.spreader_active_observations),
    }

    def template(name):
        return Template(files("winterops").joinpath("sql", name).read_text(encoding="utf-8")).substitute(substitutions).strip()

    sources = template("products_sources.sql")
    fleet = template("products_fleet.sql")
    composition = """COUNT(*) AS observation_count,
       COUNT_IF(plow_active AND NOT spreader_active) AS plow_only_observations,
       COUNT_IF(spreader_active AND NOT plow_active) AS spreader_only_observations,
       COUNT_IF(plow_active AND spreader_active) AS both_active_observations,
       COUNT_IF(NOT plow_active AND NOT spreader_active) AS neither_active_observations,
       COUNT_IF(NOT engine_active) AS engine_off_observations,
       COUNT_IF(NOT engine_active AND (plow_active OR spreader_active)) AS engine_off_with_equipment_flag_observations"""
    bodies = {
        "daily_activity": """SELECT CAST(source_local_naive_hour AS DATE) AS source_local_naive_day,
       SUM(observation_count) AS observation_count,
       SUM(plow_active_observation_count) AS plow_active_observations,
       SUM(spreader_active_observation_count) AS spreader_active_observations,
       COUNT(*) AS hours_containing_telemetry,
       MAX(distinct_truck_count) AS maximum_hourly_distinct_truck_identifiers
FROM _gold GROUP BY CAST(source_local_naive_hour AS DATE) ORDER BY source_local_naive_day""",
        "equipment_hourly": "SELECT source_local_naive_hour, " + composition + "\nFROM _valid GROUP BY source_local_naive_hour ORDER BY source_local_naive_hour",
        "equipment_daily": "SELECT source_local_naive_day, " + composition + "\nFROM _valid GROUP BY source_local_naive_day ORDER BY source_local_naive_day",
        "fleet_overview": """SELECT COUNT(*) AS observed_identifier_count,
       COALESCE(SUM(observation_count), 0) AS observation_count,
       COALESCE(SUM(reporting_days), 0) AS observed_identifier_day_pairs,
       MIN(observation_count) AS minimum_observations_per_identifier,
       MAX(observation_count) AS maximum_observations_per_identifier,
       AVG(observation_count) AS mean_observations_per_identifier,
       COUNT(CASE WHEN observation_count = 1 THEN 1 END) AS singleton_identifier_count,
       COUNT(CASE WHEN observation_count > 1 AND distinct_timestamps = 1 THEN 1 END) AS constant_timestamp_identifier_count,
       COUNT(CASE WHEN conflict_timestamps > 0 THEN 1 END) AS same_timestamp_conflict_identifier_count,
       COALESCE(SUM(conflict_timestamps), 0) AS conflicting_identifier_timestamp_groups,
       COUNT(CASE WHEN long_gap_pairs > 0 THEN 1 END) AS identifiers_with_long_gaps,
       COALESCE(SUM(gap_pairs), 0) AS consecutive_timestamp_pairs,
       COALESCE(SUM(zero_gap_pairs), 0) AS zero_gap_pairs,
       COALESCE(SUM(long_gap_pairs), 0) AS long_gap_pairs,
       MIN(minimum_positive_gap_seconds) AS minimum_positive_source_clock_gap_seconds,
       MAX(maximum_gap_seconds) AS maximum_source_clock_gap_seconds,
       COUNT(CASE WHEN dense_hours > 0 THEN 1 END) AS dense_reporting_identifier_count,
       COALESCE(SUM(dense_hours), 0) AS dense_identifier_hour_count,
       MAX(peak_hour_observations) AS peak_identifier_hour_observation_count,
       (SELECT COUNT(*) FROM _payloads WHERE n > 1) AS repeated_payload_group_count,
       (SELECT COALESCE(SUM(CASE WHEN n > 1 THEN n ELSE 0 END), 0) FROM _payloads) AS repeated_payload_observations,
       (SELECT COALESCE(SUM(n - 1), 0) FROM _payloads) AS excess_payload_observations,
       (SELECT COUNT(*) FROM _payloads WHERE identifier_count > 1 OR timestamp_count > 1) AS payload_identity_conflict_groups,
       (SELECT COUNT(*) FROM _valid WHERE truck_id <> trim(truck_id)) AS whitespace_identifier_observations
FROM _identifiers""",
        "fleet_daily_participation": """SELECT source_local_naive_day, COUNT(DISTINCT truck_id) AS observed_identifier_count,
       COUNT(*) AS observation_count, COUNT(DISTINCT source_local_naive_hour) AS hours_containing_telemetry
FROM _valid GROUP BY source_local_naive_day ORDER BY source_local_naive_day""",
        "fleet_observation_frequency": """SELECT frequency_band, COUNT(*) AS identifier_count,
       SUM(observation_count) AS observation_count
FROM (SELECT observation_count,
      CASE WHEN observation_count = 1 THEN '01_single'
           WHEN observation_count <= 10 THEN '02_2_to_10'
           WHEN observation_count <= 100 THEN '03_11_to_100'
           WHEN observation_count <= 1000 THEN '04_101_to_1000'
           ELSE '05_1001_plus' END AS frequency_band FROM _identifiers)
GROUP BY frequency_band ORDER BY frequency_band""",
        "fleet_gap_distribution": f"""SELECT gap_band, COUNT(*) AS consecutive_timestamp_pairs,
       COUNT(DISTINCT truck_id) AS identifiers_in_band,
       MIN(source_clock_gap_seconds) AS minimum_source_clock_gap_seconds,
       MAX(source_clock_gap_seconds) AS maximum_source_clock_gap_seconds
FROM (SELECT truck_id, source_clock_gap_seconds,
      CASE WHEN source_clock_gap_seconds = 0 THEN '01_zero'
           WHEN source_clock_gap_seconds <= {settings.long_gap_seconds} THEN '02_positive_within_review_threshold'
           ELSE '03_above_review_threshold' END AS gap_band FROM _gaps)
GROUP BY gap_band ORDER BY gap_band""",
        "fleet_reporting_days": """SELECT reporting_days AS days_with_observations,
       COUNT(*) AS identifier_count, SUM(observation_count) AS observation_count
FROM _identifiers GROUP BY reporting_days ORDER BY reporting_days""",
    }
    queries = tuple((name, "WITH " + sources + (",\n" + fleet if name in {
        "fleet_overview", "fleet_observation_frequency", "fleet_gap_distribution", "fleet_reporting_days"} else "")
        + "\n" + bodies[name]) for name in PRODUCT_NAMES)
    substitutions.update({"q_" + name: body.rsplit(" ORDER BY", 1)[0] for name, body in bodies.items()})
    return ProductsPlan(("WITH " + sources + ",\n" + template("products_guard.sql"),
                         "WITH " + sources + ",\n" + fleet + ",\n" + template("products_checks.sql")), queries)


def _selected_rows(rows: Iterable[Mapping[str, object]], scope: SourceScope) -> list[dict]:
    selected = []
    for original in rows:
        if not scope.matches(original):
            continue
        row = dict(original)
        event = row.get("event_time_unzoned")
        if isinstance(event, str):
            try:
                event = datetime.fromisoformat(event)
            except ValueError:
                raise ValueError("Invalid source-local/naive event time") from None
        if (row.get("quality_status") != "VALID" or not isinstance(event, datetime)
                or event.tzinfo is not None or not scope.start_unzoned <= event < scope.end_unzoned):
            raise ValueError("Expected VALID observations within the naive source window")
        if not isinstance(row.get("truck_id"), str) or not row["truck_id"].strip():
            raise ValueError("Missing observed truck identifier")
        for name in ("plow_active", "spreader_active", "engine_active", "has_repeated_payload"):
            if type(row.get(name)) is not bool:
                raise ValueError("Status/repetition fields must be Boolean")
        if (not isinstance(row.get("record_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", row["record_sha256"])
                or type(row.get("payload_occurrences")) is not int or row["payload_occurrences"] < 1
                or row["has_repeated_payload"] != (row["payload_occurrences"] > 1)):
            raise ValueError("Invalid payload hash/frequency contract")
        row["event_time_unzoned"] = event
        selected.append(row)
    frequencies = Counter(row["record_sha256"] for row in selected)
    if any(row["payload_occurrences"] != frequencies[row["record_sha256"]] for row in selected):
        raise ValueError("Payload multiplicities do not match selected observations")
    return selected


def reference_products(rows: Iterable[Mapping[str, object]], scope: SourceScope,
                       settings: DiagnosticSettings = DiagnosticSettings()) -> dict[str, list[dict]]:
    """Pure Python oracle over synthetic/local rows; returns aggregate products only."""
    rows = _selected_rows(rows, scope)
    result = {name: [] for name in PRODUCT_NAMES}
    daily = {}
    for hour in hourly_observations(rows, scope):
        day = hour["source_local_naive_hour"].date().isoformat()
        aggregate = daily.setdefault(day, dict(source_local_naive_day=day, observation_count=0,
            plow_active_observations=0, spreader_active_observations=0, hours_containing_telemetry=0,
            maximum_hourly_distinct_truck_identifiers=0))
        aggregate["observation_count"] += hour["observation_count"]
        aggregate["plow_active_observations"] += hour["plow_active_observation_count"]
        aggregate["spreader_active_observations"] += hour["spreader_active_observation_count"]
        aggregate["hours_containing_telemetry"] += 1
        aggregate["maximum_hourly_distinct_truck_identifiers"] = max(aggregate["maximum_hourly_distinct_truck_identifiers"], hour["distinct_truck_count"])
    result["daily_activity"] = [daily[key] for key in sorted(daily)]
    for product, grain in (("equipment_hourly", "hour"), ("equipment_daily", "day")):
        groups = defaultdict(list)
        for row in rows:
            event = row["event_time_unzoned"]
            key = event.replace(minute=0, second=0, microsecond=0).isoformat(sep=" ") if grain == "hour" else event.date().isoformat()
            groups[key].append(row)
        for key, values in sorted(groups.items()):
            p = lambda row: row["plow_active"]
            s = lambda row: row["spreader_active"]
            result[product].append({"source_local_naive_" + grain: key, "observation_count": len(values),
                "plow_only_observations": sum(p(row) and not s(row) for row in values),
                "spreader_only_observations": sum(s(row) and not p(row) for row in values),
                "both_active_observations": sum(p(row) and s(row) for row in values),
                "neither_active_observations": sum(not p(row) and not s(row) for row in values),
                "engine_off_observations": sum(not row["engine_active"] for row in values),
                "engine_off_with_equipment_flag_observations": sum(not row["engine_active"] and (p(row) or s(row)) for row in values)})
    by_id, by_payload, by_day = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in rows:
        by_id[row["truck_id"]].append(row)
        by_payload[row["record_sha256"]].append(row)
        by_day[row["event_time_unzoned"].date().isoformat()].append(row)
    gaps, counts, reporting_days, conflicts, dense, peaks = [], [], [], [], [], []
    zero_span_ids = 0
    for identifier, values in by_id.items():
        ordered = sorted(values, key=lambda row: (row["event_time_unzoned"], row["record_sha256"]))
        times = {row["event_time_unzoned"] for row in values}
        counts.append(len(values))
        reporting_days.append(len({time.date() for time in times}))
        zero_span_ids += len(values) > 1 and len(times) == 1
        time_payloads = defaultdict(set)
        hours = Counter(row["event_time_unzoned"].replace(minute=0, second=0, microsecond=0) for row in values)
        for row in values:
            time_payloads[row["event_time_unzoned"]].add(row["record_sha256"])
        conflicts.append(sum(len(hashes) > 1 for hashes in time_payloads.values()))
        dense.append(sum(n > settings.dense_hour_observations for n in hours.values()))
        peaks.append(max(hours.values()))
        for previous, current in zip(ordered, ordered[1:]):
            delta = current["event_time_unzoned"] - previous["event_time_unzoned"]
            seconds = (delta.days * 86400000000 + delta.seconds * 1000000 + delta.microseconds) / 1000000
            gaps.append((identifier, seconds))
    positive = [gap for _, gap in gaps if gap > 0]
    long_ids = {identifier for identifier, gap in gaps if gap > settings.long_gap_seconds}
    result["fleet_overview"] = [dict(
        observed_identifier_count=len(by_id), observation_count=len(rows), observed_identifier_day_pairs=sum(reporting_days),
        minimum_observations_per_identifier=min(counts, default=None), maximum_observations_per_identifier=max(counts, default=None),
        mean_observations_per_identifier=sum(counts) / len(counts) if counts else None,
        singleton_identifier_count=sum(n == 1 for n in counts), constant_timestamp_identifier_count=zero_span_ids,
        same_timestamp_conflict_identifier_count=sum(n > 0 for n in conflicts), conflicting_identifier_timestamp_groups=sum(conflicts),
        identifiers_with_long_gaps=len(long_ids), consecutive_timestamp_pairs=len(gaps), zero_gap_pairs=sum(gap == 0 for _, gap in gaps),
        long_gap_pairs=sum(gap > settings.long_gap_seconds for _, gap in gaps), minimum_positive_source_clock_gap_seconds=min(positive, default=None),
        maximum_source_clock_gap_seconds=max((gap for _, gap in gaps), default=None),
        dense_reporting_identifier_count=sum(n > 0 for n in dense), dense_identifier_hour_count=sum(dense),
        peak_identifier_hour_observation_count=max(peaks, default=None), repeated_payload_group_count=sum(len(values) > 1 for values in by_payload.values()),
        repeated_payload_observations=sum(len(values) for values in by_payload.values() if len(values) > 1),
        excess_payload_observations=sum(len(values) - 1 for values in by_payload.values()),
        payload_identity_conflict_groups=sum(len({row["truck_id"] for row in values}) > 1 or len({row["event_time_unzoned"] for row in values}) > 1 for values in by_payload.values()),
        whitespace_identifier_observations=sum(row["truck_id"] != row["truck_id"].strip() for row in rows))]
    for day, values in sorted(by_day.items()):
        result["fleet_daily_participation"].append(dict(source_local_naive_day=day,
            observed_identifier_count=len({row["truck_id"] for row in values}), observation_count=len(values),
            hours_containing_telemetry=len({row["event_time_unzoned"].replace(minute=0, second=0, microsecond=0) for row in values})))
    frequency = defaultdict(list)
    for n in counts:
        band = "01_single" if n == 1 else "02_2_to_10" if n <= 10 else "03_11_to_100" if n <= 100 else "04_101_to_1000" if n <= 1000 else "05_1001_plus"
        frequency[band].append(n)
    result["fleet_observation_frequency"] = [dict(frequency_band=band, identifier_count=len(values), observation_count=sum(values)) for band, values in sorted(frequency.items())]
    gap_groups = defaultdict(list)
    for identifier, gap in gaps:
        band = "01_zero" if gap == 0 else "02_positive_within_review_threshold" if gap <= settings.long_gap_seconds else "03_above_review_threshold"
        gap_groups[band].append((identifier, gap))
    result["fleet_gap_distribution"] = [dict(gap_band=band, consecutive_timestamp_pairs=len(values), identifiers_in_band=len({identifier for identifier, _ in values}),
        minimum_source_clock_gap_seconds=min(gap for _, gap in values), maximum_source_clock_gap_seconds=max(gap for _, gap in values)) for band, values in sorted(gap_groups.items())]
    days = defaultdict(list)
    for n, day_count in zip(counts, reporting_days):
        days[day_count].append(n)
    result["fleet_reporting_days"] = [dict(days_with_observations=day, identifier_count=len(values), observation_count=sum(values)) for day, values in sorted(days.items())]
    return result
