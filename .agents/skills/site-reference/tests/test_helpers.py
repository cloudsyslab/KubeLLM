import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1]
CAPTURE = SKILL / 'scripts/capture.py'
PREVIEW = SKILL / 'scripts/preview.py'


class Helpers(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='reference-fixture-')
        self.root = Path(self.temporary.name).resolve()
        self.command = self.root / 'single-file-stub'
        self.command.write_text('#!' + sys.executable + '\nimport json,os,sys,time\n'
                                'from pathlib import Path\n'
                                'mode=os.environ.get("STUB_MODE", "success")\n'
                                'output=Path(sys.argv[2])\n'
                                'argsfile=os.environ.get("STUB_ARGS")\n'
                                'Path(argsfile).write_text(json.dumps(sys.argv)) if argsfile else None\n'
                                'overwrite="--filename-conflict-action" in sys.argv and '
                                'sys.argv[sys.argv.index("--filename-conflict-action")+1]=="overwrite"\n'
                                'if output.exists() and not overwrite: '
                                'output=output.with_name(output.stem+" (1)"+output.suffix)\n'
                                'output.write_text("<html><body>new capture</body></html>")\n'
                                'if mode=="failure": print("ENOTFOUND source",file=sys.stderr);sys.exit(2)\n'
                                'if mode=="empty": output.write_text("")\n'
                                'if mode=="timeout": time.sleep(5)\n')
        self.command.chmod(0o755)

    def tearDown(self):
        self.temporary.cleanup()

    def run_capture(self, extra=(), mode='success'):
        args = [sys.executable, str(CAPTURE), '--url', 'https://example.com/product#hero',
                '--slug', 'example-com-product', '--single-file', str(self.command),
                '--chrome', sys.executable, *extra]
        return subprocess.run(args, cwd=self.root, env={**os.environ, 'STUB_MODE': mode,
                                                        'STUB_ARGS': str(self.root / 'stub-args.json')},
                              text=True, capture_output=True, timeout=10)

    def make_wacz(self, path, url='https://example.com/product#hero', *, title='Example', corrupt_resource=False):
        resources = {
            'pages/pages.jsonl': (b'{"format":"json-pages-1.0","id":"pages"}\n'
                                  + json.dumps({'url': url, 'title': title}).encode() + b'\n'),
            'archive/data.warc.gz': b'fixture archive bytes',
            'indexes/index.cdx': b'com,example)/product 20261002000000 {"url":"https://example.com/product","mime":"text/html","status":200}\n',
        }
        if corrupt_resource:
            resources['archive/data.warc.gz'] = b'changed after digest'
        package_resources = []
        for name, value in resources.items():
            expected = hashlib.sha256(value).hexdigest()
            if corrupt_resource and name == 'archive/data.warc.gz':
                expected = '0' * 64
            package_resources.append({'name': Path(name).name, 'path': name,
                                      'hash': f'sha256:{expected}', 'bytes': len(value)})
        package = {'profile': 'data-package', 'wacz_version': '1.1.1', 'title': 'Fixture',
                   'software': 'ArchiveWeb fixture', 'created': '2026-10-02T12:00:00Z',
                   'resources': package_resources}
        package_bytes = json.dumps(package).encode()
        digest = {'path': 'datapackage.json',
                  'hash': f"sha256:{hashlib.sha256(package_bytes).hexdigest()}"}
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, value in resources.items():
                archive.writestr(name, value)
            archive.writestr('datapackage.json', package_bytes)
            archive.writestr('datapackage-digest.json', json.dumps(digest).encode())
        return path

    def import_wacz(self, path, url='https://example.com/product#hero', slug='example-com-product', extra=()):
        args = [sys.executable, str(CAPTURE), '--root', str(self.root), '--url', url,
                '--slug', slug, '--import-wacz', str(path), *extra]
        return subprocess.run(args, cwd=self.root, text=True, capture_output=True, timeout=10)

    def test_cwd_root_and_capture_without_screenshot_tool(self):
        result = self.run_capture()
        self.assertEqual(result.returncode, 0, result.stderr)
        site = self.root / 'references/sites/example-com-product'
        self.assertIn('new capture', (site / 'clone/index.html').read_text())
        metadata = json.loads((site / 'meta.json').read_text())
        self.assertEqual(metadata['screenshot_status'], 'screenshot_pending')
        self.assertEqual(metadata['motion_and_embeds'], 'unverified')
        self.assertFalse((site / 'clone/shots').exists())
        arguments = json.loads((self.root / 'stub-args.json').read_text())
        for option in ('--block-scripts', '--block-videos', '--block-audios', '--block-fonts',
                       '--remove-hidden-elements', '--remove-unused-styles', '--remove-unused-fonts'):
            index = arguments.index(option)
            self.assertEqual(arguments[index + 1], 'false')

    def test_wacz_import_verifies_original_archive_and_records_replay_evidence(self):
        source = self.make_wacz(self.root / 'source.wacz')
        result = self.import_wacz(source, extra=('--replay-validated', '--tested-state', 'menu open',
                                                  '--viewport', '1600x900 CSS px', '--action', 'open menu'))
        self.assertEqual(result.returncode, 0, result.stderr)
        site = self.root / 'references/sites/example-com-product'
        self.assertEqual((site / 'clone/original.wacz').read_bytes(), source.read_bytes())
        metadata = json.loads((site / 'meta.json').read_text())
        self.assertEqual(metadata['snapshot_status'], 'archived_client_runtime')
        self.assertEqual(metadata['replay_status'], 'interaction_replay_validated')
        self.assertEqual(metadata['tested_states'], ['menu open'])
        self.assertEqual(metadata['capture_session']['viewport'], '1600x900 CSS px')
        self.assertEqual(metadata['capture_session']['live_actions'], ['open menu'])
        self.assertEqual(metadata['original_archive']['index_entry_count'], 1)
        self.assertEqual(metadata['original_archive']['mime_counts'], {'text/html': 1})
        self.assertIn('SHA-256', metadata['original_archive']['integrity'])

    def test_reimport_preserves_separate_screenshot_and_comparison_evidence(self):
        source = self.make_wacz(self.root / 'source.wacz')
        self.assertEqual(self.import_wacz(source).returncode, 0)
        site = self.root / 'references/sites/example-com-product'
        shots = site / 'clone/shots'
        shots.mkdir()
        (shots / 'live.jpg').write_bytes(b'fixture image')
        metadata = json.loads((site / 'meta.json').read_text())
        metadata['visual_comparison_status'] = 'pending_same_viewport'
        (site / 'meta.json').write_text(json.dumps(metadata))
        result = self.import_wacz(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        updated = json.loads((site / 'meta.json').read_text())
        self.assertEqual(updated['screenshot_status'], 'live_still_captured')
        self.assertEqual(updated['visual_comparison_status'], 'pending_same_viewport')

    def test_replacing_wacz_resets_visual_comparison_evidence(self):
        original = self.make_wacz(self.root / 'original.wacz')
        self.assertEqual(self.import_wacz(original).returncode, 0)
        site = self.root / 'references/sites/example-com-product'
        metadata = json.loads((site / 'meta.json').read_text())
        metadata['visual_comparison_status'] = 'matched'
        (site / 'meta.json').write_text(json.dumps(metadata))

        replacement = self.make_wacz(self.root / 'replacement.wacz', title='Updated page')
        result = self.import_wacz(replacement)

        self.assertEqual(result.returncode, 0, result.stderr)
        updated = json.loads((site / 'meta.json').read_text())
        self.assertEqual(updated['visual_comparison_status'], 'not_compared')
        self.assertEqual(updated['original_archive']['sha256'], hashlib.sha256(replacement.read_bytes()).hexdigest())

    def test_invalid_wacz_and_wrong_page_url_preserve_existing_pack(self):
        good = self.make_wacz(self.root / 'good.wacz')
        self.assertEqual(self.import_wacz(good).returncode, 0)
        site = self.root / 'references/sites/example-com-product'
        before = {str(path.relative_to(site)): path.read_bytes()
                  for path in site.rglob('*') if path.is_file()}
        corrupt = self.make_wacz(self.root / 'corrupt.wacz', corrupt_resource=True)
        result = self.import_wacz(corrupt)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('resource integrity check failed', result.stderr)
        after = {str(path.relative_to(site)): path.read_bytes()
                 for path in site.rglob('*') if path.is_file()}
        self.assertEqual(after, before)
        result = self.import_wacz(good, url='https://other.example.com/')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('source URL', result.stderr)
        after = {str(path.relative_to(site)): path.read_bytes()
                 for path in site.rglob('*') if path.is_file()}
        self.assertEqual(after, before)

    def test_reimport_accepts_browser_added_slash_and_malformed_metadata_is_non_destructive(self):
        source = self.make_wacz(self.root / 'source.wacz')
        self.assertEqual(self.import_wacz(source).returncode, 0)
        site = self.root / 'references/sites/example-com-product'
        result = self.import_wacz(source, url='https://example.com/product/')
        self.assertEqual(result.returncode, 0, result.stderr)
        archive_before = (site / 'clone/original.wacz').read_bytes()
        (site / 'meta.json').write_text('{broken json')
        result = self.import_wacz(source, url='https://different.example.com/')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('existing meta.json needs inspection', result.stderr)
        self.assertEqual((site / 'clone/original.wacz').read_bytes(), archive_before)
        self.assertEqual((site / 'meta.json').read_text(), '{broken json')

    def test_failure_timeout_and_empty_preserve_previous_capture_and_notes(self):
        self.assertEqual(self.run_capture().returncode, 0)
        site = self.root / 'references/sites/example-com-product'
        (site / 'preferences.md').write_text('User likes this particular component.')
        (site / 'notes.md').write_text('Existing authored notes.')
        metadata = json.loads((site / 'meta.json').read_text())
        metadata['study_targets'] = ['pricing comparison']
        (site / 'meta.json').write_text(json.dumps(metadata))
        saved = {str(path.relative_to(site)): path.read_bytes() for path in site.rglob('*') if path.is_file()}
        for mode in ('failure', 'empty', 'timeout'):
            result = self.run_capture(['--capture-timeout', '0.15'], mode=mode)
            self.assertNotEqual(result.returncode, 0)
            actual = {str(path.relative_to(site)): path.read_bytes() for path in site.rglob('*') if path.is_file()}
            self.assertEqual(actual, saved, result.stderr)
        self.assertEqual(self.run_capture().returncode, 0)
        self.assertEqual((site / 'preferences.md').read_text(), 'User likes this particular component.')
        self.assertEqual((site / 'notes.md').read_text(), 'Existing authored notes.')
        self.assertEqual(json.loads((site / 'meta.json').read_text())['study_targets'], ['pricing comparison'])

    def test_doctor_no_writes(self):
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        result = subprocess.run([sys.executable, str(CAPTURE), '--doctor'], cwd=self.root,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['root'], str(self.root))
        after = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        self.assertEqual(after, before)

    def test_explicit_root(self):
        target = self.root / 'other'
        target.mkdir()
        result = self.run_capture(['--root', str(target)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((target / 'references/sites/example-com-product/clone/index.html').exists())
        self.assertFalse((self.root / 'references').exists())

    def test_url_slug_and_symlink_write_validation(self):
        for extra in (['--url', 'file:///etc/passwd'], ['--url', 'https://user:pass@example.com'],
                      ['--slug', '../escape'], ['--slug', 'UPPER'], ['--url', 'https://example.com:bad']):
            result = self.run_capture(extra)
            self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse((self.root / 'references').exists())
        (self.root / 'references').symlink_to(self.root.parent)
        result = self.run_capture()
        self.assertEqual(result.returncode, 2)
        self.assertIn('outside --root', result.stderr)

    def test_preview_permission_diagnostic_without_socket(self):
        spec = importlib.util.spec_from_file_location('preview_test', PREVIEW)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        stderr = io.StringIO()
        with patch.object(sys, 'argv', ['preview.py', '--directory', str(self.root)]), \
             patch.object(module, 'QuietServer', side_effect=PermissionError(1, 'Operation not permitted')), \
             contextlib.redirect_stderr(stderr):
            self.assertEqual(module.main(), 1)
        self.assertIn('127.0.0.1', stderr.getvalue())
        self.assertIn('established approval', stderr.getvalue())
        self.assertIn('do not change global permissions', stderr.getvalue())

    def test_source_collision_and_legacy_preservation(self):
        self.assertEqual(self.run_capture().returncode, 0)
        site = self.root / 'references/sites/example-com-product'
        before = {str(p.relative_to(site)): p.read_bytes() for p in site.rglob('*') if p.is_file()}
        result = self.run_capture(['--url', 'https://other.example.com/'])
        self.assertEqual(result.returncode, 2)
        self.assertIn('different source URL', result.stderr)
        after = {str(p.relative_to(site)): p.read_bytes() for p in site.rglob('*') if p.is_file()}
        self.assertEqual(after, before)
        (site / 'meta.json').unlink()
        legacy = 'url: "https://example.com/product#hero"\nliked:\n  - "User authored"\n'
        (site / 'meta.yaml').write_text(legacy)
        self.assertEqual(self.run_capture().returncode, 0)
        self.assertEqual((site / 'meta.yaml').read_text(), legacy)
        result = self.run_capture(['--url', 'https://other.example.com/'])
        self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
