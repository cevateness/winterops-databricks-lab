-- Compare multiplicities, not just totals or distinct payload counts.
WITH bronze AS (
  SELECT record_sha256, COUNT(*) AS n FROM $bronze_table
  WHERE $source_filter GROUP BY record_sha256
), silver AS (
  SELECT record_sha256, COUNT(*) AS n,
         MIN(payload_occurrences) AS min_occurrences,
         MAX(payload_occurrences) AS max_occurrences
  FROM $silver_table WHERE $source_filter GROUP BY record_sha256
)
SELECT assert_true(COUNT(*) = 0, 'Bronze/Silver payload multiplicity or warning counts disagree') AS payload_check
FROM bronze b FULL OUTER JOIN silver s ON b.record_sha256 = s.record_sha256
WHERE b.n IS NULL OR s.n IS NULL OR b.n <> s.n
   OR s.min_occurrences <> b.n OR s.max_occurrences <> b.n
