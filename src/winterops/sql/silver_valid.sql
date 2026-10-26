CREATE OR REPLACE VIEW $valid_table
COMMENT 'Exact file version; VALID field checks only, not verified service coverage'
AS SELECT * FROM $silver_table
WHERE $source_filter AND quality_status = 'VALID' AND $window_filter
