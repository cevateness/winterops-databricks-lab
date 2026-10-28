# Native Gold analytics validation — 2026-10-29

**PASS: both reconciliation guards and all eight analytical products ran successfully in native Databricks SQL.** The approved run used merged PR #4, canonical main `402c820199d89a7125179449b1c3461c98924822`. Query definitions were unchanged. No corrective code change was needed.

Complete sanitized outputs, result column types, query hashes and statement timings are in [GOLD_ANALYTICS_NATIVE_RESULTS.json](GOLD_ANALYTICS_NATIVE_RESULTS.json). Metric definitions and the four-chart dashboard recommendation remain in [GOLD_ANALYTICS_PRODUCTS.md](GOLD_ANALYTICS_PRODUCTS.md).

## Scope and execution

The existing authenticated `winterops` profile accessed the previously verified warehouse, with its configuration matching the saved baseline. The two published input views matched their saved object identities. Private workspace URLs, identities, warehouse IDs and statement IDs remain local.

Source dataset, filename, canonical Volume path and SHA-256 remain exactly as documented in [SOURCE_VERSION_EVIDENCE.md](SOURCE_VERSION_EVIDENCE.md): `f5d7633c910e1ad6be23b4111445bf0bc14fe2071c6ea0f0d4cd456295ea9e94`. The selected window is `[2026-01-12 00:00:00, 2026-01-19 00:00:00)`, source-local/naive. Review settings were 1,800 source-clock seconds for long gaps and 1,000 observations per identifier-hour for dense reporting.

Exactly **11 SELECT/WITH statements** ran sequentially: one schema query with a constant synthetic clock probe, two unchanged guards, then eight unchanged product queries. Every response was HTTP 200 / SUCCEEDED, complete, inline and untruncated. No retry, cancellation, timeout, runtime error or unexpected result occurred. Each request used `wait_timeout=30s`, `on_wait_timeout=CANCEL`, a hard 45-second client deadline, and 200-row / 65,536-byte response limits. Redirects and automatic HTTP retries were disabled. There was no extra polling or result-chunk retrieval.

The one-shot runner checked exact result columns, numeric values, nonnegative integral counts, ordered unique grains, category partitions, per-day/hour completeness, histogram sums, duplicate relationships, gap bounds and prior published hourly grains/peaks. It checked each result before allowing the next statement. No source records, raw identifiers, coordinates, payloads or trajectories were exported.

| Statement, in execution order | Rows | Client elapsed seconds | Result |
|---|---:|---:|---|
| Schema and native clock probe | 27 | 9.742 | PASS |
| Source/version/per-hour guard | 1 | 9.354 | Both assertions PASS |
| Product reconciliation guard | 1 | 4.877 | Both assertions PASS |
| `daily_activity` | 7 | 2.032 | PASS |
| `equipment_hourly` | 79 | 1.876 | PASS |
| `equipment_daily` | 7 | 1.696 | PASS |
| `fleet_overview` | 1 | 3.280 | PASS |
| `fleet_daily_participation` | 7 | 1.698 | PASS |
| `fleet_observation_frequency` | 4 | 1.816 | PASS |
| `fleet_gap_distribution` | 3 | 1.920 | PASS |
| `fleet_reporting_days` | 2 | 1.772 | PASS |

All four guard outputs were SQL NULL, the successful `assert_true` result. The source guard matched 110,311 valid observations, 251 observed identifiers, 79,471 plow-active and 68,870 spreader-active observations, including full per-hour Silver/Gold reconciliation and payload multiplicities. Whole-view checks rejected unrelated versions/window rows. Product checks reconciled daily/hourly totals and `110,311 - 251 = 110,060` consecutive pairs.

This run verified the source binding stored in the published valid Silver and hourly Gold views. It **did not** independently rehash the raw CSV or repeat the Bronze audit. That earlier byte/source evidence remains dated 2026-10-28. Views are not immutable snapshots; the statements were not a multi-query transaction, and no repeat stability run was included in this approval.

## Observed analytical results

### Daily observations and participation

All dates and telemetry hours below are source-local/naive. The participation column is daily distinct raw identifiers; the peak column is the maximum distinct count within one hour.

| Source date | Observations | Plow flag | Spreader flag | Hours with telemetry | Daily identifiers | Peak hourly identifiers |
|---|---:|---:|---:|---:|---:|---:|
| 2026-01-12 | 1 | 1 | 0 | 1 | 1 | 1 |
| 2026-01-13 | 142 | 140 | 2 | 4 | 3 | 1 |
| 2026-01-14 | 31,222 | 24,750 | 18,323 | 14 | 58 | 18 |
| 2026-01-15 | 52,115 | 38,246 | 33,017 | 24 | 104 | 17 |
| 2026-01-16 | 16,209 | 11,037 | 9,734 | 21 | 50 | 20 |
| 2026-01-17 | 10,476 | 5,151 | 7,794 | 11 | 38 | 18 |
| 2026-01-18 | 146 | 146 | 0 | 4 | 9 | 4 |

