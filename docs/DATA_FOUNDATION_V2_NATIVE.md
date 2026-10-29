# V2 native integration — stopped before SQL (2026-10-29)

**Readiness PASS. Approved Phase B STOPPED at the upload deadline. No development tables were created and no Phase B SQL ran.** This is a transport failure, not native Bronze/Silver/manifest validation. See [sanitized execution evidence](DATA_FOUNDATION_V2_NATIVE_RESULTS.json).

## Actual execution

Work began at merged PR #6 / `fceb46a`, on `feat/v2-native-integration`. Original uncommitted `.gitignore`, `.vscode/settings.json` and `databricks.yml` bytes were preserved.

Phase A confirmed the expected authenticated `winterops` workspace/warehouse, required catalog/schema/Volume privileges, protected schemas and identities, absent development names and absent upload destinations. Both artifacts matched their hashes and every parsed source record.

Seven bounded read-only SQL statements succeeded without truncation: existing source/payload/published-view guards, Gold summary, two protected Delta history reads, and a synthetic V2 probe. Bronze/Silver remained 110,337 rows with 26 headers / 110,311 valid observations. Gold remained 79 buckets / 110,311 observations / 79,471 plow-active / 68,870 spreader-active. Protected Delta versions were Bronze **2**, Silver **0**. Synthetic native JSON timestamp parsing, Silver classification, duplicates, NTZ projection and UTF-8 manifest round-trip passed. New real-file reading was not exercised.

Phase A client SQL durations totaled **30.942 seconds**. Local submission-wrapper guards were corrected before SQL submission; no SQL statement was retried.

After separate explicit Phase B approval, fresh metadata checks passed. Only the two approved upload attempts ran, with `overwrite=false`, redirects/retries disabled, a 256 MiB size cap and a hard 180-second deadline per file:

| Artifact | Bytes | Outcome |
|---|---:|---|
| January 5–11 NDJSON | 3,619,379 | HTTP 204 in 9.551 seconds; post-stop HEAD 200, expected length |
| January 19–25 NDJSON | 152,492,496 | Client deadline at 180.010 seconds; no success response; post-stop HEAD 404 |

The second outcome was not promoted to success. The matrix stopped with **zero Phase B SQL statements**, no retries, cleanup or rollback. Parent directories were created only under the approved dedicated prefix. No original CSV or unrelated path changed.

All three development-name lookups returned 404 after the stop. Native table counts/classifications are **not available**; native manifest/recovery/rerun/coexistence validation is **NOT RUN**. All five protected object metadata snapshots, parent grants and warehouse configuration still matched. No protected data-write request was issued. Final protected-data SQL postflight was not reached.

## Local transport correction

`export_bronze(..., compression='gzip')` now produces optional compact transport bytes; the plain default remains compatible. The CLI exposes `--artifact-compression gzip`. SQL/PySpark path checks accept `.jsonl.gz`. Gzip headers omit filename/time, outputs remain content-addressed, and metadata distinguishes encoded versus decoded fingerprints.

The prepared replacement is **9,920,290 bytes**, instead of 152,492,496. Its compressed SHA-256 is `5516fe43d00a609c858f71323b7c4fa7c856ca7c3b8c69137e6e67ac5b99034c`. It decompresses byte-for-byte to the original NDJSON SHA-256 `94b6464999a58757ea6977cdc3d8b6e402b19edac2b9843369e7c1a18738c172`, retaining **118,159 observations**. Source CSV fingerprint, version/processing keys, row order, repeats and audit fields are unchanged. Exporting did not change manifest state or earlier exports. No compressed artifact was uploaded.

Compression reduces transport bytes, not decoded scan volume. It does not guarantee transfer duration or lower native compute cost. The [Spark JSON documentation](https://spark.apache.org/docs/latest/sql-data-sources-json.html) describes JSON Lines and gzip output. The official [line reader](https://github.com/apache/spark/blob/master/sql/core/src/main/scala/org/apache/spark/sql/execution/datasources/HadoopFileLinesReader.scala) describes codec inference from file extensions, and [binary-file reader](https://github.com/apache/spark/blob/master/sql/core/src/main/scala/org/apache/spark/sql/execution/datasources/binaryfile/BinaryFileFormat.scala) reads file bytes for fingerprinting. These are implementation references, **not proof of this warehouse's gzip compatibility**. Real-artifact/input guards must pass before any DDL in a renewed scope.

## Remaining approval and verification

The stopped run cannot resume automatically. The [revised scope](DATA_FOUNDATION_V2_INTEGRATION.md) reuses the first upload after verification, uploads only the compressed second artifact to a new immutable path, keeps the same three tables/bounds/matrix, and moves both artifact/input guards ahead of all DDL. It requires renewed explicit approval because the payload fingerprint/destination changed and the prior attempt failed. If the old failed destination later becomes visible, never overwrite or delete it automatically.

All **110 offline tests pass**, including exact decoded-byte equality, row/repeat preservation, repeatable gzip headers, unchanged manifest state, retained plain exports and bounded gzip SQL-path rendering. Syntax and original aggregate checks pass; CI is assessed at the PR head. Native DDL/DML, real JSON/gzip reading, planned recovery and no-write reruns remain unexecuted. No forecasting, optimization, streaming, jobs, schedules or dashboard work is included.
