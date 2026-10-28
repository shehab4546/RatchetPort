import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
from paths import ROOT
sys.path.insert(0, str(ROOT/'scripts'))
import session_diagnostics as diagnostics

CONFIG = {'project_id': 'ratchet-test', 'api_key': 'a'*30}
LOGIN = {'idToken': 'token', 'localId': 'user123', 'refreshToken': 'refresh'}
RECEIPT = {'writeResults': [{'updateTime': '2026-10-28T00:00:00Z'}],
           'commitTime': '2026-10-28T00:00:00Z'}


class DiagnosticsTest(unittest.TestCase):
    def queued(self, root):
        log = root/'run.log'
        log.write_text('Hardware: CPU test\nGPU test\n')
        payload = diagnostics.report(log, 0, '1.7')
        folder = root/'diagnostics-pending'
        folder.mkdir(exist_ok=True)
        path = folder/(payload['id']+'.json')
        path.write_text(json.dumps(payload))
        return folder, path, payload

    def test_disabled_or_unconfigured_never_uses_network(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(diagnostics, 'request_json') as request:
            diagnostics.finish({}, tmp, Path(tmp)/'missing.log', 0, '1.7')
            diagnostics.finish({'diagnostics_upload': True}, tmp, Path(tmp)/'missing.log', 0, '1.7')
            request.assert_not_called()

    def test_report_filter_and_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp)/'run.log'
            log.write_text('Hardware: CPU model test\nPlayer name: private\nRuntime: file opened secret-save.dat\n'
                           'GPU error C:\\Users\\Private Name\\secret.txt\n'
                           + 'GPU warning token=SECRET person@example.com\n'*20000)
            payload = diagnostics.report(log, 3, '1.7')
        self.assertNotIn('private', payload['log'].lower())
        self.assertNotIn('secret-save', payload['log'])
        self.assertNotIn('SECRET', payload['log'])
        self.assertNotIn('person@example.com', payload['log'])
        self.assertIn('Hardware: CPU model', payload['log'])
        self.assertLess(len(json.dumps(payload).encode()), diagnostics.MAX_REPORT)
        self.assertTrue(diagnostics.valid_report(payload))
        for bad in ({'schema': True}, {'extra': 'field'}, {'log': 'x'*32769}, {'exit_code': 2**64}):
            self.assertFalse(diagnostics.valid_report({**payload, **bad}))

    def test_unicode_log_limit_preserves_header_and_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp)/'run.log'
            log.write_text('Hardware: first\n'+''.join('GPU '+str(i)+' ش'*900+'\n' for i in range(500))+'GPU last\n')
            payload = diagnostics.report(log, 0, '1.7')
            self.assertTrue(diagnostics.valid_report(payload))
            self.assertIn('Hardware: first', payload['log'])
            self.assertIn('GPU last', payload['log'])

    def test_only_successful_commit_removes_report_and_refreshes_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder, path, payload = self.queued(root)
            with mock.patch.object(diagnostics, 'request_json', side_effect=[LOGIN, {}]):
                with self.assertRaises(ValueError):
                    diagnostics.send_pending(folder, CONFIG)
            self.assertTrue(path.exists())
            refreshed = {'id_token': 'fresh', 'user_id': 'user123', 'refresh_token': 'rotated'}
            with mock.patch.object(diagnostics, 'request_json', side_effect=[refreshed, RECEIPT]) as send:
                diagnostics.send_pending(folder, CONFIG)
                self.assertIn('securetoken.googleapis.com', send.call_args_list[0].args[0])
                self.assertTrue(send.call_args_list[0].kwargs['form'])
                self.assertEqual(send.call_args.args[2], 'fresh')
                write = send.call_args.args[1]['writes'][0]
                self.assertTrue(write['update']['name'].endswith('user123_'+payload['id']))
                self.assertEqual(write['currentDocument'], {'exists': False})
                self.assertEqual(write['updateTransforms'][0]['setToServerValue'], 'REQUEST_TIME')
                self.assertNotIn('refresh', json.dumps(write))
            self.assertFalse(path.exists())

    def test_daily_limit_survives_multiple_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _ in range(3):
                folder, _, _ = self.queued(root)
            with mock.patch.object(diagnostics, 'request_json', side_effect=[LOGIN, RECEIPT, RECEIPT]) as send:
                diagnostics.send_pending(folder, CONFIG)
                self.assertEqual(send.call_count, 3)
                diagnostics.send_pending(folder, CONFIG)
                self.assertEqual(send.call_count, 3)
            self.assertEqual(len(list(folder.glob('*.json'))), 1)

    def test_failed_network_retains_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder, path, _ = self.queued(Path(tmp))
            with mock.patch.object(diagnostics, 'request_json', side_effect=[LOGIN, OSError('offline')]):
                with self.assertRaises(OSError):
                    diagnostics.send_pending(folder, CONFIG)
            self.assertTrue(path.exists())

    def test_config_fallback_override_and_excludes_extra_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            public = root/'diagnostics.public.json'
            public.write_text(json.dumps({**CONFIG, 'extra_secret': 'never package'}))
            self.assertEqual(diagnostics.configuration(tmp), CONFIG)
            override = root/'diagnostics.json'
            override.write_text(json.dumps({**CONFIG, 'endpoint': 'https://example.test'}))
            self.assertIsNone(diagnostics.configuration(tmp))
            override.write_text(json.dumps({**CONFIG, 'project_id': '../evil'}))
            self.assertIsNone(diagnostics.configuration(tmp))
            override.write_text(json.dumps({**CONFIG, 'api_key': 123}))
            self.assertIsNone(diagnostics.configuration(tmp))

    def test_deployment_excludes_paid_services_and_log_index(self):
        config = json.loads((ROOT/'services/diagnostics/firebase.json').read_text())
        self.assertEqual(set(config), {'firestore'})
        indexes = json.loads((ROOT/'services/diagnostics/firestore.indexes.json').read_text())
        self.assertEqual(indexes['fieldOverrides'][0]['indexes'], [])
        self.assertEqual(diagnostics.configuration(ROOT)['project_id'], 'ratchetport-diagnostics')
