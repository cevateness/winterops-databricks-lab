WITH _parsed AS (
 SELECT *, from_json(raw_record_json, 'MAP<STRING,STRING>') AS payload,
        COUNT(*) OVER (PARTITION BY source_version_id, record_sha256) AS payload_occurrences
 FROM $bronze_table WHERE source_version_id = '$version_id'
), _typed AS (
 SELECT $audit_fields,
   try_element_at(payload, 'Truck') AS truck_id,
   CASE WHEN trim(try_element_at(payload, 'Date time')) RLIKE '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]{1,6})?$$'
     AND substring(trim(try_element_at(payload, 'Date time')), 1, 4) <> '0000'
     THEN try_cast(trim(try_element_at(payload, 'Date time')) AS TIMESTAMP_NTZ) END AS event_time_unzoned,
   $latitude_number AS latitude, $longitude_number AS longitude,
   $plow_boolean AS plow_active, $spreader_boolean AS spreader_active, $engine_boolean AS engine_active,
   COALESCE(upper(trim(try_element_at(payload, 'Truck'))) = 'TRUCK', FALSE)
   AND COALESCE(upper(trim(try_element_at(payload, 'Date time'))) = 'DATE TIME', FALSE)
   AND COALESCE(upper(trim(try_element_at(payload, 'Latitude'))) = 'LATITUDE', FALSE)
   AND COALESCE(upper(trim(try_element_at(payload, 'Longitude'))) = 'LONGITUDE', FALSE) AS is_repeated_header,
   payload_occurrences
 FROM _parsed
), _checks AS (
 SELECT *, concat_ws(';',
   CASE WHEN csv_parse_issues <> '' THEN csv_parse_issues END,
   CASE WHEN truck_id IS NULL OR trim(truck_id) = '' THEN 'MISSING_TRUCK' END,
   CASE WHEN latitude IS NULL OR isnan(latitude) OR NOT latitude BETWEEN -90 AND 90 THEN 'INVALID_LATITUDE' END,
   CASE WHEN longitude IS NULL OR isnan(longitude) OR NOT longitude BETWEEN -180 AND 180 THEN 'INVALID_LONGITUDE' END,
   CASE WHEN event_time_unzoned IS NULL THEN 'INVALID_TIMESTAMP' END,
   CASE WHEN event_time_unzoned < CAST(source_week_start AS TIMESTAMP_NTZ)
          OR event_time_unzoned >= CAST(source_week_end_exclusive AS TIMESTAMP_NTZ) THEN 'TIMESTAMP_OUTSIDE_SOURCE_WEEK' END,
   CASE WHEN plow_active IS NULL THEN 'INVALID_PLOW_STATUS' END,
   CASE WHEN spreader_active IS NULL THEN 'INVALID_SPREADER_STATUS' END,
   CASE WHEN engine_active IS NULL THEN 'INVALID_ENGINE_STATUS' END) AS issues,
 concat_ws(';',
   CASE WHEN NOT is_repeated_header AND latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180
       AND NOT isnan(latitude) AND NOT isnan(longitude)
       AND NOT (latitude BETWEEN $lat_min AND $lat_max AND longitude BETWEEN $lon_min AND $lon_max)
       THEN 'OUTSIDE_REVIEW_ENVELOPE' END,
   CASE WHEN NOT is_repeated_header AND truck_id <> trim(truck_id) THEN 'TRUCK_WHITESPACE' END,
   CASE WHEN NOT is_repeated_header AND NOT engine_active AND (plow_active OR spreader_active)
       THEN 'ENGINE_OFF_EQUIPMENT_FLAG' END) AS quality_warnings
 FROM _typed
)
SELECT $audit_fields, '$processing_key' AS processing_key, '$pipeline_version' AS pipeline_version,
 '$policy_hash' AS quality_policy_sha256, truck_id, event_time_unzoned, latitude, longitude,
 plow_active, spreader_active, engine_active, payload_occurrences,
 payload_occurrences > 1 AS has_repeated_payload, is_repeated_header,
 CASE WHEN is_repeated_header THEN 'HEADER' WHEN issues <> '' THEN 'INVALID' ELSE 'VALID' END AS quality_status,
 CASE WHEN is_repeated_header THEN 'REPEATED_HEADER' ELSE issues END AS quality_issues, quality_warnings
FROM _checks
