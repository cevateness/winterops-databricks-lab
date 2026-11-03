"""Bounded Open-Meteo ERA5 batch acquisition and portable hourly staging.

No Databricks client, retries, interpolation or forecast-feature generation.
Response extensions are tolerated; fields used by this contract are validated.
"""
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import tempfile
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ENDPOINT = 'https://archive-api.open-meteo.com/v1/archive'
VARIABLES = ('temperature_2m', 'precipitation', 'snowfall')
UNITS = dict(time='unixtime', temperature_2m='°C', precipitation='mm', snowfall='cm')
MAX_BYTES = 1048576
UTC = timezone.utc
ATTRIBUTION = 'Weather data by Open-Meteo.com (https://open-meteo.com/), ERA5 / Copernicus C3S; CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).'


class WeatherContractError(ValueError):
    """Fixed public-safe error codes; never echo response bodies."""


def require(condition, code):
    if not condition:
        raise WeatherContractError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(value).hexdigest()


def decode_json(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, 'WEATHER_RESPONSE_SIZE')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'WEATHER_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def nonfinite(_):
        raise WeatherContractError('WEATHER_NONFINITE_JSON')
    try:
        body = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=nonfinite)
    except (UnicodeError, ValueError) as error:
        if isinstance(error, WeatherContractError):
            raise
        raise WeatherContractError('WEATHER_INVALID_JSON') from None
    require(type(body) is dict, 'WEATHER_OBJECT_REQUIRED')
    return body


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


@dataclass(frozen=True)
class WeatherRequest:
    """One representative Windsor point, fixed model, at most 31 UTC days.

    End date is inclusive as required by the archive API. This point is a
    sampling choice, not a city boundary, station or vehicle location.
    """
    start_date: str = '2026-01-04'
    end_date: str = '2026-02-02'
    latitude: float = 42.3149
    longitude: float = -83.0364
    grid_only: bool = False

    def __post_init__(self):
        try:
            start, end = date.fromisoformat(self.start_date), date.fromisoformat(self.end_date)
        except (ValueError, TypeError):
            raise WeatherContractError('WEATHER_DATE_CONTRACT') from None
        require(start.isoformat() == self.start_date and end.isoformat() == self.end_date
                and 0 <= (end - start).days < 31, 'WEATHER_DATE_BOUND')
        require(finite(self.latitude) and finite(self.longitude)
                and 42 <= self.latitude <= 43 and -84 <= self.longitude <= -82, 'WEATHER_WINDSOR_POINT_BOUND')
        require(type(self.grid_only) is bool, 'WEATHER_GRID_MODE_REQUIRED')

    @property
    def parameters(self):
        parameters = dict(latitude=self.latitude, longitude=self.longitude,
                    start_date=self.start_date, end_date=self.end_date,
                    hourly=','.join(VARIABLES), models='era5', timezone='GMT',
                    timeformat='unixtime', temperature_unit='celsius',
                    precipitation_unit='mm', cell_selection='land')
        if self.grid_only:
            # Disable point-elevation downscaling so identical returned model
            # cells are comparable across coarse requested representatives.
            parameters.update(elevation='nan', cell_selection='nearest')
        return parameters

    @property
    def url(self):
        return ENDPOINT + '?' + urlencode(self.parameters)

    @property
    def request_id(self):
        return digest(canonical(dict(endpoint=ENDPOINT, parameters=self.parameters)))

    @property
    def epochs(self):
        start = datetime.combine(date.fromisoformat(self.start_date), time(), UTC)
        end = datetime.combine(date.fromisoformat(self.end_date) + timedelta(days=1), time(), UTC)
        return tuple(range(int(start.timestamp()), int(end.timestamp()), 3600))


def stage_response(raw, request):
    """Return one row per snapshot/UTC valid time, preserving explicit nulls.

    Snapshot identity binds request + exact wire bytes. The response does not
    attest a model name: ERA5 is recorded as requested, never independently proven.
    """
    require(isinstance(request, WeatherRequest), 'WEATHER_REQUEST_REQUIRED')
    body = decode_json(raw)
    require('error' not in body and 'reason' not in body, 'WEATHER_API_ERROR')
    require(type(body.get('utc_offset_seconds')) is int and body['utc_offset_seconds'] == 0
            and body.get('timezone') in ('GMT', 'UTC', 'Etc/GMT', 'Etc/UTC'), 'WEATHER_UTC_REQUIRED')
    for key in ('latitude', 'longitude', 'elevation'):
        require(finite(body.get(key)), 'WEATHER_GRID_METADATA')
    require(abs(body['latitude'] - request.latitude) <= 1
            and abs(body['longitude'] - request.longitude) <= 1, 'WEATHER_GRID_OUTSIDE_POINT_BOUND')
    require(type(body.get('hourly_units')) is dict
            and all(body['hourly_units'].get(k) == v for k, v in UNITS.items()), 'WEATHER_UNIT_MISMATCH')
    hourly = body.get('hourly')
    require(type(hourly) is dict and all(type(hourly.get(k)) is list for k in ('time',) + VARIABLES),
            'WEATHER_HOURLY_ARRAYS')
    epochs = hourly['time']
    require(all(type(t) is int for t in epochs) and tuple(epochs) == request.epochs,
            'WEATHER_TIME_GRID_MISSING_DUPLICATE_OR_UNORDERED')
    require(all(len(hourly[k]) == len(epochs) for k in VARIABLES), 'WEATHER_ARRAY_LENGTH')
    snapshot = digest(canonical(dict(request_id=request.request_id, response_sha256=digest(raw))))
    rows = []
    for index, epoch in enumerate(epochs):
        values = {k: hourly[k][index] for k in VARIABLES}
        for key, value in values.items():
            require(value is None or finite(value), 'WEATHER_NUMERIC_TYPE')
            require(value is None or key == 'temperature_2m' or value >= 0, 'WEATHER_NEGATIVE_ACCUMULATION')
        rows.append(dict(snapshot_id=snapshot, valid_time_utc=datetime.fromtimestamp(epoch, UTC).isoformat(),
                         accumulation_start_utc=datetime.fromtimestamp(epoch - 3600, UTC).isoformat(),
                         temperature_2m_c=values['temperature_2m'],
                         precipitation_preceding_hour_mm=values['precipitation'],
                         snowfall_preceding_hour_cm=values['snowfall'],
                         missing_variables=[k for k, v in values.items() if v is None],
                         weather_kind='historical_reanalysis', requested_model='era5'))
    return rows, {k: body[k] for k in ('latitude', 'longitude', 'elevation', 'timezone', 'utc_offset_seconds')}


