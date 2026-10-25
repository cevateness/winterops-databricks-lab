"""Offline integrity checks for *aggregated* Windsor notebook QA evidence.

These checks never infer that reported numbers came from a live Databricks API.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class QualitySnapshot:
    """Counts associated with one explicitly identified source-file version."""

    source_file: str
    bronze_rows: int
    silver_rows: int
    header_rows: int
    valid_rows: int
    other_invalid_rows: int
    distinct_truck_ids: int
    plow_active_observations: int
    spreader_active_observations: int

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "QualitySnapshot":
        keys = (
            "bronze_rows", "silver_rows", "header_rows", "valid_rows",
            "other_invalid_rows", "distinct_truck_ids",
            "plow_active_observations", "spreader_active_observations",
        )
        counts: dict[str, int] = {}
        for key in keys:
            value = raw[key]
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{key} must be an integer, got {value!r}")
            counts[key] = value
        source = raw["source_file"]
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source_file must be a non-empty string")
        return cls(source_file=source, **counts)


def validate_snapshot(snapshot: QualitySnapshot) -> list[str]:
    """Return invariant violations. Does *not* verify raw telemetry or APIs."""
    errors = []
    for key in (
        "bronze_rows", "silver_rows", "header_rows", "valid_rows",
        "other_invalid_rows", "distinct_truck_ids",
        "plow_active_observations", "spreader_active_observations",
    ):
        if getattr(snapshot, key) < 0:
            errors.append(f"{key} must not be negative")
    if snapshot.bronze_rows != snapshot.silver_rows:
        errors.append("Bronze and Silver row counts do not match")
    if snapshot.silver_rows != (
        snapshot.header_rows + snapshot.valid_rows + snapshot.other_invalid_rows
    ):
        errors.append("Silver classification counts do not reconcile")
    if snapshot.distinct_truck_ids > snapshot.valid_rows:
        errors.append("Distinct truck IDs exceed valid observations")
    if snapshot.plow_active_observations > snapshot.valid_rows:
        errors.append("Plow-active observations exceed valid observations")
    if snapshot.spreader_active_observations > snapshot.valid_rows:
        errors.append("Spreader-active observations exceed valid observations")
    return errors
