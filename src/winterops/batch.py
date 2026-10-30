"""Pinned on-demand batch requests and declarative Jobs files; no remote client.

Acquisition/export/upload are separate contracts. Rendering never verifies remote
bytes or authorizes deployment. A job is prepared for one exact processing key.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re

from winterops.foundation import PIPELINE_VERSION, QualityPolicy, processing_key
from winterops.landing import OriginalLanding, VOLUME
from winterops.sources import SourceVersion, WeeklySource, outside_git
from winterops.spark_ingestion import DevelopmentTargets


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class BatchRequest:
    version: SourceVersion
    artifact_path: str
    artifact_sha256: str
    artifact_bytes: int
    expected_rows: int
    header_rows: int
    valid_rows: int
    invalid_rows: int
    original_csv_path: str
    policy: QualityPolicy = QualityPolicy()
    targets: DevelopmentTargets = DevelopmentTargets()
    prior_attempts: int = 0
    write_policy: str = 'complete_only'

    def __post_init__(self):
        if (not isinstance(self.version, SourceVersion) or not isinstance(self.policy, QualityPolicy)
                or not isinstance(self.targets, DevelopmentTargets)):
            raise ValueError('Validated V2 contracts required')
        if (type(self.expected_rows) is not int or not 1 <= self.expected_rows <= 500000
                or any(type(n) is not int or not 0 <= n <= self.expected_rows
                       for n in (self.header_rows, self.valid_rows, self.invalid_rows))
                or self.header_rows + self.valid_rows + self.invalid_rows != self.expected_rows
                or type(self.artifact_bytes) is not int or not 1 <= self.artifact_bytes <= 256 * 1024 * 1024
                or type(self.prior_attempts) is not int or not 0 <= self.prior_attempts < 1000
                or self.write_policy not in ('complete_only', 'append_missing')
                or not re.fullmatch('[0-9a-f]{64}', self.artifact_sha256)):
            raise ValueError('Exact bounded fingerprints, quality counts and attempt required')
        prefix = f'{VOLUME}/foundation_v2_dev/{self.version.version_id}/{self.artifact_sha256}/bronze.jsonl'
        if self.artifact_path not in (prefix, prefix + '.gz'):
            raise ValueError('Artifact must have the exact immutable V2 version/hash path')
        # Reuse the original source landing validation, including the legacy path.
        self.selection
        self.landing

    @property
    def selection(self):
        from winterops.unified_gold import SelectedVersion
        return SelectedVersion(self.version.source.source_file_name, self.version.source_file_sha256,
                               self.version.version_id, self.key, self.expected_rows,
                               self.original_csv_path, self.policy)

    @property
    def key(self):
        return processing_key(self.version, self.policy)

    @property
    def landing(self):
        direct = VOLUME + '/' + self.version.source.source_file_name
        return OriginalLanding(self.version.source, self.version.source_file_sha256,
                               self.version.byte_count, direct if self.original_csv_path == direct else None)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, value):
        value = dict(value)
        value['version'] = SourceVersion.from_dict(value['version'])
        value['policy'] = QualityPolicy(**value.get('policy', {}))
        value['targets'] = DevelopmentTargets(**value.get('targets', {}))
        return cls(**value)

    @property
    def sha256(self):
        return digest(dict(contract='winterops-on-demand-v1', pipeline=PIPELINE_VERSION,
                           request=self.to_dict()))


@dataclass(frozen=True)
class Sql:
    text: str

    def render(self):
        return self.text.rstrip(';') + ';'


@dataclass(frozen=True)
class When:
    predicate: str
    steps: tuple

    def render(self):
        body = '\n'.join(step.render() for step in self.steps)
        return f'IF {self.predicate} THEN\n{body}\nEND IF;'


@dataclass(frozen=True)
class Task:
    key: str
    steps: tuple
    dependencies: tuple = ()
    run_if: str = 'ALL_SUCCESS'

    def render(self):
        return '-- PRIVATE GENERATED SQL. Review the pinned request before deployment.\nBEGIN\n' + '\n'.join(
            step.render() for step in self.steps) + '\nEND;\n'


def job_definition(request, warehouse_id, workspace_root):
    """Jobs create-settings JSON; no schedules, clusters, deployment or run-now."""
    from winterops.batch_sql import tasks
    if (not re.fullmatch('[0-9a-f]{16}', warehouse_id)
            or not re.fullmatch(r'/Workspace/(?:[A-Za-z0-9_.@-]+/)*[A-Za-z0-9_.@-]+', workspace_root)
            or any(part in ('.', '..') for part in workspace_root.split('/'))):
        raise ValueError('Explicit existing warehouse and safe private workspace file root required')
    params = dict(source_version_id=request.version.version_id, processing_key=request.key,
                  request_sha256=request.sha256, execution_mode='verify', recovery='deny')
    result = dict(name='WinterOps on-demand V1', max_concurrent_runs=1,
                queue={'enabled': False}, timeout_seconds=600,
                parameters=[dict(name=k, default=v) for k, v in params.items()],
                tasks=[dict(task_key=t.key, depends_on=[{'task_key': d} for d in t.dependencies],
                            run_if=t.run_if, timeout_seconds=90, max_retries=0, retry_on_timeout=False,
                            sql_task=dict(warehouse_id=warehouse_id,
                                          file=dict(source='WORKSPACE', path=f'{workspace_root}/{request.sha256}/{t.key}.sql'),
                                          parameters={k: '{{job.parameters.' + k + '}}' for k in params}))
                       for t in tasks(request)])
    result['tasks'][-1]['sql_task']['parameters']['batch_preflight_state'] = '{{tasks.preflight.result_state}}'
    return result


def prepare_job(request, output_root, warehouse_id, workspace_root):
    """Write an immutable private review package outside every Git working tree."""
    from winterops.batch_sql import tasks
    job = job_definition(request, warehouse_id, workspace_root)
    rendered = {t.key + '.sql': t.render() for t in tasks(request)}
    rendered['job.json'] = json.dumps(job, indent=2) + '\n'
    rendered['request.json'] = json.dumps(request.to_dict(), indent=2) + '\n'
    hashes = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in rendered.items()}
    sql_bytes = {name: len(content.encode()) for name, content in rendered.items() if name.endswith('.sql')}
    if any(n > 256 * 1024 for n in sql_bytes.values()) or sum(sql_bytes.values()) > 1024 * 1024:
        raise ValueError('JOB_SQL_UPLOAD_BOUND_EXCEEDED')
    review = dict(status='PREPARED_NOT_DEPLOYED_NOT_EXECUTED', request_sha256=request.sha256,
                  files_sha256=hashes, hashed_file_count=len(rendered), package_file_count=len(rendered) + 1,
                  sql_upload_bytes=sql_bytes, sql_upload_total_bytes=sum(sql_bytes.values()), tasks=len(job['tasks']),
                  maximum_active_tasks=1, job_timeout_seconds=600, task_timeout_seconds=90,
                  retries=0, schedule=None, targets=list(request.targets.names),
                  default_mode='verify', write_policy=request.write_policy, publication='ELIGIBILITY_ONLY_NO_GOLD_DDL')
    rendered['review.json'] = json.dumps(review, indent=2) + '\n'
    target = outside_git(Path(output_root) / request.sha256)
    target.mkdir(parents=True, exist_ok=True)
    # Check all existing files before writing any; never refresh an old package.
    for name, content in rendered.items():
        path = target / name
        if path.exists() and path.read_text(encoding='utf-8') != content:
            raise ValueError('IMMUTABLE_JOB_PACKAGE_CONFLICT')
    for name, content in rendered.items():
        path = target / name
        if not path.exists():
            with path.open('x', encoding='utf-8', newline='\n') as out:
                out.write(content)
    return review


def synthetic_request():
    """Rendering fixture only. Hashes/files are deliberately fictitious."""
    source = WeeklySource.from_url('https://opendata.citywindsor.ca/Uploads/snowplow-2026-01-05_2026-01-11.csv')
    version = SourceVersion(source, '1' * 64, 1234, '2026-01-26T00:00:00+00:00',
                            'SYNTHETIC_ONLY/input.csv')
    artifact_hash = '2' * 64
    return BatchRequest(version, f'{VOLUME}/foundation_v2_dev/{version.version_id}/{artifact_hash}/bronze.jsonl.gz',
                        artifact_hash, 1234, 4, 1, 2, 1, OriginalLanding(source, version.source_file_sha256, version.byte_count).path)
