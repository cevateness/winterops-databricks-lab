# WinterOps development review — November 3, 2026

**Result:** a working historical weather batch prototype, reproducible conditional activity joins, a current operating runbook and 242 passing offline tests. Four-week Gold was reviewed without changing its implementation. Native publication is blocked by unavailable private inputs/authentication; **zero Databricks requests, SQL submissions, objects created or native changes occurred in this assignment**. Current remote target existence was not queried.

## Starting point and evidence boundaries

Latest `main` was `35c07e08f7850815660923a9570abb28343ad0e0`, matching the supplied baseline. Connected GitHub inspection found PRs #10–#16 merged and no open PR at initial inspection. Main CI [41426527686](https://github.com/cevateness/winterops-databricks-lab/actions/runs/41426527686) was successful. The checkout started a single branch, `feat/weather-batch-and-operations`. The project remains an occasional personal learning MVP; no forecasting, production service, commercialization or automation is added.

Already completed before this assignment:

- PR #15: native fourth-source verify/process/rerun, four COMPLETE scopes and preservation of previous data/Gold, supported by historical execution evidence.
- PR #16: four-week selection and create-only versioned Gold candidate; 217 offline tests; prior private-data SQLite/oracle validation. This task reran the 217-test baseline successfully in **2.832 seconds**. It did not repeat private raw-data validation.
- Three-week Gold remains the historically published baseline. Existing source-local/naive NTZ semantics, quality policy, observation multiplicity and lineage remain unchanged.

## Four-week Gold review and publication status

The explicit selection retains the first three entries unchanged and adds one distinct nonoverlapping source version/processing key under the same policy. Hourly and daily grains include selected processing provenance plus source-local hour/date; weekly grain is one selected processing version. The selection gate checks one COMPLETE manifest, source-record uniqueness/range, source/policy identity, Bronze/Silver lineage, quality classification and payload frequency. Repeated identical payloads remain observations. Additive metrics reconcile across grains; identifier participation is recomputed, not summed.

`scripts/audit_gold_candidate.py` verifies the authorized proposal SHA **1d22f9c…89330e** and **13 public dependency pins**, unchanged selection/render target names, all 29 statement classifications, recorded quality totals and overlapping equipment categories. All pass. No defect requiring a Gold runtime change was found. Existing differential/isolation/corruption tests pass. The exact proposal and pinned dependencies are byte-preserved; no replacement execution plan was generated.

| Recorded four-week candidate | Result | Status in this task |
| --- | ---: | --- |
| Valid observations | 298,051 | Public evidence consistency checked; private raw inputs unavailable |
| Plow / spreader observations | 239,344 / 127,232 | Same boundary |
| Hourly / daily / weekly rows | 325 / 25 / 4 | Existing candidate tests and renders pass |
| Bronze/Silver; HEADER; INVALID | 298,156; 105; 0 | Recorded aggregates reconcile |
| New native objects created | 0 | No native attempt |

The current user instruction conditionally authorizes the exact plan; the original JSON's preparation-time `NOT_APPROVED` wording remains historical because its hash is frozen. Authorization is **not** the blocker. This environment lacks the pinned private SQL matrix, metadata/bindings, expected aggregate-results file, original private CSV/store and secure Databricks profile/CLI configuration. There is no credential variable or default profile available. The required workspace and targets cannot be established safely, so native publication stopped before authentication or API access. None of the 29/33/900 allowance was used. There is no partial creation by this assignment and no rollback. Live state remains unknown.

## Implemented and actually executed

| Area | Files / result |
| --- | --- |
| Portable source/staging | `src/winterops/weather.py`: bounded request, exact raw snapshot/provenance, typed UTC hourly rows, contract validation and create-only verified reruns |
| Temporal analysis | `src/winterops/weather_analysis.py`: conditional timezone hypotheses, preceding-hour intervals, DST handling, strict daily join grains, missingness preservation |
| Entry points | `scripts/weather_batch.py`: fetch, offline validate/JSONL staging, recorded daily example; `scripts/audit_gold_candidate.py`: public Gold pins/evidence only |
| Real sample | `data/weather/windsor_era5_20260104_20260202/`: original 19,147-byte response plus retrieval metadata; 720 rows; no missing values/duplicate hours |
| Regression evidence | `tests/test_weather.py`: 24 new tests; Files API observed fixture plus one new replay test; existing native schema-response tests reused |
| CI | Three offline checks added: Gold public audit, weather staging and conditional example. Existing checks retained |
| Handoff | This report, weather contract/limitations, operational runbook, source register, current README/status and architecture decision |

