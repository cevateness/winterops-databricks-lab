"""Audit public four-week proposal pins and recorded aggregate consistency.

This is neither a native executor nor a replacement for the private SQL matrix,
original CSVs, row-level oracle or live prerequisites.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from winterops.unified_gold import load_selection

PROPOSAL_SHA = '1d22f9c99d2d540111296c890c3173ede71921665c5a1ac8cc938f64c589330e'


def sha(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def audit():
    path = ROOT / 'docs/FOUR_WEEK_NATIVE_PLAN.json'
    if sha(path) != PROPOSAL_SHA:
        raise ValueError('AUTHORIZED_PROPOSAL_HASH_MISMATCH')
    plan = json.loads(path.read_text())
    pins = dict(plan['code_sha256_lf'])
    for name in ('selection', 'previous_selection', 'local_evidence', 'prior_native_evidence'):
        pins[plan[name]] = plan[name + '_sha256_lf']
    if any(sha(ROOT / p) != expected for p, expected in pins.items()):
        raise ValueError('PUBLIC_DEPENDENCY_HASH_MISMATCH')
    selection = load_selection(ROOT / plan['selection'])
    previous = load_selection(ROOT / plan['previous_selection'])
    if selection.selected[:3] != previous.selected or len(selection.selected) != 4:
        raise ValueError('SOURCE_SELECTION_CHANGED')
    evidence = json.loads((ROOT / plan['local_evidence']).read_text())
    totals = evidence['totals']
    weekly = evidence['weekly_aggregates']
    for key in ('observation_count', 'plow_active_observations', 'spreader_active_observations'):
        if sum(row[key] for row in weekly) != totals[key]:
            raise ValueError('RECORDED_WEEKLY_TOTAL_MISMATCH')
    if totals['valid_rows'] + totals['header_rows'] + totals['invalid_rows'] != totals['bronze_rows']:
        raise ValueError('RECORDED_QUALITY_TOTAL_MISMATCH')
    categories = ('plow_only_observations', 'spreader_only_observations', 'both_active_observations', 'neither_active_observations')
    if sum(totals[k] for k in categories) != totals['observation_count']:
        raise ValueError('RECORDED_EQUIPMENT_TOTAL_MISMATCH')
    if (totals['plow_only_observations'] + totals['both_active_observations'] != totals['plow_active_observations']
            or totals['spreader_only_observations'] + totals['both_active_observations'] != totals['spreader_active_observations']):
        raise ValueError('RECORDED_OVERLAP_TOTAL_MISMATCH')
    expected = dict(observation_count=298051, plow_active_observations=239344, spreader_active_observations=127232)
    if any(totals[k] != v for k, v in expected.items()) or evidence['aggregate_rows'] != dict(hourly=325, daily=25, weekly=4):
        raise ValueError('ASSIGNMENT_EXPECTATIONS_MISMATCH')
    contracts = plan['statement_contracts']
    if len(contracts) != 29 or sum(c['kind'] == 'READ' for c in contracts) != 26:
        raise ValueError('PUBLIC_STATEMENT_BOUND_MISMATCH')
    creates = [c for c in contracts if c['kind'] == 'CREATE_VIEW']
    if len(creates) != 3 or [c['expected']['target'] for c in creates] != plan['new_view_targets']:
        raise ValueError('CREATE_TARGET_MISMATCH')
    if [selection.view_name(p) for p in ('hourly', 'daily', 'weekly')] != plan['new_view_targets']:
        raise ValueError('RENDER_TARGET_MISMATCH')
    return dict(status='PASS_PUBLIC_PINS_AND_RECORDED_AGGREGATES', proposal_sha256_lf=PROPOSAL_SHA,
                public_dependency_pins=len(pins), expected_totals=expected, expected_grains=evidence['aggregate_rows'],
                native_execution='NOT_PERFORMED_BY_THIS_OFFLINE_AUDIT',
                private_inputs_and_live_prerequisites='NOT_CHECKED_BY_THIS_SCRIPT',
                raw_source_revalidation='NOT_PERFORMED_BY_THIS_SCRIPT')


if __name__ == '__main__':
    try:
        print(json.dumps(audit(), indent=2))
    except Exception as error:
        print(json.dumps(dict(status='FAILED', error_type=type(error).__name__)), file=sys.stderr)
        raise SystemExit(2)
