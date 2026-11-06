"""Offline public diagnostics and a distinct private geographic playback renderer."""
from pathlib import Path
from winterops.weather import canonical
from winterops.weather import require


def render_public(summary):
    def check(value):
        if isinstance(value,dict):
            forbidden={'truck_id','source_record_ordinals','first_observed','last_observed',
                       'first_observed_cell','spatial_bin','grid_id','latitude','longitude','raw_record_json'}
            require(not (set(value)&forbidden),'DIAG_PRIVATE_FIELD_IN_PUBLIC_OUTPUT')
            for item in value.values():check(item)
        elif isinstance(value,list):
            for item in value:check(item)
    check(summary)
    return _render('diagnostics.html',summary)


def render_private(data):
    # No identifier, raw coordinate or episode input can reach this view.
    fields=('processing_key','spatial_bin','source_local_naive_hour','observation_count',
            'plow_only_observations','spreader_only_observations','both_active_observations')
    match_fields=('processing_key','spatial_bin','source_local_hour','timezone_hypothesis','grid_id',
                  'temperature_2m_c','precipitation_activity_hour_mm','snowfall_activity_hour_cm',
                  'precipitation_antecedent_mm','snowfall_antecedent_cm')
    projected=dict(evidence=data['evidence'],snapshot_id=data['snapshot_id'],scopes=data['scopes'],grids=data['grids'],
                   cells=[{k:r[k] for k in fields} for r in data['cells']],
                   matches=[{k:r[k] for k in match_fields} for r in data['matches']])
    return _render('private_playback.html',projected)


def _render(name,data):
    source=(Path(__file__).parent/'templates'/name).read_text(encoding='utf-8')
    return source.replace('__DATA__',canonical(data).decode().replace('<','\\u003c').replace('&','\\u0026'))