Weather was actually retrieved twice from the public archive: an initial interface probe and one persisted acquisition. The latter is exactly recorded in `retrieval.json`, requested `models=era5`, with returned grid **42.25 / −83.0**. The provider does not attest model identity in the JSON. No synthetic measurements were presented as observed weather. Offline validation and the actual sensitivity example ran successfully; committed [WEATHER_EXAMPLE_RESULTS.json](WEATHER_EXAMPLE_RESULTS.json) reproduces from saved inputs.

The example combines January 26–February 1 weather with the existing five daily aggregate rows, independently under Toronto and UTC clock hypotheses. Both produce seven calendar rows and preserve **66,824 valid / 64,336 plow / 7,793 spreader observations**. The last two dates have null activity. January 26 precipitation differs **0.0 vs 0.1 mm**, demonstrating alignment sensitivity. No timezone choice, causal conclusion, service duration, fleet availability, road coverage or productivity is inferred.

## Architecture, trade-offs and lessons

1. **Business keys precede joins.** A weekly filename is insufficient when bytes or policies can change. Municipal source version and processing key retain that distinction. Weather binds request plus exact bytes, and hourly keys include snapshot identity. Duplicate daily/hourly keys fail before they can multiply counts.
2. **A hash proves identity, not truth.** Matching response bytes makes a result reproducible; it does not certify weather accuracy, municipality timezone, source completeness or service delivery. Keep requested model and returned metadata distinct.
3. **Event time, interval time and availability time differ.** UTC weather instants are known; activity instant interpretation is not. Accumulations use preceding-hour endpoints. Reanalysis retrieval happens later, so this dataset cannot become dispatch-time forecasts merely by applying a lag. Predictive issue-time/as-of design is deferred.
4. **Transaction boundaries determine recovery.** A source can be written before a manifest checkpoint commits. Existing scoped reconciliation and explicit matching recovery are appropriate; a whole-Job SUCCESS/FAILED label cannot describe every persisted side effect. There is no cross-Job writer lock.
5. **API contracts are service-specific.** PRs #11–#12 corrected ordinals/canonical full types; #13–#14 separated FILE export support and optional metadata from content integrity; #15 corrected Files-vs-Workspace absence semantics. The new observed fixture closes a synthetic-only fixture gap without weakening existing identity/hash checks.
6. **Observability should summarize the current attempt.** The runbook separates deployment proofs, routine data integrity and release acceptance. README no longer leads with a resolved schema failure. Historical evidence is preserved in its existing files and handoff history, while current status is concise.

Rejected alternatives: Best Match weather would weaken explicit model comparability; implicit Toronto zoning would assert unsupported source semantics; zero-filling missing activity/weather would fabricate evidence; using reanalysis as historical forecast features would leak future information. A generic API validator, orchestration rewrite, dynamic source registry, streaming stack or forecasting deployment is not warranted for this learning batch. Existing successful municipal runtime code and Job definitions are preserved. No extra native validation calls were introduced. Routine-check reductions are documented recommendations, not deployed changes.

## Validation and review

**242 tests passed, zero failures/errors, 3.162 seconds** after implementation: 217 baseline + 24 weather + one recorded Files response regression. All existing fixture, syntax, seven SQL renders and synthetic Job render pass, as do the three new offline checks. Tests exercise DST ambiguous/nonexistent times and 23/25-hour days, interval endpoints, nulls, duplicate grains, corrupt/conflicting snapshots, no-network reuse and failure before final bundle publication. These are Python/SQLite tests, not native Spark/Databricks execution.

Remote PR CI is the final review gate; its exact run and commit are linked in the PR and completion response. No automatic merge is performed. For local reproduction, use the [runbook](BATCH_OPERATIONS_RUNBOOK.md) and [weather commands](WEATHER_INTEGRATION.md#reproduce). For the full existing SQL/render command list, use `.github/workflows/ci.yml`. All new analysis runs offline after checkout; the Windows checkout and Databricks credentials are unnecessary.

## Remaining limits and next worthwhile milestone

Native Gold publication needs the **existing pinned private artifacts and secure workspace binding**, then every prerequisite and the exact authorized execution limits. This report is not a substitute for those inputs. The full 325-hour activity product was not available publicly, so the real weather example uses the available five daily aggregates; full hourly integration remains pending.

Weather is one coarse model grid point, with no station cross-check or citywide representativeness proof. All activity/weather joins remain conditional. The next useful engineering step is authoritative source timezone/clock evidence; then extend the same batch join to the complete selected aggregates and, if worthwhile, review a small weather Delta landing. Research prediction and optimization remain later work after availability-time and operational definitions are established. No deadline or recurring work is proposed.

Weather attribution and external-source references: [WEATHER_INTEGRATION.md](WEATHER_INTEGRATION.md). Contains municipal aggregates licensed under the [City of Windsor Open Government Licence](https://opendata.citywindsor.ca/Documents/OpenDataTermsofUse.pdf).