def acquire_snapshot(destination, request=WeatherRequest(), *, opener=urlopen):
    """One HTTP GET, 30s socket timeout, 1 MiB read cap; create-only local bundle.

    A rerun against an existing destination verifies/reuses it with zero HTTP.
    A response change requires another destination. Bytes and metadata are staged
    together before an atomic directory rename on the same filesystem.
    """
    destination = Path(destination)
    if destination.exists():
        metadata, rows = load_snapshot(destination)
        require(metadata['request_id'] == request.request_id, 'WEATHER_EXISTING_REQUEST_CONFLICT')
        return metadata, rows
    started = datetime.now(UTC).isoformat()
    with opener(Request(request.url, headers={'Accept': 'application/json',
                'User-Agent': 'WinterOps-learning-batch/1'}), timeout=30) as response:
        require(response.status == 200, 'WEATHER_HTTP_200_REQUIRED')
        require(response.geturl() == request.url, 'WEATHER_REDIRECT_NOT_EXPECTED')
        require(response.headers.get_content_type() == 'application/json', 'WEATHER_JSON_CONTENT_TYPE')
        raw = response.read(MAX_BYTES + 1)
        rows, grid = stage_response(raw, request)
        metadata = dict(contract_version='open-meteo-era5-windsor-v1', request=asdict(request),
                        request_id=request.request_id, request_url=request.url,
                        response_sha256=digest(raw), response_bytes=len(raw), snapshot_id=rows[0]['snapshot_id'],
                        retrieval_started_at_utc=started, retrieved_at_utc=datetime.now(UTC).isoformat(),
                        http_status=200, response_date=response.headers.get('Date'),
                        response_etag=response.headers.get('ETag'), grid=grid, row_count=len(rows),
                        weather_kind='historical_reanalysis', model_attestation='REQUEST_PARAMETER_ONLY',
                        attribution=ATTRIBUTION)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.weather-stage-', dir=destination.parent) as staging:
        bundle = Path(staging) / 'bundle'
        bundle.mkdir()
        (bundle / 'response.json').write_bytes(raw)
        (bundle / 'retrieval.json').write_bytes(canonical(metadata) + b'\n')
        bundle.rename(destination)
    return metadata, rows


def load_snapshot(directory):
    """Verify local provenance and body integrity before any transformation."""
    directory = Path(directory)
    with (directory / 'retrieval.json').open('rb') as source:
        metadata = decode_json(source.read(MAX_BYTES + 1))
    request = WeatherRequest(**metadata['request'])
    with (directory / 'response.json').open('rb') as source:
        raw = source.read(MAX_BYTES + 1)
    rows, grid = stage_response(raw, request)
    require(metadata.get('contract_version') == 'open-meteo-era5-windsor-v1'
            and metadata.get('request_url') == request.url and metadata.get('request_id') == request.request_id
            and metadata.get('http_status') == 200 and metadata.get('response_bytes') == len(raw)
            and metadata.get('response_sha256') == digest(raw) and metadata.get('grid') == grid
            and metadata.get('row_count') == len(rows) and metadata.get('snapshot_id') == rows[0]['snapshot_id']
            and metadata.get('weather_kind') == 'historical_reanalysis'
            and metadata.get('model_attestation') == 'REQUEST_PARAMETER_ONLY'
            and metadata.get('attribution') == ATTRIBUTION, 'WEATHER_SNAPSHOT_INTEGRITY')
    for key in ('retrieval_started_at_utc', 'retrieved_at_utc'):
        try:
            stamp = datetime.fromisoformat(metadata[key])
        except (KeyError, TypeError, ValueError):
            raise WeatherContractError('WEATHER_RETRIEVAL_TIMESTAMP') from None
        require(stamp.utcoffset() == timedelta(0), 'WEATHER_RETRIEVAL_TIMESTAMP')
    require(metadata['retrieval_started_at_utc'] <= metadata['retrieved_at_utc'], 'WEATHER_RETRIEVAL_ORDER')
    return metadata, rows
