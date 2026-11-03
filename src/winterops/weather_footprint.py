"""Coarse activity footprint and collection-size diagnostics; no raw geometry.

Use quarter-degree cell corners on an integer lattice. This is a conservative
envelope of candidate cells, not a hull of GPS positions or a municipal boundary.
"""
import re

from winterops.weather import WeatherRequest, require


def _cell(value):
    require(isinstance(value, str) and re.fullmatch(r'q25:-?\d+:-?\d+', value) is not None,
            'FOOTPRINT_COARSE_BIN_REQUIRED')
    _, y, x = value.split(':')
    y, x = int(y), int(x)
    require(value == f'q25:{y}:{x}', 'FOOTPRINT_CANONICAL_BIN_REQUIRED')
    WeatherRequest(latitude=(y + .5) / 4, longitude=(x + .5) / 4, grid_only=True)
    return x, y


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _hull(points):
    points = sorted(set(points))
    if len(points) <= 1:
        return points
    def half(sequence):
        result = []
        for point in sequence:
            while len(result) >= 2 and _cross(result[-2], result[-1], point) <= 0:
                result.pop()
            result.append(point)
        return result
    return half(points)[:-1] + half(reversed(points))[:-1]


def coarse_footprint(spatial_bins):
    """O(K log K) hull after deduplication, where K is coarse occupied cells.

    Enumerate at most 64 bounding-box candidate centres. Hull membership uses
    exact doubled-integer coordinates, including polygon edges. Do not treat
    candidates as actual provider grids until returned-grid metadata is known.
    """
    cells = sorted({_cell(value) for value in spatial_bins})
    base = dict(geometry_kind='COARSE_CELL_ENVELOPE_NOT_RAW_POSITION_HULL',
                coordinate_order='longitude_latitude', cell_size_degrees=.25,
                occupied_bin_count=len(cells), occupied_bins=[f'q25:{y}:{x}' for x, y in cells])
    if not cells:
        return dict(base, bbox=None, convex_hull=None, hull_candidate_bins=[],
                    hull_candidate_count=0, bbox_candidate_count=0)
    xmin, xmax = min(x for x, _ in cells), max(x for x, _ in cells)
    ymin, ymax = min(y for _, y in cells), max(y for _, y in cells)
    require((xmax - xmin + 1) * (ymax - ymin + 1) <= 64, 'FOOTPRINT_CANDIDATE_BOUND')
    corners = {(x + dx, y + dy) for x, y in cells for dx, dy in ((0, 0), (1, 0), (1, 1), (0, 1))}
    polygon = _hull(corners)
    doubled = [(2 * x, 2 * y) for x, y in polygon]
    edges = list(zip(doubled, doubled[1:] + doubled[:1]))
    candidates = []
    for x in range(xmin, xmax + 1):
        for y in range(ymin, ymax + 1):
            centre = (2 * x + 1, 2 * y + 1)
            if all(_cross(a, b, centre) >= 0 for a, b in edges):
                candidates.append(f'q25:{y}:{x}')
    ring = [[x / 4, y / 4] for x, y in polygon + polygon[:1]]
    return dict(base, bbox=[xmin / 4, ymin / 4, (xmax + 1) / 4, (ymax + 1) / 4],
                convex_hull=dict(type='Polygon', coordinates=[ring]),
                hull_candidate_bins=candidates, hull_candidate_count=len(candidates),
                bbox_candidate_count=(xmax - xmin + 1) * (ymax - ymin + 1))


def collection_comparison(footprint, *, utc_dates, activity_api_hours):
    """Compare occupied demand with filling the region on every required date.

    Estimates are returned-hour counts, not billing or guaranteed unique model
    grid counts. The actual plan still requests only occupied bins/time windows.
    """
    days = len(set(utc_dates))
    return dict(selection='OCCUPIED_BIN_AND_HOUR_DEMAND', union_required_utc_dates=days,
                activity_driven_api_hours=activity_api_hours,
                hull_region_all_dates_api_hours=24 * days * footprint['hull_candidate_count'],
                bbox_region_all_dates_api_hours=24 * days * footprint['bbox_candidate_count'],
                regional_requests_executed=False,
                unique_provider_grid_count='UNKNOWN_UNTIL_RESPONSES_ARE_BOUND')
