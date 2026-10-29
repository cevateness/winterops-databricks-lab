"""Serialized local V2 manifest, incremental reference store and recovery.

All record-bearing files/databases must live outside Git. Each data-stage commit
is atomic in SQLite; the multi-stage workflow is deliberately recoverable rather
than pretending to be one Bronze/Silver/manifest transaction.
"""
from __future__ import annotations

from contextlib import contextmanager
import gzip
import hashlib
import io
import json
from pathlib import Path
import sqlite3

from winterops.foundation import (PIPELINE_VERSION, QualityPolicy, aggregate_quality, canonical,
                                 processing_key, read_bronze, silver_rows)
from winterops.sources import SourceVersion, outside_git, utc_now

FAILURE_CODES = {'SOURCE_SCHEMA_DRIFT','SOURCE_RECORD_BOUND_EXCEEDED','STAGED_BYTES_CHANGED',
    'MIXED_SOURCE_VERSIONS','BRONZE_SILVER_COUNT_MISMATCH_OR_EMPTY','OBSERVATION_IDENTITY_MISMATCH',
    'PERSISTED_CONTENT_CONFLICT_REQUIRES_EXPLICIT_REPAIR','COMPLETE_CONTENT_MISMATCH_REQUIRES_EXPLICIT_REPAIR',
    'PERSISTED_CONTENT_RECONCILIATION_FAILED','RECORD_SEQUENCE_MISMATCH','MIXED_WRITE_SCOPE'}


def rows_digest(rows):
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode())
        digest.update(b'\n')
    return digest.hexdigest()


