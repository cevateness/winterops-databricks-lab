"""A separate provider contract for published route status, never GPS telemetry."""
from winterops.arcgis_source import digest


def edmonton_status_sample(rows):
    required={'district','priority','route_stat','seg_stat'}
    if not rows or len(rows)>100:raise ValueError('EDMONTON_BOUNDED_SAMPLE')
    identity=digest(rows);result=[]
    for i,row in enumerate(rows):
        if set(row)!=required or row['priority'] not in ('1','2','3','4') or not row['district']:
            raise ValueError('EDMONTON_STATUS_SCHEMA')
        result.append(dict(provider='city_of_edmonton',city='edmonton_ab',source='socrata_8pdx_hfxi',
                           source_version_id=identity,source_record_ordinal=i+1,
                           grain='PUBLISHED_ROUTE_STATUS_SAMPLE_NOT_EQUIPMENT_OBSERVATION',district=row['district'],
                           route_priority=int(row['priority']),reported_route_status=row['route_stat'],
                           reported_segment_status=row['seg_stat'],
                           status_available=row['seg_stat'] not in ('NA',''),provider_attributes=dict(row)))
    return result
