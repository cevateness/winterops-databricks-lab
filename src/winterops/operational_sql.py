"""Reuse UnifiedGold definitions in a bounded local SQLite analytical workspace.

SQLite execution is portable analytical evidence, never native Spark evidence.
Only verified local inputs establish the local gate; no native manifest is forged.
"""
from datetime import datetime
from decimal import Decimal
import re
import sqlite3
import math

from winterops.unified_gold import DIMENSIONS, HOUR


def sqlite_sql(sql):
    """Adapt only the date/string/NTZ expressions used by UnifiedGold products."""
    sql = sql.replace(HOUR, "(substr(event_time_unzoned,1,13) || ':00:00')")
    sql = sql.replace('CAST(CAST(substring(CAST(event_time_unzoned AS STRING), 18, 9) AS DECIMAL(8,6)) * 1000000 AS BIGINT)',
                      'source_seconds_us(substr(event_time_unzoned,18,9))')
    sql = re.sub(r'CAST\((?:substring\(CAST\(event_time_unzoned AS STRING\), 1, 10\)|event_time_unzoned|source_local_naive_hour) AS DATE\)',
                 lambda m: 'substr(' + ('source_local_naive_hour' if 'source_local_naive_hour' in m[0] else 'event_time_unzoned') + ',1,10)', sql)
    sql = re.sub(r"DATE ('[^']*')", r'\1', sql)
    return sql.replace(' AS STRING)', ' AS TEXT)')


def cell_hour_query(plan):
    """All VALID coordinates retained; no hull, sparse-bin or review-box filter."""
    return f"""WITH _cells AS (SELECT *,
 'q25:' || CAST(CAST(FLOOR(latitude*4) AS INT) AS STRING) || ':' ||
 CAST(CAST(FLOOR(longitude*4) AS INT) AS STRING) AS spatial_bin FROM _valid)
SELECT {', '.join(DIMENSIONS)}, source_local_naive_hour, spatial_bin, {plan.activity()},
 COUNT(CASE WHEN quality_warnings LIKE '%OUTSIDE_REVIEW_ENVELOPE%' THEN 1 END) AS outside_source_review_observations
FROM _cells GROUP BY {', '.join(DIMENSIONS)}, source_local_naive_hour, spatial_bin
ORDER BY processing_key, spatial_bin, source_local_naive_hour"""


