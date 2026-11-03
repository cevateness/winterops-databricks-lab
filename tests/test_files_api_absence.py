"""Files API contracts using synthetic negatives and recorded sanitized evidence."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from winterops.workspace_files import (
    WorkspaceContractError, validate_absent_destination, validate_absent_volume_file,
)


class FilesApiAbsenceTests(unittest.TestCase):
    path = '/Volumes/SYNTHETIC/default/raw/immutable/example.csv'
    info = {'@type': 'type.googleapis.com/google.rpc.ErrorInfo',
            'reason': 'FILES_API_FILE_NOT_FOUND', 'domain': 'filesystem.databricks.com'}

    def test_recorded_native_files_response_passes_only_its_service_contract(self):
        root = Path(__file__).resolve().parents[1]
        fixture = json.loads((root / 'tests/fixtures/databricks_files_absence_observed.json').read_text())
        source = root / fixture['provenance']['evidence']
        normalized = source.read_bytes().replace(b'\r\n', b'\n')
        self.assertEqual(hashlib.sha256(normalized).hexdigest(), fixture['provenance']['evidence_sha256'])
        actual = json.loads(normalized)['stopped_gate']['observed_sanitized_body']
        self.assertEqual(fixture['body'], actual)
        self.check(fixture['body'], fixture['http_status'])
        with self.assertRaisesRegex(WorkspaceContractError, 'NOT_FOUND_ERROR_CONTRACT_MISMATCH'):
            validate_absent_destination(fixture['http_status'], fixture['body'],
                                       requested_path='/Shared/SYNTHETIC.sql', expected_path='/Shared/SYNTHETIC.sql')

    def check(self, body=None, http_status=404, **changes):
        args = dict(requested_method='GET', requested_endpoint='/api/2.0/fs/files' + self.path,
                    expected_path=self.path)
        args.update(changes)
        if body is None:
            body = {'error_code': 'NOT_FOUND', 'message': 'Synthetic file missing.', 'details': [self.info]}
        return validate_absent_volume_file(http_status, body, **args)

    def test_observed_files_response_shape_accepts_object_text_and_utf8_bytes(self):
        body = {'error_code': 'NOT_FOUND', 'message': 'Synthetic file missing.', 'details': [self.info]}
        for value in (body, json.dumps(body), json.dumps(body).encode()):
            with self.subTest(kind=type(value).__name__):
                self.assertIsNone(self.check(value))

    def test_optional_details_empty_and_unrelated_typed_details_are_accepted(self):
        base = {'error_code': 'NOT_FOUND', 'message': 'Informational wording can change.'}
        unrelated = [{'@type': 'type.googleapis.com/google.rpc.RequestInfo', 'request_id': 'SYNTHETIC'},
                     {'@type': 'type.googleapis.com/example.FutureHint', 'context': {'value': 1}}]
        for body in (base, dict(base, details=[]), dict(base, details=unrelated),
                     dict(base, details=unrelated + [self.info])):
            with self.subTest(body=body):
                self.check(body)

    def test_csv_and_gzip_destinations_each_require_their_own_pinned_endpoint(self):
        csv = self.path
        gzip = '/Volumes/SYNTHETIC/default/raw/transport/version/hash/bronze.jsonl.gz'
        for path in (csv, gzip):
            self.check(requested_endpoint='/api/2.0/fs/files' + path, expected_path=path)
        with self.assertRaises(WorkspaceContractError):
            self.check(requested_endpoint='/api/2.0/fs/files' + csv, expected_path=gzip)

    def test_wrong_method_endpoint_path_queries_and_encoded_aliases_are_rejected(self):
        endpoints = ('/api/2.0/fs/directories' + self.path, '/api/2.0/workspace/get-status',
                     '/api/2.1/fs/files' + self.path, '/api/2.0/fs/files' + self.path.upper(),
                     '/api/2.0/fs/files' + self.path + '?extra=true',
                     '/api/2.0/fs/files' + self.path + '.other',
                     '/api/2.0/fs/files' + self.path.replace('/Volumes/', '/%56olumes/'),
                     'https://example.invalid/api/2.0/fs/files' + self.path)
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint), self.assertRaises(WorkspaceContractError):
                self.check(requested_endpoint=endpoint)
        for method in ('HEAD', 'POST', 'PUT', 'get', None):
            with self.subTest(method=method), self.assertRaises(WorkspaceContractError):
                self.check(requested_method=method)

    def test_expected_scope_must_be_a_canonical_absolute_volume_file(self):
        for path in ('/Shared/file.sql', '/volumes/c/s/v/file', '/Volumes/c/s/v',
                     '/Volumes/c/s/v/', '/Volumes/c/s/v/../file', '/Volumes/c/s/v//file',
                     '/Volumes/c/s/v/file?x=1', '/Volumes/c/s/v/%66ile', None):
            with self.subTest(path=path), self.assertRaises(WorkspaceContractError):
                self.check(expected_path=path, requested_endpoint='/api/2.0/fs/files' + str(path))

    def test_status_code_alone_and_permission_endpoint_or_workspace_codes_never_pass(self):
        for status in (None, True, 404.0, 200, 204, 206, 400, 401, 403, 409, 500):
            with self.subTest(status=status), self.assertRaises(WorkspaceContractError):
                self.check(http_status=status)
        for code in (None, 404, '404', 'ENDPOINT_NOT_FOUND', 'PERMISSION_DENIED', 'UNAUTHENTICATED',
                     'RESOURCE_DOES_NOT_EXIST', 'INTERNAL_ERROR', 'not_found', True, [], {}):
            with self.subTest(code=code), self.assertRaises(WorkspaceContractError):
                self.check({'error_code': code, 'message': 'File missing.'})

    def test_malformed_json_and_unexpected_error_response_structures_are_rejected(self):
        bodies = ('', ' ', '{', 'null', '[]', 'true', b'\xff', [], 404, True, {},
                  {'error_code': 'NOT_FOUND'}, {'error_code': 'NOT_FOUND', 'message': None},
                  {'error_code': 'NOT_FOUND', 'message': []}, {'error_code': 'NOT_FOUND', 'message': 1},
                  {'error': {'error_code': 'NOT_FOUND', 'message': 'Nested'}},
                  {'error_code': 'NOT_FOUND', 'message': 'Missing', 'success': True},
                  {'error_code': 'NOT_FOUND', 'message': 'Missing', 'details': None},
                  {'error_code': 'NOT_FOUND', 'message': 'Missing', 'details': {}},
                  {'error_code': 'NOT_FOUND', 'message': 'Missing', 'details': [None]},
                  {'error_code': 'NOT_FOUND', 'message': 'Missing', 'details': [{}]},
                  {'error_code': 'NOT_FOUND', 'message': 'Missing', 'details': [{'@type': 1}]})
        for body in bodies:
            with self.subTest(body_type=type(body).__name__), self.assertRaises(WorkspaceContractError):
                self.check(body)
        with self.assertRaises(WorkspaceContractError):
            validate_absent_volume_file(404, None, requested_method='GET',
                requested_endpoint='/api/2.0/fs/files' + self.path, expected_path=self.path)

    def test_duplicate_keys_nonfinite_values_and_oversized_json_are_rejected(self):
        base = '{"error_code":"NOT_FOUND","message":"Missing"'
        bodies = (base + ',"error_code":"NOT_FOUND"}', base + ',"message":"Missing"}',
                  base + ',"details":[{"@type":"type.googleapis.com/google.rpc.ErrorInfo",'
                  '"reason":"FILES_API_FILE_NOT_FOUND","reason":"ENDPOINT_NOT_FOUND",'
                  '"domain":"filesystem.databricks.com"}]}',
                  base + ',"details":[{"@type":"type.googleapis.com/example.Hint","x":NaN}]}',
                  base + ',"details":[{"@type":"type.googleapis.com/example.Hint","x":Infinity}]}',
                  'x' * 1048577, {'error_code': 'NOT_FOUND', 'message': 'x' * 1048577})
        for body in bodies:
            with self.subTest(body_type=type(body).__name__), self.assertRaises(WorkspaceContractError):
                self.check(body)

    def test_supplied_error_info_must_have_exact_reason_and_domain(self):
        for change in (dict(reason='ENDPOINT_NOT_FOUND'), dict(reason='PERMISSION_DENIED'),
                       dict(reason='FILES_API_DIRECTORY_IS_NOT_FOUND'), dict(reason=None),
                       dict(domain='databricks.com'), dict(domain='filesystem.databricks.com.other'),
                       dict(domain=None), dict(unexpected=True)):
            info = dict(self.info, **change)
            for details in ([info], [self.info, info], [info, self.info]):
                with self.subTest(change=change), self.assertRaises(WorkspaceContractError):
                    self.check({'error_code': 'NOT_FOUND', 'message': 'Missing', 'details': details})
        for field in ('reason', 'domain'):
            info = dict(self.info); del info[field]
            with self.subTest(missing=field), self.assertRaises(WorkspaceContractError):
                self.check({'error_code': 'NOT_FOUND', 'message': 'Missing', 'details': [info]})

    def test_error_info_metadata_is_optional_but_if_present_is_a_string_map(self):
        for metadata in ({}, {'key': 'SYNTHETIC'}):
            self.check({'error_code': 'NOT_FOUND', 'message': 'Missing',
                        'details': [dict(self.info, metadata=metadata)]})
        for metadata in (None, [], True, {'key': 1}, {1: 'value'}, {'key': {}}):
            with self.subTest(metadata=metadata), self.assertRaises(WorkspaceContractError):
                self.check({'error_code': 'NOT_FOUND', 'message': 'Missing',
                            'details': [dict(self.info, metadata=metadata)]})

    def test_messages_are_informational_and_never_substitute_for_machine_codes(self):
        self.check({'error_code': 'NOT_FOUND', 'message': ''})
        with self.assertRaises(WorkspaceContractError):
            self.check({'error_code': 'ENDPOINT_NOT_FOUND', 'message': 'The file being accessed is not found.'})

    def test_workspace_absence_still_requires_its_original_resource_code(self):
        args = dict(requested_path='/Shared/SYNTHETIC/file.sql', expected_path='/Shared/SYNTHETIC/file.sql')
        validate_absent_destination(404, {'error_code': 'RESOURCE_DOES_NOT_EXIST'}, **args)
        with self.assertRaises(WorkspaceContractError):
            validate_absent_destination(404, {'error_code': 'NOT_FOUND', 'message': 'Missing',
                                             'details': [self.info]}, **args)
