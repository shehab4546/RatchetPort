import io
import json
import queue
import sys
import unittest
import zipfile
from unittest import mock
from paths import ROOT
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'launcher'))
import release_updates as updates
import ratchetport_launcher_win as launcher


class ReleaseUpdatesTest(unittest.TestCase):
    def fixture(self):
        return {'tag_name': 'v1.7.1', 'draft': False, 'prerelease': False,
                'html_url': updates.PAGE+'/tag/v1.7.1', 'assets': [
                    {'name': 'RatchetPort-V1.7.1-Controls-Windows.zip', 'state': 'uploaded',
                     'digest': 'sha256:'+'a'*64,
                     'browser_download_url': updates.PAGE+'/download/v1.7.1/port.zip'}]}

    def fetch(self, data, current='1.7'):
        return updates.latest(current, lambda *a, **k: io.BytesIO(json.dumps(data).encode()))

    def test_only_new_published_release_and_windows_asset(self):
        data = self.fixture()
        self.assertEqual(self.fetch(data)[0], 'v1.7.1')
        self.assertEqual(self.fetch(data)[3], 'a'*64)
        self.assertIsNone(self.fetch(data, '1.7.1.0'))
        self.assertIsNone(self.fetch(data, '1.8'))
        data['prerelease'] = True
        self.assertIsNone(self.fetch(data))
        data['prerelease'], data['draft'] = False, True
        self.assertIsNone(self.fetch(data))

    def test_wrong_archive_or_missing_digest_uses_release_page(self):
        data = self.fixture()
        data['assets'][0]['name'] = 'RatchetPort-V1.7.1-Source.zip'
        self.assertEqual(self.fetch(data)[1], '')
        data = self.fixture()
        del data['assets'][0]['digest']
        self.assertEqual(self.fetch(data)[1], '')
        data = self.fixture()
        data['assets'][0]['browser_download_url'] = 'https://example.com/unrelated.zip'
        self.assertEqual(self.fetch(data)[1], '')

    def test_failure_is_not_reported_as_up_to_date(self):
        with self.assertRaises(ValueError):
            self.fetch({'tag_name': 'invalid'})
        owner = launcher.Launcher.__new__(launcher.Launcher)
        owner.ui_calls, owner.messagebox = queue.Queue(), mock.Mock()
        with mock.patch.object(launcher, 'latest_release', side_effect=OSError('offline')):
            owner.check_update(True)
        owner.ui_calls.get_nowait()()
        owner.messagebox.showerror.assert_called_once()
        owner.messagebox.showinfo.assert_not_called()

    def test_archive_paths_checked_before_extraction(self):
        for name in ('../bad.exe', '/bad.exe', 'C:/bad.exe', 'x/../../bad.exe', 'x\\..\\bad.exe', 'CON.txt'):
            data = io.BytesIO()
            with zipfile.ZipFile(data, 'w') as z:
                z.writestr(name, b'test')
            with zipfile.ZipFile(data) as z, self.assertRaises(ValueError):
                updates.safe_members(z)
