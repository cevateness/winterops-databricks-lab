"""Synthetic response contracts; never authenticate, upload or call an API."""
import base64
from dataclasses import replace
import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from winterops.workspace_files import (
    FileContract, WorkspaceContractError, validate_import_response,
    validate_object_status, verify_raw_export, validate_absent_destination,
    validate_unused_job_name, verify_existing_file,
)


class WorkspaceFileTests(unittest.TestCase):
    def setUp(self):
        self.data = b'-- SYNTHETIC SQL\nSELECT 1;\n'
        self.file = FileContract('/Shared/SYNTHETIC/preflight.sql', len(self.data), hashlib.sha256(self.data).hexdigest())
        self.status = dict(path=self.file.path, object_type='FILE', object_id=42, size=len(self.data))
        self.export = dict(content=base64.b64encode(self.data).decode())

    def status_check(self, body=None, **kwargs):
        return validate_object_status(200, self.status if body is None else body,
            requested_path=self.file.path, expected_path=self.file.path, object_type='FILE',
            expected_bytes=self.file.byte_count, **kwargs)

    def export_check(self, body=None, **kwargs):
        args = dict(requested_path=self.file.path, export_format='RAW', direct_download=False)
        args.update(kwargs)
        return verify_raw_export(200, self.export if body is None else body, self.file, **args)

    def test_import_empty_and_observed_object_id_variants(self):
        for body in ({}, '', b'', '{}', b'{}', {'object_id': 42}, b'{"object_id":42}'):
            with self.subTest(body=body):
                ack = validate_import_response(200, body)
                self.assertFalse(ack.content_verified)
                self.assertEqual(ack.object_id, 42 if 'object_id' in str(body) else None)

    def test_import_rejects_invalid_ids_and_extra_fields(self):
        for body in ({'object_id': v} for v in (0, -1, True, False, None, '42', 42.0, [], {}, 2**63)):
            with self.subTest(body=body), self.assertRaises(WorkspaceContractError):
                validate_import_response(200, body)
        for body in ({'object_id': 42, 'unexpected': 1}, {'error_code': 'ERROR'}, {'ok': True}):
            with self.subTest(body=body), self.assertRaises(WorkspaceContractError):
                validate_import_response(200, body)

    def test_import_rejects_error_missing_or_ambiguous_http_status(self):
        for status in (None, True, '200', 0, 201, 202, 204, 301, 400, 401, 404, 409, 429, 500):
            for body in ({}, {'object_id': 42}):
                with self.subTest(status=status), self.assertRaises(WorkspaceContractError):
                    validate_import_response(status, body)

    def test_import_rejects_missing_malformed_and_duplicate_json(self):
        for body in (None, [], (), 42, True, 'null', '[]', ' ', '{', b'\xff',
                     '{"object_id":1,"object_id":2}', '{"object_id":1,"object_id":1}', 'x'*1048577):
            with self.subTest(body_type=type(body).__name__), self.assertRaises(WorkspaceContractError):
                validate_import_response(200, body)

    def test_acknowledgement_hides_id_and_never_proves_contents(self):
        ack = validate_import_response(200, {'object_id': 123456789})
        self.assertNotIn('123456789', repr(ack))
        self.assertFalse(ack.content_verified)
        bad = dict(content=base64.b64encode(b'X'*len(self.data)).decode())
        with self.assertRaises(WorkspaceContractError):
            self.export_check(bad)

    def test_status_requires_exact_path_file_identity_and_optional_size(self):
        self.assertEqual(self.status_check(expected_object_id=42), 42)
        without_size = dict(self.status); without_size.pop('size')
        self.assertEqual(self.status_check(without_size), 42)
        for changed in (dict(path=self.file.path.upper()), dict(path=self.file.path+'.other'),
                        dict(object_type='NOTEBOOK'), dict(object_type='DIRECTORY'),
                        dict(object_id=0), dict(object_id=True), dict(size=len(self.data)+1), dict(size=True),
                        dict(error_code='ERROR'), dict(directory_info='unexpected')):
            with self.subTest(changed=changed), self.assertRaises(WorkspaceContractError):
                self.status_check(dict(self.status, **changed))
        with self.assertRaises(WorkspaceContractError):
            self.status_check(expected_object_id=43)

    def test_status_rejects_wrong_request_path_or_http(self):
        for code in (None, 202, 404, 500):
            with self.subTest(code=code), self.assertRaises(WorkspaceContractError):
                validate_object_status(code, self.status, requested_path=self.file.path,
                    expected_path=self.file.path, object_type='FILE')
        with self.assertRaises(WorkspaceContractError):
            validate_object_status(200, self.status, requested_path='/Shared/OTHER/preflight.sql',
                expected_path=self.file.path, object_type='FILE')

    def test_existing_directories_are_verified_without_create_or_replacement(self):
        path='/Shared/SYNTHETIC'
        body=dict(path=path, object_type='DIRECTORY', object_id=10, directory_info={'is_git_folder': False})
        self.assertEqual(validate_object_status(200, body, requested_path=path, expected_path=path,
            object_type='DIRECTORY', expected_object_id=10), 10)
        for change in (dict(object_type='REPO'), dict(object_type='FILE'), dict(object_id=11),
                       dict(directory_info={'is_git_folder': True})):
            with self.subTest(change=change), self.assertRaises(WorkspaceContractError):
                validate_object_status(200, dict(body, **change), requested_path=path, expected_path=path,
                    object_type='DIRECTORY', expected_object_id=10)

    def test_raw_export_proves_exact_decoded_hash_and_size_only(self):
        proof=self.export_check()
        self.assertEqual((proof.byte_count, proof.sha256), (len(self.data), hashlib.sha256(self.data).hexdigest()))
        self.assertNotIn(self.data.decode(), repr(proof))
        self.assertEqual(self.export_check(dict(self.export, file_type='SQL')), proof)

    def test_export_rejects_wrong_context_and_non_success_http(self):
        for args in (dict(export_format='SOURCE'), dict(export_format='AUTO'), dict(direct_download=True),
                     dict(direct_download=0), dict(requested_path=self.file.path+'.other')):
            with self.subTest(args=args), self.assertRaises(WorkspaceContractError):
                self.export_check(**args)
        for code in (None, 204, 404, 500):
            with self.subTest(code=code), self.assertRaises(WorkspaceContractError):
                verify_raw_export(code,self.export,self.file,requested_path=self.file.path,export_format='RAW',direct_download=False)

    def test_export_rejects_corruption_truncation_unknown_and_malformed_payloads(self):
        for body in ({}, {'content': None}, {'content': self.data}, {'content':'!'*len(self.export['content'])},
                     {'content': self.export['content'][:-4]}, {'content':self.export['content']+'\n'},
                     dict(self.export, unexpected=True), dict(self.export, file_type=False),
                     {'content':base64.b64encode(self.data[:-1]).decode()},
                     {'content':base64.b64encode(b'X'*len(self.data)).decode()}):
            with self.subTest(keys=list(body)), self.assertRaises(WorkspaceContractError):
                self.export_check(body)
        with self.assertRaises(WorkspaceContractError):
            verify_raw_export(200,self.export,replace(self.file,sha256='0'*64),
                requested_path=self.file.path,export_format='RAW',direct_download=False)

    def test_absence_requires_exact_resource_not_found_not_permission_failure(self):
        missing={'error_code':'RESOURCE_DOES_NOT_EXIST','message':'synthetic missing'}
        validate_absent_destination(404,missing,requested_path=self.file.path,expected_path=self.file.path)
        for code,body in ((200,{}),(403,missing),(500,missing),(404,{}),(404,{'error_code':'PERMISSION_DENIED'})):
            with self.subTest(code=code), self.assertRaises(WorkspaceContractError):
                validate_absent_destination(code,body,requested_path=self.file.path,expected_path=self.file.path)

    def test_job_name_requires_empty_complete_listing(self):
        for body in ({}, {'jobs':[]}, {'jobs':[], 'has_more':False}):
            validate_unused_job_name(200,body,requested_name='SYN Job',expected_name='SYN Job')
        for body in ({'jobs':[{'job_id':1}]}, {'jobs':None}, {'has_more':True}, {'next_page_token':'more'}, {'error_code':'ERROR'}):
            with self.subTest(body=body), self.assertRaises(WorkspaceContractError):
                validate_unused_job_name(200,body,requested_name='SYN Job',expected_name='SYN Job')
        with self.assertRaises(WorkspaceContractError):
            validate_unused_job_name(200,{},requested_name='OTHER',expected_name='SYN Job')

    def test_pinned_contract_rejects_noncanonical_paths_sizes_and_hashes(self):
        for change in (dict(path='/Workspace/Shared/a.sql'),dict(path='/Shared/../a.sql'),dict(path='/Shared//a.sql'),
                       dict(path='/Shared/a.sql/'),dict(byte_count=0),dict(byte_count=True),dict(byte_count=262145),dict(sha256='bad')):
            with self.subTest(change=change), self.assertRaises(WorkspaceContractError):
                replace(self.file,**change)

    def test_complete_existing_file_verification_returns_reuse_without_import(self):
        result=verify_existing_file(self.file,status_http=200,status_body=self.status,status_path=self.file.path,
            export_http=200,export_body=self.export,export_path=self.file.path,export_format='RAW',
            direct_download=False,expected_object_id=42)
        self.assertEqual((result.action,result.import_required,result.overwrite),('REUSE',False,False))
        self.assertEqual((result.byte_count,result.sha256),(len(self.data),self.file.sha256))
        self.assertNotIn(self.file.path,repr(result))

    def test_reuse_is_blocked_by_missing_identity_or_either_unproven_response(self):
        args=dict(status_http=200,status_body=self.status,status_path=self.file.path,
            export_http=200,export_body=self.export,export_path=self.file.path,export_format='RAW',
            direct_download=False,expected_object_id=42)
        for change in (dict(status_http=None),dict(export_http=None),dict(expected_object_id=None),
                       dict(expected_object_id=43),dict(status_body=dict(self.status,object_type='NOTEBOOK')),
                       dict(export_body={'content':base64.b64encode(b'X'*len(self.data)).decode()})):
            with self.subTest(change=list(change)),self.assertRaises(WorkspaceContractError):
                verify_existing_file(self.file,**dict(args,**change))
