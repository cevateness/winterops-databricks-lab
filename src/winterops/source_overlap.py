"""Multiplicity-preserving comparisons of alternate telemetry representations."""
from collections import Counter, defaultdict
from datetime import datetime


def key(row, digits=None):
    coordinate=lambda v:round(v,digits) if digits is not None else v
    return (row['truck_id'],datetime.fromisoformat(row['event_time_unzoned']).isoformat(' '),
            coordinate(row['latitude']),coordinate(row['longitude']),
            row['plow_active'],row['spreader_active'],row['engine_active'])


def compare(csv_rows, portal_rows):
    """Not an append decision. Six-decimal agreement is quantized, not exact GPS.

    Unmatched records sharing an ID/time are unresolved revision/conflict
    candidates, not proof of corrected events. Portal and CSV are not independent
    sensor systems. Duplicate multiplicity participates in multiset comparison.
    """
    a,b=Counter(key(r) for r in csv_rows),Counter(key(r) for r in portal_rows)
    aq,bq=Counter(key(r,6) for r in csv_rows),Counter(key(r,6) for r in portal_rows)
    same=sum((a&b).values());quantized=sum((aq&bq).values())
    missing=a-b;extra=b-a
    at=Counter();bt=Counter()
    for k,n in missing.items():at[k[:2]]+=n
    for k,n in extra.items():bt[k[:2]]+=n
    candidates=sum((at&bt).values())
    return dict(csv_records=len(csv_rows),portal_records=len(portal_rows),exact_matches=same,
                six_decimal_matches=quantized,quantized_only_matches=quantized-same,
                csv_unmatched=len(csv_rows)-same,portal_unmatched=len(portal_rows)-same,
                unresolved_same_identifier_time_candidates=candidates,
                csv_hour_counts=dict(sorted(Counter(r['event_time_unzoned'][:13] for r in csv_rows).items())),
                portal_hour_counts=dict(sorted(Counter(r['event_time_unzoned'][:13] for r in portal_rows).items())),
                rule='MULTISET_ID_TORONTO_NAIVE_TIME_COORDINATES_FLAGS_NO_OBJECTID_BUSINESS_KEY',
                append_decision='DO_NOT_APPEND_OVERLAP',independent_corroboration=False)
