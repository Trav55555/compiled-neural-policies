"""Failure-sensitive publication boundary checks. No private files are read."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('publication', ROOT / 'tools/check_publication.py')
assert SPEC is not None and SPEC.loader is not None
publication = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publication)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.files = publication.publication_files()

    def test_actual_publication_passes(self):
        publication.check_files(self.files)

    def test_staged_bytes_not_clean_worktree(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(['git', 'init', '--quiet', str(root)], check=True, capture_output=True)
            report = root / 'report.md'
            staged = ('/' + 'home' + '/example/private-note').encode()
            report.write_bytes(staged)
            subprocess.run(['git', 'add', 'report.md'], cwd=root, check=True)
            report.write_text('clean working copy')
            with patch.object(publication, 'ROOT', root):
                self.assertEqual(publication.publication_files(staged=True)['report.md'], staged)

    def test_staged_private_path_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(['git', 'init', '--quiet', str(root)], check=True, capture_output=True)
            (root / 'private.txt').write_text('not approved')
            subprocess.run(['git', 'add', 'private.txt'], cwd=root, check=True)
            with patch.object(publication, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'unapproved staged publication path'):
                    publication.publication_files(staged=True)

    def test_staged_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(['git', 'init', '--quiet', str(root)], check=True, capture_output=True)
            (root / 'report.md').write_text('target')
            (root / 'README.md').symlink_to('report.md')
            subprocess.run(['git', 'add', 'README.md'], cwd=root, check=True)
            with patch.object(publication, 'ROOT', root):
                with self.assertRaisesRegex(ValueError, 'nonregular staged file'):
                    publication.publication_files(staged=True)

    def test_unapproved_path_rejected(self):
        self.files['private.txt'] = b'not approved'
        with self.assertRaisesRegex(ValueError, 'unapproved publication paths'):
            publication.check_files(self.files)

    def test_machine_path_rejected(self):
        self.files['report.md'] += ('\n/' + 'home' + '/example/private-note\n').encode()
        with self.assertRaisesRegex(ValueError, 'possible private data'):
            publication.check_files(self.files)

    def test_key_rejected(self):
        self.files['report.md'] += ('\n-----BEGIN ' + 'PRIVATE KEY-----\n').encode()
        with self.assertRaisesRegex(ValueError, 'possible private data'):
            publication.check_files(self.files)

    def test_token_rejected(self):
        self.files['report.md'] += ('\n' + 'ghp' + '_' + 'A' * 30).encode()
        with self.assertRaisesRegex(ValueError, 'possible private data'):
            publication.check_files(self.files)

    def test_attribution_rejected(self):
        self.files['report.md'] += ('\nGenerated with ' + 'Claude Code\n').encode()
        with self.assertRaisesRegex(ValueError, 'disallowed attribution'):
            publication.check_files(self.files)

    def test_stale_data_rejected(self):
        self.files['docs/data/results.json'] += b'\n'
        with self.assertRaisesRegex(ValueError, 'differ from source'):
            publication.check_files(self.files)

    def test_failure_cannot_be_promoted(self):
        files = copy.deepcopy(self.files)
        data = json.loads(files['data/results.json'])
        data['post_hoc_interface_diagnostic']['status'] = 'passed'
        for name in ('data/results.json', 'docs/data/results.json'):
            files[name] = json.dumps(data).encode()
        with self.assertRaisesRegex(ValueError, 'must remain failed'):
            publication.check_files(files)

    def test_unresolved_source_cannot_be_promoted(self):
        data = json.loads(self.files['data/results.json'])
        data['focused_final_grading']['states'][0]['resolved'] = True
        for name in ('data/results.json', 'docs/data/results.json'):
            self.files[name] = json.dumps(data).encode()
        with self.assertRaisesRegex(ValueError, 'must not be presented as resolved'):
            publication.check_files(self.files)


if __name__ == '__main__':
    unittest.main()