The week contains **79 hours with telemetry**, not 79 hours worked. January 15 has the largest observation count in this file; that does not establish the greatest workload or service delivered. Daily identifier counts sum to 263 identifier-day pairs; weekly distinct identifiers remain **251**. Hourly distinct counts must not be summed into fleet size.

### Equipment composition

| Mutually exclusive category | Observations |
|---|---:|
| Plow-only | 41,441 |
| Spreader-only | 30,840 |
| Both flags active | 38,030 |
| Neither flag active | 0 |
| **Total** | **110,311** |

Plow-only + both = 79,471; spreader-only + both = 68,870. Hourly categories reconcile to each daily category. Engine-off observations and engine-off-with-equipment-flag observations were both **0**. These are observed flag values, not proof of continuous engine operation, equipment effectiveness or mechanical consistency. The absence of neither-active observations and uniformly true engine flags are field-semantics questions for subsequent review, not evidence of productivity.

### Fleet reporting diagnostics

- **251** raw identifiers reported; **239** appeared on one source date and **12** on two dates. Without a roster and stable ID mapping, these cannot establish actual fleet size, availability, identifier reassignment or operating schedules.
- Observations per identifier: minimum **1**, mean **439.4861**, maximum **977**. Frequency bins contain 4 identifiers with one observation, 7 with 2–10, 36 with 11–100, and 204 with 101–1,000; the 1,001+ bin is absent. Four identifiers were singletons.
- **1,097** repeated-payload groups contain **2,210** observations, of which **1,113** are excess copies. All observations remain retained. No cross-identifier/timestamp payload-hash conflicts or surrounding-whitespace identifier observations were found.
- **165** identifiers had more than one payload hash at a timestamp, across **2,661** identifier/timestamp groups. There were no multi-observation identifiers with only one timestamp. These are reporting conflicts for review, not demonstrated corruption or operational failure.
- **110,060** consecutive pairs comprise **3,793** zero gaps, **106,172** positive gaps at or below 1,800 seconds, and **95** gaps above that threshold. Long gaps involve **82** identifiers. The smallest positive gap is **1 second** and the maximum is **23,467 source-clock seconds**. Gap-band identifier counts overlap and cannot be summed.
- No identifier-hour exceeded 1,000 observations; the peak was **515**. This review threshold is not a known cadence or physical operating limit.

No gap measures vehicle downtime, staff time or an unobserved absence interval at the beginning/end of the week. Sorted source timestamps do not reveal arrival ordering or clock rollback. Source timezone and observation cadence remain unverified.

## Native runtime compatibility and performance

- Metadata returned 18 valid-Silver columns and nine hourly-Gold columns. All 17 required Silver types and all nine Gold types matched. Source event/hour types were `TIMESTAMP_NTZ`; flags were Boolean and count fields BIGINT.
- The schema query's three synthetic timestamp values were deliberately unordered, with a tied timestamp on leap day and a following timestamp across midnight. Native NTZ-to-string/date extraction, `DECIMAL(8,6)` seconds, calendar arithmetic and ordered LAG returned two pairs: one zero gap and one **500,001-microsecond** positive gap. No timezone or instant conversion was introduced.
- Product manifests returned DATE daily grains, TIMESTAMP_NTZ hourly grains, LONG counts, DOUBLE mean and DECIMAL source-clock gaps. Native CTEs, scalar subqueries, full outer joins, aggregate assertions, window ordering and all eight product projections succeeded unchanged.
- Client statement times totaled **40.063 seconds**; the eight product requests totaled **16.090 seconds**, ranging from **1.696 to 3.280 seconds**. The two guards took 9.354 and 4.877 seconds; the schema/probe request took 9.742 seconds. Every request completed within its bounds.

These are one-run request durations, including transport, queueing, compilation and possible compute-resume effects. They are not isolated engine times, controlled cold/warm benchmarks or a latency guarantee. No query profile, bytes-scanned metrics or repetition was collected. Shared CTEs may rescan/sort Silver across products; this run gives no evidence that new caching/materialization infrastructure is necessary. Repeated dashboard refresh costs remain unmeasured.

## Engineering verification and remaining work

The unchanged suite passed **80 offline tests**. An initial sandbox run hit Windows temporary-directory permission errors in two CSV tests; the unchanged suite passed outside that sandbox. Aggregate fixture validation passed. The session-only response checker also accepted all eight synthetic product shapes and rejected seven malformed/duplicate-result cases before any SQL submission. No production SQL/Python, original fixtures, notebooks, source files or published definitions were modified for this task.

Changes are evidence and status documentation on `feat/native-gold-validation`. GitHub CI is assessed at the resulting PR head. Original uncommitted `.gitignore`, `.vscode/settings.json` and `databricks.yml` bytes were preserved and excluded from commits.

This approval was consumed by the completed one-shot SQL API run. It does not authorize another run, DDL, dashboard publication, jobs, schedules, grant changes or warehouse configuration changes. The notebook/Spark entrypoint was not executed. Next small milestone: review these diagnostics and the identifier/flag interpretation limits, then choose whether to prepare the documented four-chart dashboard from these aggregate datasets. Weather, H3, multi-week ingestion, forecasting and optimization remain separate scopes.
