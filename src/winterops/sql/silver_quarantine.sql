CREATE OR REPLACE VIEW $quarantine_table
COMMENT 'Exact file version; retains HEADER, INVALID and unexpected classifications for audit'
AS SELECT * FROM $silver_table
WHERE $source_filter AND (quality_status <> 'VALID' OR quality_status IS NULL)
