"""Official Windsor weekly discovery and immutable, bounded local staging."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, build_opener
from uuid import uuid4

CATALOGUE_URL = 'https://opendata.citywindsor.ca/details/224'
LICENCE_URL = 'https://opendata.citywindsor.ca/Documents/OpenDataTermsofUse.pdf'
DATASET = 'windsor_snowplow_activity'


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def fingerprint(path: Path) -> str:
    digest = sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def outside_git(path: Path) -> Path:
    path = Path(path).resolve()
    if any((parent / '.git').exists() for parent in (path, *path.parents)):
        raise ValueError('Telemetry staging must be outside every Git working tree')
    return path


@dataclass(frozen=True)
class WeeklySource:
    source_url: str
    source_file_name: str
    covered_start: str
    covered_end_exclusive: str
    source_dataset: str = DATASET

    def __post_init__(self):
        parsed = urlsplit(self.source_url)
        match = re.fullmatch(r'snowplow-(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.csv', self.source_file_name)
        if (parsed.scheme != 'https' or parsed.netloc != 'opendata.citywindsor.ca'
                or parsed.path != '/Uploads/' + self.source_file_name or parsed.query or parsed.fragment
                or not match or self.source_dataset != DATASET):
            raise ValueError('Require an official Windsor weekly CSV URL')
        start, end = (date.fromisoformat(value) for value in match.groups())
        if (start.weekday() != 0 or end - start != timedelta(days=6)
                or self.covered_start != start.isoformat()
                or self.covered_end_exclusive != (end + timedelta(days=1)).isoformat()):
            raise ValueError('Filename and Monday-to-Sunday covered period disagree')

    @classmethod
    def from_url(cls, url: str):
        name = urlsplit(url).path.rsplit('/', 1)[-1]
        match = re.fullmatch(r'snowplow-(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.csv', name)
        if not match:
            raise ValueError('Not a weekly Windsor CSV')
        return cls(url, name, match[1], (date.fromisoformat(match[2]) + timedelta(days=1)).isoformat())


def discover_weekly(html: str, catalogue_url: str = CATALOGUE_URL) -> tuple[WeeklySource, ...]:
    """Discover only real links in supplied official HTML; no guessed downloads."""
    if catalogue_url != CATALOGUE_URL:
        raise ValueError('Unexpected catalogue')
    found = {}
    class Links(HTMLParser):
        def handle_starttag(self, tag, attrs):
            href = dict(attrs).get('href')
            if tag == 'a' and href:
                try:
                    source = WeeklySource.from_url(urljoin(catalogue_url, href))
                except ValueError:
                    return
                found[source.source_url] = source
    Links().feed(html)
    return tuple(sorted(found.values(), key=lambda source: source.covered_start))


@dataclass(frozen=True)
class SourceVersion:
    source: WeeklySource
    source_file_sha256: str
    byte_count: int
    retrieved_at_utc: str
    local_path: str
    retrieval_method: str = 'LOCAL_IMPORT'
    http_content_type: str | None = None

    def __post_init__(self):
        if not re.fullmatch('[0-9a-f]{64}', self.source_file_sha256):
            raise ValueError('Invalid exact file hash')
        if type(self.byte_count) is not int or self.byte_count <= 0:
            raise ValueError('Empty source bytes')
        if self.retrieval_method not in {'LOCAL_IMPORT','OFFICIAL_HTTPS'}:
            raise ValueError('Unknown retrieval method')
        stamp = datetime.fromisoformat(self.retrieved_at_utc)
        if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
            raise ValueError('Retrieval timestamp must be UTC')

    @property
    def version_id(self):
        text = '\0'.join((self.source.source_dataset, self.source.source_file_name, self.source_file_sha256))
        return sha256(text.encode()).hexdigest()

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        return cls(WeeklySource(**value['source']), **{k:v for k,v in value.items() if k != 'source'})

    def verify(self):
        path = Path(self.local_path)
        if not path.is_file() or path.stat().st_size != self.byte_count or fingerprint(path) != self.source_file_sha256:
            raise ValueError('STAGED_BYTES_CHANGED')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LocalStager:
    """Content-addressed files and sidecars. No credentials, retries or overwrites."""
    def __init__(self, root: Path, max_bytes=64 * 1024 * 1024, deadline_seconds=60):
        self.root = outside_git(root)
        if type(max_bytes) is not int or not 1 <= max_bytes <= 256 * 1024 * 1024:
            raise ValueError('Invalid staging byte bound')
        if type(deadline_seconds) is not int or not 1 <= deadline_seconds <= 120:
            raise ValueError('Invalid staging deadline')
        self.max_bytes, self.deadline_seconds = max_bytes, deadline_seconds
        self.root.mkdir(parents=True, exist_ok=True)

    def _event(self, source, state, **details):
        with (self.root/'retrievals.jsonl').open('a',encoding='utf-8') as log:
            log.write(json.dumps(dict(at_utc=utc_now(),source_url=source.source_url,
                filename=source.source_file_name,state=state,**details))+'\n')

    def _stage(self, source, reader, content_type=None, method='LOCAL_IMPORT'):
        scratch = self.root / (uuid4().hex + '.partial')
        began, size = time.monotonic(), 0
        self._event(source,'STARTED',retrieval_method=method)
        try:
            with scratch.open('xb') as output:
                for block in iter(lambda: reader.read(1024 * 1024), b''):
                    size += len(block)
                    if size > self.max_bytes or time.monotonic() - began > self.deadline_seconds:
                        raise ValueError('STAGING_BOUND_EXCEEDED')
                    output.write(block)
            if not size:
                raise ValueError('EMPTY_DOWNLOAD')
            digest = fingerprint(scratch)
            target = self.root / 'raw' / source.source_file_name / digest / source.source_file_name
            target.parent.mkdir(parents=True, exist_ok=True)
            sidecar = target.with_suffix('.version.json')
            if target.exists():
                if fingerprint(target) != digest or not sidecar.exists():
                    raise ValueError('IMMUTABLE_STAGING_CONFLICT')
                version = SourceVersion.from_dict(json.loads(sidecar.read_text(encoding='utf-8')))
                version.verify()
                self._event(source,'IDENTICAL_BYTES',sha256=digest,byte_count=size)
                return version, 'IDENTICAL_BYTES'
            # Exclusive copy, never replace an existing version (including races).
            with target.open('xb') as output, scratch.open('rb') as raw:
                for block in iter(lambda: raw.read(1024 * 1024), b''):
                    output.write(block)
            version = SourceVersion(source, digest, size, utc_now(), str(target),method,content_type)
            with sidecar.open('x', encoding='utf-8') as output:
                json.dump(version.to_dict(), output, indent=2)
            self._event(source,'NEW_BYTES',sha256=digest,byte_count=size)
            return version, 'NEW_BYTES'
        except Exception as error:
            self._event(source,'FAILED',error_type=type(error).__name__,partial_byte_count=size)
            raise
        finally:
            scratch.unlink(missing_ok=True)

    def adopt(self, source: WeeklySource, path: Path):
        """Stage previously downloaded bytes; also useful for fully offline fixtures."""
        with Path(path).open('rb') as raw:
            return self._stage(source, raw)

    def download(self, source: WeeklySource):
        opener = build_opener(NoRedirect())
        self._event(source,'REQUEST_STARTED',retrieval_method='OFFICIAL_HTTPS')
        try:
            response=opener.open(source.source_url, timeout=self.deadline_seconds)
        except Exception as error:
            self._event(source,'REQUEST_FAILED',error_type=type(error).__name__)
            raise
        with response:
            if response.status != 200 or response.url != source.source_url:
                raise ValueError('UNEXPECTED_DOWNLOAD_RESPONSE')
            return self._stage(source, response, response.headers.get('Content-Type', ''),'OFFICIAL_HTTPS')
