"""Pure Workspace response gates. No auth, HTTP client, writes or retries.

An import acknowledgement never proves content integrity. Reuse requires exact
get-status metadata followed by explicitly selected export length/hash verification.
Errors use fixed codes so response bodies, object IDs and private paths are not echoed.
"""
import base64
import binascii
from dataclasses import dataclass, field
import hashlib
import json
import re


class WorkspaceContractError(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise WorkspaceContractError(code)


def positive_id(value):
    return type(value) is int and 0 < value < 2**63


def api_path(path):
    require(isinstance(path, str) and bool(re.fullmatch(r'/(?:[A-Za-z0-9_.@-]+/)*[A-Za-z0-9_.@-]+', path))
            and not path.startswith('/Workspace/') and not any(p in ('.', '..') for p in path.split('/')),
            'NONCANONICAL_API_PATH')
    return path


def _json(body, *, allow_empty=False):
    if isinstance(body, (str, bytes)):
        if not body and allow_empty:
            return {}
        require(len(body) <= 1048576, 'RESPONSE_TOO_LARGE')
        def unique(pairs):
            result = {}
            for key, value in pairs:
                require(key not in result, 'DUPLICATE_JSON_KEY')
                result[key] = value
            return result
        try:
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            body = json.loads(body, object_pairs_hook=unique)
        except (ValueError, UnicodeError) as error:
            if isinstance(error, WorkspaceContractError):
                raise
            raise WorkspaceContractError('INVALID_JSON_RESPONSE') from None
    require(type(body) is dict, 'JSON_OBJECT_REQUIRED')
    return body


def _ok(status, body, *, allow_empty=False):
    # 202/204 and missing statuses are ambiguous for this reviewed HTTP-200 API.
    require(type(status) is int and status == 200, 'HTTP_200_REQUIRED_STOP_NO_RETRY')
    return _json(body, allow_empty=allow_empty)


@dataclass(frozen=True)
class ImportAcknowledgement:
    object_id: int | None = field(default=None, repr=False)
    content_verified: bool = field(default=False, init=False)


def validate_import_response(http_status, body):
    """Accept only HTTP 200 + empty body/object or exactly a positive object_id.

    None is an ambiguous/missing parsed body, not proof of an empty wire body.
    Actual empty wire bytes/text are accepted; JSON null and unknown fields fail.
    """
    body = _ok(http_status, body, allow_empty=True)
    require(not body or set(body) == {'object_id'} and positive_id(body['object_id']),
            'UNEXPECTED_IMPORT_RESPONSE')
    return ImportAcknowledgement(body.get('object_id'))


@dataclass(frozen=True)
class FileContract:
    path: str
    byte_count: int
    sha256: str

    def __post_init__(self):
        api_path(self.path)
        require(type(self.byte_count) is int and 0 < self.byte_count <= 262144, 'INVALID_FILE_SIZE_CONTRACT')
        require(isinstance(self.sha256, str) and bool(re.fullmatch('[0-9a-f]{64}', self.sha256)), 'INVALID_HASH_CONTRACT')


def validate_object_status(http_status, body, *, requested_path, expected_path, object_type,
                           expected_object_id=None, expected_bytes=None):
    """Validate FILE/DIRECTORY identity; return its private positive object ID."""
    api_path(expected_path)
    require(requested_path == expected_path, 'STATUS_REQUEST_PATH_MISMATCH')
    require(object_type in ('FILE', 'DIRECTORY'), 'UNSUPPORTED_OBJECT_CONTRACT')
    body = _ok(http_status, body)
    require(not any(k in body for k in ('error', 'error_code', 'message')), 'ERROR_IN_STATUS_RESPONSE')
    require(body.get('path') == expected_path, 'STATUS_PATH_MISMATCH')
    require(body.get('object_type') == object_type, 'OBJECT_TYPE_MISMATCH')
    require(positive_id(body.get('object_id')), 'INVALID_STATUS_OBJECT_ID')
    if expected_object_id is not None:
        require(positive_id(expected_object_id) and body['object_id'] == expected_object_id, 'OBJECT_ID_CHANGED')
    if expected_bytes is not None:
        require(type(expected_bytes) is int and expected_bytes > 0, 'INVALID_EXPECTED_BYTES')
        if 'size' in body:
            require(type(body['size']) is int and body['size'] == expected_bytes, 'STATUS_SIZE_MISMATCH')
    info = body.get('directory_info')
    require(info is None or type(info) is dict, 'INVALID_DIRECTORY_INFO')
    require(info is None or info.get('is_git_folder', False) is False, 'GIT_FOLDER_NOT_APPROVED')
    return body['object_id']


@dataclass(frozen=True)
class VerifiedExport:
    byte_count: int
    sha256: str


def verify_file_export(http_status, body, contract, *, requested_path, export_format, direct_download):
    """Verify an explicitly selected RAW or AUTO JSON export; never fall back."""
    require(isinstance(contract, FileContract), 'FILE_CONTRACT_REQUIRED')
    require(requested_path == contract.path, 'EXPORT_REQUEST_PATH_MISMATCH')
    require(export_format in ('RAW', 'AUTO') and direct_download is False, 'EXPLICIT_FILE_JSON_EXPORT_REQUIRED')
    body = _ok(http_status, body)
    require('content' in body and set(body) <= {'content', 'file_type'}, 'UNEXPECTED_EXPORT_RESPONSE')
    if 'file_type' in body:
        require(isinstance(body['file_type'], str) and 0 < len(body['file_type']) <= 64, 'INVALID_EXPORT_FILE_TYPE')
    content = body['content']
    require(isinstance(content, str) and len(content) == 4 * ((contract.byte_count + 2) // 3), 'EXPORT_ENCODED_SIZE_MISMATCH')
    try:
        decoded = base64.b64decode(content, validate=True)
    except (ValueError, binascii.Error):
        raise WorkspaceContractError('INVALID_BASE64_EXPORT') from None
    require(base64.b64encode(decoded).decode('ascii') == content, 'NONCANONICAL_BASE64_EXPORT')
    require(len(decoded) == contract.byte_count, 'EXPORT_DECODED_SIZE_MISMATCH')
    require(hashlib.sha256(decoded).hexdigest() == contract.sha256, 'EXPORT_SHA256_MISMATCH')
    return VerifiedExport(len(decoded), contract.sha256)


def verify_raw_export(http_status, body, contract, *, requested_path, export_format, direct_download):
    """Historical RAW-only entrypoint; AUTO must be explicitly selected elsewhere."""
    require(export_format == 'RAW', 'RAW_JSON_EXPORT_REQUIRED')
    return verify_file_export(http_status, body, contract, requested_path=requested_path,
        export_format=export_format, direct_download=direct_download)


@dataclass(frozen=True)
class ReusableWorkspaceFile:
    path: str = field(repr=False)
    object_id: int = field(repr=False)
    byte_count: int
    sha256: str
    action: str = field(default='REUSE', init=False)
    import_required: bool = field(default=False, init=False)
    overwrite: bool = field(default=False, init=False)


def verify_existing_file(contract, *, status_http, status_body, status_path,
                         export_http, export_body, export_path, export_format,
                         direct_download, expected_object_id):
    """Produce a reuse-only decision only after both independent response gates."""
    require(isinstance(contract, FileContract), 'FILE_CONTRACT_REQUIRED')
    require(positive_id(expected_object_id), 'SAVED_IMPORT_OBJECT_ID_REQUIRED')
    object_id = validate_object_status(status_http, status_body, requested_path=status_path,
        expected_path=contract.path, object_type='FILE', expected_object_id=expected_object_id,
        expected_bytes=contract.byte_count)
    proof = verify_file_export(export_http, export_body, contract, requested_path=export_path,
        export_format=export_format, direct_download=direct_download)
    return ReusableWorkspaceFile(contract.path, object_id, proof.byte_count, proof.sha256)


def validate_absent_destination(http_status, body, *, requested_path, expected_path):
    api_path(expected_path)
    require(requested_path == expected_path, 'ABSENCE_REQUEST_PATH_MISMATCH')
    require(type(http_status) is int and http_status == 404, 'DESTINATION_NOT_PROVEN_ABSENT')
    require(_json(body).get('error_code') == 'RESOURCE_DOES_NOT_EXIST', 'NOT_FOUND_ERROR_CONTRACT_MISMATCH')


def validate_unused_job_name(http_status, body, *, requested_name, expected_name):
    require(isinstance(expected_name, str) and expected_name and requested_name == expected_name, 'JOB_NAME_REQUEST_MISMATCH')
    body = _ok(http_status, body)
    require(not any(k in body for k in ('error', 'error_code', 'message')), 'ERROR_IN_JOB_LIST')
    require(not body.get('next_page_token') and body.get('has_more', False) is False, 'JOB_LIST_INCOMPLETE')
    require(type(body.get('jobs', [])) is list and body.get('jobs', []) == [], 'JOB_NAME_IN_USE')
