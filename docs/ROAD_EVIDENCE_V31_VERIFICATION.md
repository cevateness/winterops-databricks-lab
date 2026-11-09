# V3.1 executed verification

Executed November 6, 2026. Current test suite: **382 passing unittest tests**, including the Node playback/privacy contract invocation. Exact PR-head GitHub Actions status is shown in the follow-up PR; CI repeats public offline checks, not private source reconstruction or native ingestion.

## Real-data execution

- Exact seven-week CSVs restored outside Git from the original private V3 replay; source identities, quality policy and all 338,746 VALID rows reconciled.
- Full road/sensor/weather workflow ran against real records and full official geometry. Reference result: 37,126 candidate fragments, 4,147 conflicting groups, 235,012 original accepted V3 intervals. [Receipt](ROAD_EVIDENCE_V31_EXECUTION.json).
- A fresh full offline rebuild of the final code reproduced **both public aggregates and the 11,917,850-byte private gzip byte-for-byte**. That final reproduction took 92.82 seconds on this host. Public/private payloads remain separate.
- Public weather replay independently reproduces all relationships from four exact public weather snapshots and 447 measured city/hour aggregate rows. 4,704 reference/clock/calendar rows, 2,448 distinct underlying weather facts, zero new HTTP calls during replay.
- New accepted portal snapshot: 7,036 records, 6,270 exact CSV multiset matches, 766 additional copies. No append and no claimed full-service equality. New source inspection and original evidence remain separately retained.
- Public HTML regeneration is byte-identical. No native Databricks requests, ingestion Jobs, Gold publication, scheduling or permissions changes occurred.

## Actual browser interaction

One shared Leaflet page was exercised using both public aggregates and the actual final private gzip, not a synthetic browser fixture. Successful checks:

| Interaction | Observed result |
| --- | --- |
| Public Dougall selection / fit | 1,661 fragments, 5,004 supported intervals, five weeks; same values after changing source week |
| Invalid local file | Rejected before parsing by byte count |
| Verified local-file loading / indexing | 2.19s initially; 3.87s after interface refinement; final byte-pinned file loaded in 3.82s. Timings vary; not an SLA |
| January 16 16:00 all states | 4,333 observations, 427 overlapping fragments, 2,833 selected accepted intervals, 1,456 sequence intervals |
| Dougall then both-active | 17 → 2 overlapping fragments; city-window observations 4,333 → 1,566, with the difference in filter grains labeled |
| Conflict / unknown overlays | All-state context visible alongside selected road evidence; recording gaps remain endpoint rings without inferred connecting paths |
| Fixed-reference clock sensitivity | January 16 16:00 snowfall 0.00cm Toronto versus 0.21cm UTC, one containing hour in either case |
| Five-minute play / pause | Advanced from 00:00 to 01:05 and paused; bucket and source-clock window remained synchronized |
| January 24 00:00 | Missing telemetry / unknown activity, while continuous reference weather remains present |
| February 10 09:00 stationary overlay + fit activity | 240 quality-flagged observations, no accepted movement or passage candidates; activity extent fit works beyond city context |
| February weather selection | Continuous reference weather available; location-matched mode explicitly reports missing January-archive coverage rather than substituting fixed weather |
| Unload | Public aggregates restored; quality/evidence/time detail controls disabled; local picker cleared |
| Missing external tiles | No external tiles configured or required. Bundled official roads and boundary remain usable offline |

Public-only screenshot: [map evidence](assets/v31-public-map.png). No detailed local screenshots were committed. One attempted January 24 selection used the wrong week, was rejected by the native select control, then corrected to January 19's source week; it did not alter data or results. Browser console errors observed were extension metadata messages, not application errors; no application exception was observed in the exercised final flow.

CSP blocks network data connections; source inspection found no fetch/upload/storage path for local data. Private inputs and outputs are outside all Git trees and outside the served dashboard. The local file interface is not a public authentication system. Browser checks validate the exercised flows; they do not certify every possible window/device combination.

## Performance and regression coverage

[Measured profile](ROAD_EVIDENCE_V31_PERFORMANCE.json): on the same original V3 file, initial frame/index preparation fell from 910.93ms to 77.88ms. Warm indexed frames were 0.04–5.01ms versus 8.63–12.41ms baseline in that single 23-frame sequence. The richer V3.1 profile (before final label-only change) decoded about 96MB, validated in 665ms, prepared its first index/frame in 526ms and warm frames in 0.53–9.01ms. Node compute timings exclude browser paint and are not cross-machine performance promises. `scripts/profile_geospatial.js` reproduces the current safe numerical profile without printing private rows.

Focused tests cover road alternatives and heading rejection, actual provider-node connectivity and endpoint disagreement, source/state/gap/reversal boundaries, short displacement, policy bounds, timestamp ties, multiplicity, source IDs, whole-second conflicts, independent weather exposure, missing weather within events, current/antecedent interval alignment, timezone alternatives, midnight interval boundaries, indexed filtering, rendering caps with uncapped metrics, public road suppression and nested private-export rejection. Existing CRS/DST, ArcGIS pagination/revision, source, quality, Gold and weather tests remain intact.

No sensor accuracy, legal routing, full-history source equality or independently verified service outcome is certified by these checks.

The compressed public transport was retested on November 7 after large generated-file publication stalled. Its decoded public data is checked for exact equality; aggregate counts and private payload are unchanged. Public replay permits 1e-12 floating-point arithmetic tolerance across Python versions while keeping structures and integer counts exact.
