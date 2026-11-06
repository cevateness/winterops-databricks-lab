"""Bounded public ArcGIS snapshots; connector keys are not business event keys.

Every HTTP body is retained outside Git. COMPLETE means the requested ID set was
retrieved and reconciled twice, not that a mutable service offered transaction
isolation. Attribute revisions during extraction remain possible without a
provider-supported historicMoment/replica; compare immutable snapshots explicitly.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import time
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import build_opener
from uuid import uuid4
from zoneinfo import ZoneInfo

from winterops.sources import NoRedirect, outside_git


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return sha256(canonical(value)).hexdigest()


def semantic_fingerprint(payload):
    """Compare record contracts across explicit connector-envelope revisions.

    Older snapshots omit the optional fields key; None means the same `*`
    projection. Scope labels are not provider identities. Raw snapshot/body
    fingerprints remain separate and are never rewritten by this comparison.
    """
    source=payload['source']
    return digest(dict(source={k:source[k] for k in ('provider','city','layer_url')},
                       where=payload['where'],schema=payload['schema'],fields=payload.get('fields'),features=payload['features']))


@dataclass(frozen=True)
class ArcGISSource:
    provider: str
    city: str
    source: str
    layer_url: str

    def __post_init__(self):
        u = urlsplit(self.layer_url)
        if (u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment
                or not u.path.rsplit('/', 1)[-1].isdigit()
                or not any('/'+s+'/' in u.path for s in ('MapServer', 'FeatureServer'))
                or not all((self.provider, self.city, self.source))):
            raise ValueError('ARCGIS_EXPLICIT_PUBLIC_LAYER_REQUIRED')

    @property
    def canonical_source_id(self):
        # `source` is a human extraction label; periods/aliases must not create
        # an apparently independent provider. The service URL identifies layer.
        return digest(dict(provider=self.provider,city=self.city,layer_url=self.layer_url))


class PublicClient:
    """Finite HTTP budget including retries. No redirect or credential handling."""
    def __init__(self, root, max_requests=120, max_bytes=80_000_000, retries=1):
        self.root = outside_git(root)
        self.root.mkdir(parents=True, exist_ok=True)
        if not 1 <= max_requests <= 500 or not 1 <= max_bytes <= 256_000_000 or not 0 <= retries <= 2:
            raise ValueError('ARCGIS_HTTP_BUDGET')
        self.max_requests, self.max_bytes, self.retries = max_requests, max_bytes, retries
        self.requests = self.bytes = 0
        self.receipts = []
        self.opener = build_opener(NoRedirect())

    def get(self, url, **params):
        target = url + '?' + urlencode(dict(f='json', **params))
        for attempt in range(self.retries+1):
            if self.requests >= self.max_requests:
                raise ValueError('ARCGIS_REQUEST_BUDGET')
            self.requests += 1
            try:
                with self.opener.open(target, timeout=35) as response:
                    if response.status != 200 or response.url != target:
                        raise ValueError('ARCGIS_HTTP_RESPONSE')
                    body = response.read(min(12_000_000, self.max_bytes-self.bytes)+1)
                    self.bytes += len(body)
                    if self.bytes > self.max_bytes or len(body) > 12_000_000:
                        raise ValueError('ARCGIS_BYTE_BUDGET')
                    receipt = dict(url=target, retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                                   bytes=len(body), sha256=sha256(body).hexdigest(), attempt=attempt,
                                   etag=response.headers.get('ETag'), last_modified=response.headers.get('Last-Modified'))
                p = self.root/(receipt['sha256']+'.json')
                if not p.exists():
                    with p.open('xb') as out: out.write(body)
                elif p.read_bytes() != body:
                    raise ValueError('ARCGIS_IMMUTABLE_BODY_CONFLICT')
                self.receipts.append(receipt)
                with (self.root/'http.jsonl').open('a', encoding='utf-8') as out:
                    out.write(json.dumps(receipt)+'\n')
                result = json.loads(body)
                if not isinstance(result, dict) or 'error' in result:
                    raise ValueError('ARCGIS_SERVICE_ERROR')
                return result
            except HTTPError as error:
                with (self.root/'http.jsonl').open('a', encoding='utf-8') as out:
                    out.write(json.dumps(dict(url=target, status=error.code, attempt=attempt))+'\n')
                if error.code not in (429, 502, 503, 504) or attempt == self.retries:
                    raise
                time.sleep(min(2, attempt+1))


def schema_contract(metadata):
    fields = metadata.get('fields')
    if not fields or len({f['name'] for f in fields}) != len(fields):
        raise ValueError('ARCGIS_SCHEMA_FIELDS')
    ids = [f['name'] for f in fields if f['type'] == 'esriFieldTypeOID']
    if len(ids) != 1:
        raise ValueError('ARCGIS_ONE_OBJECT_ID_REQUIRED')
    return dict(fields=fields, object_id=ids[0], geometry_type=metadata.get('geometryType'),
                source_crs=metadata.get('sourceSpatialReference'),
                date_reference=metadata.get('dateFieldsTimeReference'),
                dates_unknown=metadata.get('datesInUnknownTimezone', False))


def snapshot(source, client, root, where, max_records, batch_size=500, expected_schema=None, fields=None):
    """Count → IDs → exact batches → IDs/count/schema again, then immutable COMPLETE.

    Caller supplies a reviewed SQL scope; do not insert untrusted browser input.
    IDs are scoped to this snapshot only. Failed attempts retain raw responses and
    STARTED/FAILED manifests, never a COMPLETE dataset.
    """
    root = outside_git(root)
    root.mkdir(parents=True, exist_ok=True)
    if not where or type(max_records) is not int or not 1 <= max_records <= 100_000:
        raise ValueError('ARCGIS_RECORD_BOUND')
    attempt = root/(uuid4().hex+'.attempt.json')
    status = dict(state='STARTED', source=source.__dict__, where=where, max_records=max_records)
    attempt.write_bytes(canonical(status))
    start = len(client.receipts)
    try:
        metadata = client.get(source.layer_url)
        contract = schema_contract(metadata)
        schema = digest(contract)
        if expected_schema is not None and expected_schema != schema:
            raise ValueError('ARCGIS_SCHEMA_CHANGED')
        if not 1 <= batch_size <= min(1000, metadata.get('maxRecordCount', 0)):
            raise ValueError('ARCGIS_BATCH_SIZE')
        query = source.layer_url+'/query'
        def count():
            n = client.get(query, where=where, returnCountOnly='true').get('count')
            if type(n) is not int or not 0 <= n <= max_records:
                raise ValueError('ARCGIS_COUNT_BOUND')
            return n
        def ids():
            result = client.get(query, where=where, returnIdsOnly='true')
            values = result.get('objectIds')
            if (result.get('exceededTransferLimit') or not isinstance(values, list)
                    or any(type(v) is not int for v in values) or len(values) > max_records
                    or len(set(values)) != len(values)):
                raise ValueError('ARCGIS_ID_SET')
            return sorted(values)
        expected = count()
        selected = ids()
        if len(selected) != expected:
            raise ValueError('ARCGIS_COUNT_ID_MISMATCH')
        features = []
        oid = contract['object_id']
        field_names = {f['name'] for f in contract['fields'] if f['type'] != 'esriFieldTypeGeometry'}
        if fields is not None:
            if not isinstance(fields, tuple) or not set(fields)<=field_names or oid not in fields or len(set(fields))!=len(fields):
                raise ValueError('ARCGIS_EXPLICIT_FIELD_PROJECTION')
            field_names=set(fields)
        for offset in range(0, len(selected), batch_size):
            batch = selected[offset:offset+batch_size]
            page = client.get(query, objectIds=','.join(map(str,batch)), where=where, outFields=','.join(fields) if fields else '*',
                              returnGeometry='true', outSR=4326, orderByFields=oid+' ASC')
            values = page.get('features')
            if page.get('exceededTransferLimit') or not isinstance(values, list):
                raise ValueError('ARCGIS_PARTIAL_PAGE')
            if page.get('spatialReference', {}).get('wkid') != 4326:
                raise ValueError('ARCGIS_OUTPUT_CRS')
            actual = [f['attributes'].get(oid) for f in values]
            if len(actual) != len(batch) or sorted(actual) != batch:
                raise ValueError('ARCGIS_PAGE_IDS')
            if any(set(f['attributes']) != field_names for f in values):
                raise ValueError('ARCGIS_FEATURE_SCHEMA')
            features.extend(values)
        if count() != expected or ids() != selected or schema_contract(client.get(source.layer_url)) != contract:
            raise ValueError('ARCGIS_SOURCE_CHANGED_DURING_READ')
        features.sort(key=lambda f:f['attributes'][oid])
        payload = dict(source=source.__dict__, where=where, fields=fields, schema=contract, schema_sha256=schema, features=features)
        identity = digest(payload)
        target = root/(identity+'.snapshot.json')
        body = canonical(payload)
        if target.exists() and target.read_bytes() != body:
            raise ValueError('ARCGIS_SNAPSHOT_CONFLICT')
        if not target.exists():
            with target.open('xb') as out:out.write(body)
        status.update(state='COMPLETE', snapshot_id=identity, records=len(features),
                      schema_sha256=schema, response_receipts=client.receipts[start:],
                      consistency='RECONCILED_ID_SET_NOT_TRANSACTIONAL_ATTRIBUTE_SNAPSHOT')
        return payload, status
    except Exception as error:
        status.update(state='FAILED', error_type=type(error).__name__, error_code=str(error)[:150])
        raise
    finally:
        attempt.write_bytes(canonical(status))


def windsor_observation(feature, snapshot_id, ordinal):
    """Separate portal normalization: preserve feature epoch, OID and attributes.

    Only call after verifying Eastern date metadata and datesInUnknownTimezone=false.
    Does not relabel or modify original CSV TIMESTAMP_NTZ values.
    """
    a = feature['attributes']
    def flag(name):
        if a[name] not in ('True', 'False'):
            raise ValueError('ARCGIS_WINDSOR_FLAG_DOMAIN')
        return a[name] == 'True'
    if type(a['record_date']) is not int or type(a['truck']) is not int:
        raise ValueError('ARCGIS_WINDSOR_TYPES')
    lat, lon = a['latitude'], a['longitude']
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (lat,lon)) or not -90<=lat<=90 or not -180<=lon<=180:
        raise ValueError('ARCGIS_WINDSOR_COORDINATES')
    instant = datetime.fromtimestamp(a['record_date']/1000, timezone.utc)
    return dict(provider='city_of_windsor', city='windsor_on', source='arcgis_snowplow_62',
                source_version_id=snapshot_id, source_record_number=ordinal, snapshot_object_id=a['OBJECTID'],
                event_time_utc=instant.isoformat(), event_time_unzoned=instant.astimezone(ZoneInfo('America/Toronto')).replace(tzinfo=None).isoformat(' '),
                truck_id=str(a['truck']), latitude=lat, longitude=lon, plow_active=flag('plow_status'),
                spreader_active=flag('spreader_status'), engine_active=flag('engine_status'), provider_attributes=a)