class LocalManifest:
    def __init__(self, path: Path):
        self.path = outside_git(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=10)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS versions (
            version_id TEXT PRIMARY KEY, filename TEXT NOT NULL, sha256 TEXT NOT NULL,
            metadata_json TEXT NOT NULL, first_seen_utc TEXT NOT NULL, last_seen_utc TEXT NOT NULL,
            seen_count INTEGER NOT NULL, UNIQUE(filename,sha256));
          CREATE TABLE IF NOT EXISTS runs (
            processing_key TEXT PRIMARY KEY, version_id TEXT NOT NULL REFERENCES versions(version_id),
            pipeline_version TEXT NOT NULL, policy_sha256 TEXT NOT NULL,
            status TEXT NOT NULL, last_successful_stage TEXT, attempts INTEGER NOT NULL,
            bronze_rows INTEGER, silver_rows INTEGER, report_json TEXT, error_code TEXT,
            updated_at_utc TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS attempts (
            attempt_id INTEGER PRIMARY KEY, processing_key TEXT NOT NULL REFERENCES runs(processing_key),
            started_at_utc TEXT NOT NULL, finished_at_utc TEXT, status TEXT NOT NULL, error_code TEXT);
          CREATE TABLE IF NOT EXISTS bronze (
            scope_key TEXT NOT NULL REFERENCES versions(version_id), record_number INTEGER NOT NULL,
            row_json TEXT NOT NULL, PRIMARY KEY(scope_key,record_number));
          CREATE TABLE IF NOT EXISTS silver (
            scope_key TEXT NOT NULL REFERENCES runs(processing_key), record_number INTEGER NOT NULL,
            row_json TEXT NOT NULL, PRIMARY KEY(scope_key,record_number));
        ''')

    def close(self):
        self.db.close()

    @contextmanager
    def writer_lock(self):
        lock = self.path.with_suffix(self.path.suffix+'.lock')
        try:
            with lock.open('x',encoding='utf-8') as out:
                out.write('Serialized WinterOps writer. A crash requires manual lock review.\n')
        except FileExistsError:
            raise RuntimeError('WRITER_LOCK_EXISTS_REVIEW_BEFORE_RECOVERY') from None
        try:
            yield
        finally:
            lock.unlink()

    def register(self, version: SourceVersion):
        version.verify()
        existing = self.db.execute('SELECT metadata_json FROM versions WHERE version_id=?',(version.version_id,)).fetchone()
        revision = self.db.execute('SELECT COUNT(*) FROM versions WHERE filename=?',(version.source.source_file_name,)).fetchone()[0]
        with self.db:
            if existing:
                saved = SourceVersion.from_dict(json.loads(existing[0]))
                saved.verify()
                if saved.source != version.source:
                    raise ValueError('SOURCE_IDENTITY_CONFLICT')
                self.db.execute('UPDATE versions SET last_seen_utc=?, seen_count=seen_count+1 WHERE version_id=?',(utc_now(),version.version_id))
                return saved, 'IDENTICAL_VERSION'
            self.db.execute('INSERT INTO versions VALUES (?,?,?,?,?,?,?)',
                (version.version_id,version.source.source_file_name,version.source_file_sha256,
                 canonical(version.to_dict()),utc_now(),utc_now(),1))
        return version, 'NEW_REVISION' if revision else 'NEW_SOURCE'

    def select_version(self, filename, sha256=None):
        sql,args='SELECT metadata_json FROM versions WHERE filename=?',[filename]
        if sha256 is not None:
            sql+=' AND sha256=?';args.append(sha256)
        found=self.db.execute(sql,args).fetchall()
        if len(found)!=1:
            raise ValueError('REQUIRE_ONE_EXPLICIT_SOURCE_VERSION')
        return SourceVersion.from_dict(json.loads(found[0][0]))

    def run(self, key):
        cursor=self.db.execute('SELECT * FROM runs WHERE processing_key=?',(key,))
        row=cursor.fetchone()
        return dict(zip([c[0] for c in cursor.description],row)) if row else None

    def begin(self, version, policy):
        key=processing_key(version,policy)
        with self.db:
            self.db.execute('''INSERT INTO runs
              (processing_key,version_id,pipeline_version,policy_sha256,status,attempts,updated_at_utc)
              VALUES (?,?,?,?,?,1,?) ON CONFLICT(processing_key) DO UPDATE SET
              status='PROCESSING',attempts=attempts+1,error_code=NULL,updated_at_utc=excluded.updated_at_utc''',
              (key,version.version_id,PIPELINE_VERSION,policy.policy_sha256,'PROCESSING',utc_now()))
            self.db.execute("UPDATE attempts SET status='INTERRUPTED',finished_at_utc=? WHERE processing_key=? AND status='PROCESSING'",(utc_now(),key))
            return self.db.execute('INSERT INTO attempts (processing_key,started_at_utc,status) VALUES (?,?,?)',(key,utc_now(),'PROCESSING')).lastrowid

    def mark(self, key, status, **fields):
        allowed={'last_successful_stage','bronze_rows','silver_rows','report_json','error_code'}
        if not set(fields)<=allowed or status not in {'BRONZE_WRITTEN','SILVER_WRITTEN','COMPLETE','FAILED'}:
            raise ValueError('Invalid manifest transition')
        with self.db:
            self.db.execute('UPDATE runs SET status=?,updated_at_utc=?'+''.join(','+k+'=?' for k in fields)+' WHERE processing_key=?',
                [status,utc_now(),*fields.values(),key])

    def finish_attempt(self, attempt, status, error=None):
        with self.db:
            self.db.execute('UPDATE attempts SET status=?,error_code=?,finished_at_utc=? WHERE attempt_id=?',(status,error,utc_now(),attempt))

    def rows(self, layer, key):
        if layer not in {'bronze','silver'}: raise ValueError('Unknown layer')
        return [json.loads(row[0]) for row in self.db.execute('SELECT row_json FROM '+layer+' WHERE scope_key=? ORDER BY record_number',(key,))]

    def write_rows(self, layer, key, rows, repair=False):
        if layer not in {'bronze','silver'} or not rows:
            raise ValueError('Nonempty exact layer scope required')
        numbers=[row['source_record_number'] for row in rows]
        if numbers!=list(range(1,len(rows)+1)):
            raise ValueError('RECORD_SEQUENCE_MISMATCH')
        scope_field='source_version_id' if layer=='bronze' else 'processing_key'
        if any(row[scope_field]!=key for row in rows):
            raise ValueError('MIXED_WRITE_SCOPE')
        prior=self.rows(layer,key)
        if rows_digest(prior)==rows_digest(rows): return 'IDENTICAL'
        if prior and not repair:
            raise ValueError('PERSISTED_CONTENT_CONFLICT_REQUIRES_EXPLICIT_REPAIR')
        with self.db:
            self.db.execute('DELETE FROM '+layer+' WHERE scope_key=?',(key,))
            self.db.executemany('INSERT INTO '+layer+' VALUES (?,?,?)',
                ((key,row['source_record_number'],canonical(row)) for row in rows))
        return 'WRITTEN'


def process_local(manifest: LocalManifest, version: SourceVersion, policy=QualityPolicy(), *,
                  repair=False, max_records=500000, after_stage=None):
    """One explicit attempt, no retry loop. A later invocation resumes safely.

    COMPLETE is skipped only after full ordered content comparison, not row count.
    Source revisions and changed policies get new keys; neither replaces old rows.
    after_stage is an optional caller hook for progress/failure-injection tests.
    """
    with manifest.writer_lock():
        version, discovery=manifest.register(version)
        key=processing_key(version,policy)
        prior=manifest.run(key)
        attempt=None
        try:
            bronze=list(read_bronze(version,max_records))
            silver=silver_rows(bronze,version,policy)
            report=aggregate_quality(bronze,silver,version,policy)
            if prior and prior['status']=='COMPLETE':
                same=(rows_digest(manifest.rows('bronze',version.version_id))==rows_digest(bronze)
                      and rows_digest(manifest.rows('silver',key))==rows_digest(silver))
                if same:
                    return dict(action='SKIP_VERIFIED',discovery=discovery,report=report)
                if not repair:
                    raise ValueError('COMPLETE_CONTENT_MISMATCH_REQUIRES_EXPLICIT_REPAIR')
            attempt=manifest.begin(version,policy)
            manifest.write_rows('bronze',version.version_id,bronze,repair)
            manifest.mark(key,'BRONZE_WRITTEN',bronze_rows=len(bronze),last_successful_stage='BRONZE_WRITTEN')
            if after_stage: after_stage('bronze')
            manifest.write_rows('silver',key,silver,repair)
            manifest.mark(key,'SILVER_WRITTEN',silver_rows=len(silver),last_successful_stage='SILVER_WRITTEN')
            if after_stage: after_stage('silver')
            if (rows_digest(manifest.rows('bronze',version.version_id))!=rows_digest(bronze)
                    or rows_digest(manifest.rows('silver',key))!=rows_digest(silver)):
                raise ValueError('PERSISTED_CONTENT_RECONCILIATION_FAILED')
            manifest.mark(key,'COMPLETE',last_successful_stage='COMPLETE',report_json=canonical(report),error_code=None)
            manifest.finish_attempt(attempt,'COMPLETE')
            return dict(action='PROCESSED',discovery=discovery,report=report)
        except Exception as error:
            # Exception messages may contain source contents. Retain only a type.
            if attempt is None: attempt=manifest.begin(version,policy)
            code=str(error) if str(error) in FAILURE_CODES else type(error).__name__
            manifest.mark(key,'FAILED',error_code=code)
            manifest.finish_attempt(attempt,'FAILED',code)
            raise


def export_bronze(manifest, version, output_root: Path, *, compression=None):
    """Immutable NDJSON bridge; optional gzip changes transport bytes only.

    Fingerprints distinguish the original CSV, decoded NDJSON and upload bytes.
    Gzip headers omit filename/time; no observation or manifest state is changed.
    """
    if compression not in (None,'gzip'):
        raise ValueError('Unsupported artifact compression')
    root=outside_git(output_root)
    rows=manifest.rows('bronze',version.version_id)
    version.verify()
    if not rows: raise ValueError('No verified Bronze version')
    if rows_digest(rows)!=rows_digest(list(read_bronze(version))):
        raise ValueError('EXPORT_SOURCE_RECONCILIATION_FAILED')
    data=''.join(canonical(row)+'\n' for row in rows).encode('utf-8')
    if len(data)>256*1024*1024:
        raise ValueError('EXPORT_ARTIFACT_BOUND_EXCEEDED')
    decoded_digest=hashlib.sha256(data).hexdigest()
    decoded_bytes=len(data)
    if compression=='gzip':
        buffer=io.BytesIO()
        with gzip.GzipFile(filename='',mode='wb',fileobj=buffer,mtime=0,compresslevel=6) as encoded:
            encoded.write(data)
        data=buffer.getvalue()
    if len(data)>256*1024*1024:
        raise ValueError('EXPORT_ARTIFACT_BOUND_EXCEEDED')
    digest=hashlib.sha256(data).hexdigest()
    target=root/version.version_id/digest/('bronze.jsonl.gz' if compression=='gzip' else 'bronze.jsonl')
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if target.read_bytes()!=data: raise ValueError('IMMUTABLE_EXPORT_CONFLICT')
    else:
        with target.open('xb') as output: output.write(data)
    return dict(source_version_id=version.version_id,artifact_sha256=digest,row_count=len(rows),local_path=str(target),
                compression=compression or 'none',uncompressed_sha256=decoded_digest,
                artifact_bytes=len(data),uncompressed_bytes=decoded_bytes)
