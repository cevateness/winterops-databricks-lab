# WinterOps batch operations runbook

Use this as the normal workflow; consult historical execution plans only for the experiment they govern. Current status: [handoff](STATUS_HANDOFF.md). This assignment does not authorize another ingestion run, redeployment, recovery or scheduling. Its conditional native authorization covers only the exact four-week Gold plan.

## 1. Develop and test offline

Start from current `main`, use one feature branch, and inspect open PRs before duplicating work. Read the charter and current handoff. Keep acquisition, typed transformations and analytical publication separate. Write the source/processing identity and expected grain before adding a join or changing counts.

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src scripts notebooks
python scripts/audit_gold_candidate.py
python scripts/weather_batch.py validate
python scripts/weather_batch.py example --output /tmp/weather-review.json
```

Use a new output path when rerunning create-only weather output. On Windows, substitute a local temporary path; install `tzdata` if the system lacks an IANA database. CI also validates the aggregate fixture, renders seven SQL plans and renders the synthetic six-task Job package. The complete executable check list is [.github/workflows/ci.yml](../.github/workflows/ci.yml); placeholder hashes and synthetic Job outputs are **not deployable artifacts**.

API changes need endpoint-specific positive/negative fixtures. Reuse the existing 59 recorded native schema rows in `ON_DEMAND_BATCH_SCHEMA_DIAGNOSTIC_RESULTS.json`, including zero-based ordinals and `LONG` / `bigint`. Use the recorded Files API fixture in `tests/fixtures/` for Files absence, not a Workspace error response. Label substituted paths/content as synthetic. Do not create another native trial just to rediscover an already recorded response shape.

## 2. Prepare a source-specific deployment package

For municipal data, acquire/stage the official weekly source **outside public Git**, preserving original bytes, hashes, filename/window, source-record ordinals and the exact processing policy. Inspect actual content; a filename is not proof of the records it contains. Derive the source version from dataset/file/hash and the processing key from source version/pipeline/policy.

Render a reviewed `BatchRequest` with the existing builder:

```bash
python scripts/prepare_batch_job.py --request /private/request.json --output-root /private/package --warehouse-id APPROVED_EXISTING_ID --workspace-root /Workspace/Shared/REVIEWED_DESTINATION
```

The shared Job/task builder is reusable; the rendered SQL, expected counts and request digest are **source-specific immutable contracts**. Changing only a Job parameter does not authorize another source. Keep the original deployed Job protected; a separate acceptance Job was used historically to isolate the new-source experiment. Do not introduce one permanent weekly Job per source by default. A truly dynamic multi-source Job is a later design choice, not required for this MVP.

Deployment-time checks: exact reviewed revision/package hashes; correct workspace/warehouse; necessary privileges; target schema/types/order; destination absence or byte/identity-proven reuse; no competing writer; frozen settings and no schedule. Verify uploaded content, not just the import acknowledgement. Reuse existing compute. These checks belong to a changed deployment or source contract, not repeated rediscovery of an unchanged deployment on every successful batch.

## 3. Execute one reviewed batch and verify results

Use the exact approved deployment/run procedure and limits. Default recovery is `deny`. Existing order is preflight → Bronze → Silver → quality → COMPLETE; a failure audit records the last successful stage when reached. Existing production code remains unchanged in this assignment.

Routine integrity gates must retain selected source/processing/policy identity, schema required for positional writes, record multiplicity/lineage, quality reconciliation and manifest consistency. These guard against same-count corruption, partial scopes and accidental reuse of a changed source. `COMPLETE` is an eligibility marker, not a substitute for reconciliation. A Job SUCCESS flag alone is insufficient.

Record a compact result: revision/request/package digests; source version/processing key; run/task states; manifest attempt and final status; Bronze/Silver/HEADER/VALID/INVALID counts; reconciliation outcome; elapsed client time and any partial effects. Keep private IDs in private evidence. Use fixed error codes plus stage; do not copy raw response bodies, credentials or record payloads into public logs. Client time is not billed compute.

A selected COMPLETE version must verify and skip writes on rerun. Historical acceptance demonstrated this for the pinned inputs, including native Delta **4/5/17** after fourth-week processing and unchanged rerun. It is historical evidence, not the version every future batch should be forced to match.

## 4. Diagnose and recover deliberately

| Symptom | First action | Boundary |
| --- | --- | --- |
| Schema mismatch | Compare names, canonical full types and positions with saved evidence; inspect new metadata only if needed | `LONG` vs SQL `BIGINT` is a representation difference; NTZ vs zoned timestamp is substantive |
| FILE export rejection | Use the reviewed explicitly selected AUTO contract; verify base64, byte size and SHA | Empty optional `file_type` is allowed; acknowledgement or metadata alone cannot prove bytes |
| Files 404 | Apply Files `NOT_FOUND` / supplied `FILES_API_FILE_NOT_FOUND` contract to the exact endpoint/path | Workspace `RESOURCE_DOES_NOT_EXIST` is a different service contract; 403/permission errors are not absence |
| Nonterminal/failed manifest | Inspect last checkpoint, attempt and exact selected Bronze/Silver contents | Do not reset to NEW, delete rows or replay blindly |
| Commit succeeded before checkpoint | Compare exact scope contents; use reviewed `resume_matching` only with the matching attempt and explicit recovery scope | Full matching data may be reused; partial/conflicting rows block |
| SQL timeout/partial Gold creation | Stop and record known outcome/object subset | No automatic retry, DROP, replacement or rollback |

Each Delta statement is atomic; the whole Job spans multiple transactions. Bronze may commit before the manifest advances. Recovery must reconcile persisted data, not infer it from the last task status. Native interrupted Jobs recovery/failure auditing have not been established by the successful normal-path trial; offline simulations cover those paths. Concurrency 1 controls a single Job, not all possible writers of the tables.

## 5. Publish analytics separately

Choose explicit COMPLETE versions with a consistent policy. Reconcile additive measures across hourly/daily/weekly grains. Recompute distinct identifiers at each grain; never sum them into fleet availability. Existing published three-week/legacy views remain selected until a separate consumer decision.

Four-week publication is conditionally authorized only under the frozen plan SHA in [FOUR_WEEK_NATIVE_PLAN.json](FOUR_WEEK_NATIVE_PLAN.json): at most 29 SQL / 33 metadata GETs / 900 active seconds; exactly three create-only views after every gate. Missing pinned private inputs or credentials blocks the whole native attempt. Do not regenerate substitute matrices from rendered SQL. Multi-view publication is not atomic; preserve any partial footprint and stop on the first failure.

## Acceptance checks that should leave routine operation

| Historical check | Normal placement | Integrity retained by |
| --- | --- | --- |
| Repeat verify/process/identical-process trial | Deployment acceptance or changed write/recovery logic | Routine selected-scope idempotency and COMPLETE reconciliation |
| Exact old experiment Delta versions | Immutable experiment evidence | Current scope reconciliation; expected version transitions only where a reviewed trial requires them |
| Full EXCEPT ALL snapshots of every historical scope and every old Gold view | Release/preservation acceptance when shared tables/publication change | Routine selected-scope lineage/multiplicity checks and unchanged deployed definitions |
| Re-export every unchanged code file; list all protected owners/grants/Job settings | Deployment or suspected drift/incident | Pinned deployed package; necessary runtime source/schema checks |
| Every archived diagnostic and all historical candidate render variants | Development CI or regression investigation | One current normal workflow plus targeted failures |

This is a process recommendation, **not a change to deployed checks or the authorized frozen Gold plan**. No native checks/calls were added, removed or replayed in this assignment. Keep data-level gates; remove repeated proof of old experiments from the operator's normal checklist. Reassess metadata if deployment, permissions or schema changes, or when diagnosing drift.