class LocalGold:
    """Ephemeral in-memory Silver and reusable SQL products; nothing is deployed."""
    def __init__(self, plan):
        self.plan = plan
        self.db = sqlite3.connect(':memory:')
        self.db.create_function('floor', 1, math.floor)
        self.db.create_function('datediff', 2, lambda end, start:
                                (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days)
        self.db.create_function('source_seconds_us', 1, lambda s: int(Decimal(s) * 1000000))
        columns = {**{c: 'TEXT' for c in DIMENSIONS}, 'source_record_number': 'INTEGER',
                   'truck_id': 'TEXT', 'record_sha256': 'TEXT', 'event_time_unzoned': 'TEXT',
                   'latitude': 'REAL', 'longitude': 'REAL', 'quality_status': 'TEXT',
                   'quality_issues': 'TEXT', 'quality_warnings': 'TEXT', 'plow_active': 'INTEGER',
                   'spreader_active': 'INTEGER', 'engine_active': 'INTEGER', 'long_gap_seconds': 'INTEGER'}
        self.columns = tuple(columns)
        self.db.execute('CREATE TABLE _selected (' + ','.join(k + ' ' + v for k, v in columns.items()) + ')')
        self.db.execute('CREATE UNIQUE INDEX local_record_key ON _selected(processing_key,source_record_number)')
        self.scopes_added = set()

    def close(self):
        self.db.close()

    def add_verified_scope(self, scope, rows):
        """Caller verifies exact source bytes; validate derived scope and row ordinals."""
        from winterops.weather import require
        require(scope in self.plan.selected and scope.processing_key not in self.scopes_added,
                'ANALYTICS_SCOPE_DUPLICATE_OR_UNSELECTED')
        require(len(rows) == scope.expected_rows and
                [r['source_record_number'] for r in rows] == list(range(1, scope.expected_rows + 1)),
                'ANALYTICS_SOURCE_ROWS')
        dims = scope.dimensions()
        require(all(all(r.get(k) == v for k, v in dims.items() if k != 'original_csv_volume_path') for r in rows),
                'ANALYTICS_SOURCE_LINEAGE')
        self.db.executemany('INSERT INTO _selected VALUES (' + ','.join('?' for _ in self.columns) + ')',
                            ([{**r, **dims, 'long_gap_seconds': scope.policy.long_gap_seconds}[k]
                              for k in self.columns] for r in rows))
        self.scopes_added.add(scope.processing_key)

    def products(self):
        from winterops.weather import require
        require(self.scopes_added == {s.processing_key for s in self.plan.selected}, 'ANALYTICS_SCOPE_INCOMPLETE')
        self.db.execute('CREATE VIEW _wanted AS ' + sqlite_sql(self.plan.wanted_sql()))
        self.db.execute('CREATE VIEW _selection_gate AS SELECT 1 AS ok')
        # Extract the existing exact VALID projection; do not duplicate its window
        # multiplicity or NTZ-hour logic. The frozen implementation stays unchanged.
        valid = self.plan.source_ctes().rsplit('_valid AS (', 1)[1][:-1]
        self.db.execute('CREATE TABLE _valid AS ' + sqlite_sql(valid))
        self.db.execute('CREATE INDEX local_valid_hour ON _valid(processing_key,source_local_naive_hour)')
        result = {p: self.query('WITH ' + self.plan.product_ctes() + '\nSELECT * FROM _' + p)
                  for p in ('hourly', 'daily', 'weekly')}
        result['cell_hour'] = self.query(cell_hour_query(self.plan))
        return result

    def query(self, sql):
        self.db.row_factory = sqlite3.Row
        return [dict(row) for row in self.db.execute(sqlite_sql(sql))]


def analytical_queries(plan):
    """Read-only Databricks-compatible candidate queries; render, never execute.

    Exact existing UnifiedGold guards remain in candidate source CTEs. Weather
    inputs are local saved artifacts and have no fabricated Databricks table.
    """
    result = {p: plan.query(p) for p in ('weekly', 'daily', 'hourly')}
    # Compose a second WITH body into the existing CTE chain.
    result['cell_hour'] = 'WITH ' + plan.source_ctes() + ',\n' + cell_hour_query(plan)[5:]
    return result


def weather_hourly_query():
    """Shared SELECT for a locally supplied cell_weather relation, not a deployment.

    The source relation is the validated private product. SQLite can execute this
    SQL as-is; Databricks can use it only after a separate approved data binding.
    """
    return """WITH distinct_grid_hours AS (
 SELECT DISTINCT processing_key, source_local_hour, timezone_hypothesis,
 weather_snapshot_id, grid_id, temperature_valid_time_utc, accumulation_valid_time_utc,
 temperature_2m_c, precipitation_activity_hour_mm, snowfall_activity_hour_cm,
 precipitation_antecedent_mm, snowfall_antecedent_cm FROM cell_weather)
SELECT processing_key, source_local_hour, timezone_hypothesis, weather_snapshot_id,
 COUNT(*) AS sampled_grid_hours, AVG(temperature_2m_c) AS temperature_2m_c_mean,
 MIN(temperature_2m_c) AS temperature_2m_c_min, MAX(temperature_2m_c) AS temperature_2m_c_max,
 AVG(precipitation_activity_hour_mm) AS precipitation_activity_hour_mm_mean,
 MAX(precipitation_activity_hour_mm) AS precipitation_activity_hour_mm_max,
 AVG(snowfall_activity_hour_cm) AS snowfall_activity_hour_cm_mean,
 AVG(precipitation_antecedent_mm) AS precipitation_antecedent_mm_mean,
 AVG(snowfall_antecedent_cm) AS snowfall_antecedent_cm_mean
FROM distinct_grid_hours
GROUP BY processing_key, source_local_hour, timezone_hypothesis, weather_snapshot_id"""


def check_weather_sql(matches, summaries):
    """Execute the shared weather SQL locally against the actual validated join."""
    import math
    from winterops.weather import require
    db = sqlite3.connect(':memory:')
    try:
        columns = ('processing_key', 'source_local_hour', 'timezone_hypothesis', 'weather_snapshot_id',
                   'grid_id', 'temperature_valid_time_utc', 'accumulation_valid_time_utc', 'temperature_2m_c',
                   'precipitation_activity_hour_mm', 'snowfall_activity_hour_cm',
                   'precipitation_antecedent_mm', 'snowfall_antecedent_cm')
        db.execute('CREATE TABLE cell_weather (' + ','.join(columns) + ')')
        db.executemany('INSERT INTO cell_weather VALUES (' + ','.join('?' for _ in columns) + ')',
                       [[row[k] for k in columns] for row in matches])
        db.row_factory = sqlite3.Row
        key = lambda r: (r['processing_key'], r['source_local_hour'], r['timezone_hypothesis'])
        expected = {key(r): r for r in summaries}
        actual = [dict(r) for r in db.execute(weather_hourly_query())]
        require(len(actual) == len(expected), 'ANALYTICS_WEATHER_SQL_GRAIN')
        for row in actual:
            require(key(row) in expected, 'ANALYTICS_WEATHER_SQL_KEY')
            for name, value in row.items():
                target = expected[key(row)][name]
                require(math.isclose(value, target, rel_tol=1e-12, abs_tol=1e-12)
                        if type(value) in (int, float) and type(target) in (int, float) else value == target,
                        'ANALYTICS_WEATHER_SQL_VALUE')
        return dict(status='PASS_EXECUTED_SQLITE_WEATHER_SQL_VS_PYTHON', rows=len(actual))
    finally:
        db.close()
