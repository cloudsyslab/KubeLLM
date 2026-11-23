import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import os
import struct
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

    def make_crawl_wacz(self, path, url='https://example.com/product', *, with_index=True, profile=None,
                        bad_length=False):
        png = b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', 1440, 900) + b'\x08\x06\x00\x00\x00'

        def record(kind, target, content_type, body, length=None):
            head = (f'WARC/1.1\r\nWARC-Type: {kind}\r\n' + (f'WARC-Target-URI: {target}\r\n' if target else '')
                    + f'Content-Type: {content_type}\r\nContent-Length: {length or len(body)}\r\n\r\n').encode()
            return gzip.compress(head + body + b'\r\n\r\n')

        resources = {
            'pages/pages.jsonl': (b'{"format":"json-pages-1.0","id":"pages"}\n'
                                  + json.dumps({'url': url, 'title': 'Crawled', 'status': 200}).encode() + b'\n'),
            'archive/rec-fixture-0.warc.gz': record('response', url, 'application/http; msgtype=response',
                                                    b'HTTP/1.1 200 OK\r\n\r\n<html>crawled</html>'),
            'archive/screenshots-fixture.warc.gz': (record('warcinfo', None, 'application/warc-fields', b'software: fixture')
                                                    + record('resource', f'urn:view:{url}', 'image/png', png,
                                                             'abc' if bad_length else None)
                                                    + record('resource', 'urn:view:https://other.example.com/', 'image/png', png)),
        }
        if with_index:
            resources['indexes/index.cdxj'] = b'com,example)/product 20261122000000 {"url":"https://example.com/product","mime":"text/html","status":"200"}\n'
        package = {'wacz_version': '1.1.1', 'software': 'Browsertrix-Crawler fixture', 'created': '2026-11-22T12:00:00Z',
                   'resources': [{'name': Path(name).name, 'path': name, 'hash': f'sha256:{hashlib.sha256(value).hexdigest()}',
                                  'bytes': len(value)} for name, value in resources.items()]}
        if profile:
            package['profile'] = profile
        package_bytes = json.dumps(package).encode()
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, value in resources.items():
                archive.writestr(name, value)
            archive.writestr('datapackage.json', package_bytes)
            archive.writestr('datapackage-digest.json', json.dumps(
                {'path': 'datapackage.json', 'hash': f'sha256:{hashlib.sha256(package_bytes).hexdigest()}'}).encode())
        return path

    def make_docker_stub(self):
        stub = self.root / 'docker-stub'
        stub.write_text('#!' + sys.executable + '\nimport json,os,shutil,sys\nfrom pathlib import Path\n'
                        'args=sys.argv[1:]\nimage=os.environ.get("STUB_IMAGE","ready")\n'
                        'if args[:1]==["kill"]:\n'
                        '    Path(os.environ["STUB_KILLS"]).write_text(args[1]);sys.exit(0)\n'
                        'if args[:1]==["inspect"]:\n'
                        '    label=Path(os.environ["STUB_CONTAINER_LABEL"])\n'
                        '    print(label.read_text() if label.exists() else os.environ.get("STUB_EXISTING_LABEL","foreign"));sys.exit(0)\n'
                        'if args[:2]==["image","inspect"]:\n'
                        '    if image=="missing": print("Error: No such image: x",file=sys.stderr);sys.exit(1)\n'
                        '    if image=="daemon": print("Cannot connect to the Docker daemon",file=sys.stderr);sys.exit(1)\n'
                        '    print(json.dumps(["webrecorder/browsertrix-crawler@sha256:"+"a"*64]));sys.exit(0)\n'
                        'Path(os.environ["STUB_ARGS"]).write_text(json.dumps(args))\n'
                        'mode=os.environ.get("STUB_MODE","success")\n'
                        'if mode=="collision": print("Conflict. The container name is already in use",file=sys.stderr);sys.exit(125)\n'
                        'label=args[args.index("--label")+1].split("=",1)[1]\n'
                        'Path(os.environ["STUB_CONTAINER_LABEL"]).write_text(label)\n'
                        'if mode=="fail": print("Seed Page Load Failed, failing crawl",file=sys.stderr);sys.exit(1)\n'
                        'if mode=="hang":\n    import time;time.sleep(5)\n'
                        'if mode=="unshared": print("docker: Error response from daemon: invalid mount config for type '
                        '\\"bind\\": bind source path does not exist: /x",file=sys.stderr);sys.exit(125)\n'
                        'host=[a.split("source=")[1].split(",")[0] for a in args if a.endswith("target=/crawls")][0]\n'
                        'slug=args[args.index("--collection")+1]\n'
                        'if mode=="nowacz": sys.exit(0)\n'
                        'target=Path(host)/"collections"/slug/(slug+".wacz")\ntarget.parent.mkdir(parents=True)\n'
                        'shutil.copy(os.environ["STUB_WACZ"],target)\n')
        stub.chmod(0o755)
        return stub

    def run_crawl(self, extra=(), mode='success', image='ready', **fixture):
        source = self.make_crawl_wacz(self.root / 'crawl-fixture.wacz', **fixture)
        args = [sys.executable, str(CAPTURE), '--url', 'https://example.com/product', '--slug', 'example-com-product',
                '--crawl', '--docker', str(self.make_docker_stub()), *extra]
        return subprocess.run(args, cwd=self.root, text=True, capture_output=True, timeout=20,
                              env={**os.environ, 'STUB_MODE': mode, 'STUB_IMAGE': image, 'STUB_WACZ': str(source),
                                   'STUB_ARGS': str(self.root / 'docker-args.json'),
                                   'STUB_KILLS': str(self.root / 'docker-kills.txt'),
                                   'STUB_CONTAINER_LABEL': str(self.root / 'container-label.txt'),
                                   'STUB_EXISTING_LABEL': 'another-capture'})

    def test_crawl_route_imports_wacz_and_screenshots(self):
        result = self.run_crawl()
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads((self.root / 'docker-args.json').read_text())
        for expected in (['--pull', 'never'], ['--scopeType', 'page'], ['--collection', 'example-com-product']):
            index = args.index(expected[0])
            self.assertEqual(args[index:index + 2], expected)
        self.assertIn('--generateWACZ', args)
        self.assertIn('webrecorder/browsertrix-crawler:1.15.4', args)
        site = self.root / 'references/sites/example-com-product'
        meta = json.loads((site / 'meta.json').read_text())
        self.assertTrue((site / 'clone/original.wacz').is_file())
        self.assertEqual(meta['replay_status'], 'replay_unverified')
        self.assertEqual(meta['screenshot_status'], 'crawler_still_captured')
        self.assertTrue(meta['crawl']['image_digest'].endswith('a' * 64))
        self.assertEqual(meta['crawl']['login_profile'], 'none')
        self.assertEqual([shot['kind'] for shot in meta['crawl']['screenshots']], ['view'])
        self.assertEqual((meta['crawl']['screenshots'][0]['width'], meta['crawl']['screenshots'][0]['height']), (1440, 900))
        self.assertIn('1440x900', meta['capture_session']['viewport'])
        self.assertTrue((site / 'clone/shots/crawl-view.png').is_file())
        self.assertEqual(meta['original_archive']['index_files'], ['indexes/index.cdxj'])
        self.assertEqual(len(meta['original_archive']['warc_files']), 2)
        self.assertFalse(list(site.glob('.crawl-*')))

    def test_crawl_rejects_symlinked_screenshot_directory(self):
        site = self.root / 'references/sites/example-com-product'
        clone = site / 'clone'
        clone.mkdir(parents=True)
        outside = self.root / 'outside-shots'
        outside.mkdir()
        stale = outside / 'crawl-stale.png'
        stale.write_bytes(b'keep this file')
        (clone / 'shots').symlink_to(outside, target_is_directory=True)

        result = self.run_crawl()

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('clone/shots must not be a symlink', result.stderr)
        self.assertEqual(stale.read_bytes(), b'keep this file')
        self.assertFalse((clone / 'original.wacz').exists())
        self.assertFalse((site / 'meta.json').exists())

    def test_wacz_screenshot_scan_limits_expansion_and_time(self):
        source = self.make_crawl_wacz(self.root / 'bounded-scan.wacz')
        spec = importlib.util.spec_from_file_location('capture_budget_test', CAPTURE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module, 'MAX_WARC_SCAN_BYTES', 128):
            with self.assertRaisesRegex(ValueError, 'expanded-data limit'):
                module.wacz_screenshots(source, 'https://example.com/product')
        with patch.object(module, 'MAX_WARC_SCAN_SECONDS', 0):
            with self.assertRaisesRegex(ValueError, 'time limit'):
                module.wacz_screenshots(source, 'https://example.com/product')

    def test_replay_reimport_of_crawled_pack_keeps_crawl_evidence(self):
        self.assertEqual(self.run_crawl().returncode, 0)
        site = self.root / 'references/sites/example-com-product'
        result = self.import_wacz(site / 'clone/original.wacz', url='https://example.com/product',
                                  extra=('--replay-validated', '--tested-state', 'page renders offline'))
        self.assertEqual(result.returncode, 0, result.stderr)
        meta = json.loads((site / 'meta.json').read_text())
        self.assertEqual(meta['replay_status'], 'interaction_replay_validated')
        self.assertEqual(meta['screenshot_status'], 'crawler_still_captured')
        self.assertEqual(meta['crawl']['archive_sha256'], meta['original_archive']['sha256'])

    def test_phone_crawl_requests_full_page_screenshot_only(self):
        result = self.run_crawl(['--mobile-device', 'iPhone 13'])
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads((self.root / 'docker-args.json').read_text())
        self.assertEqual(args[args.index('--screenshot') + 1], 'fullPage')
        self.assertEqual(args[args.index('--mobileDevice') + 1], 'iPhone 13')
        meta = json.loads((self.root / 'references/sites/example-com-product/meta.json').read_text())
        self.assertEqual(meta['crawl']['mobile_device'], 'iPhone 13')
        self.assertTrue(meta['capture_session']['viewport'].startswith('crawler mobileDevice iPhone 13'))

    def test_crawl_timeout_stops_the_container(self):
        result = self.run_crawl(['--capture-timeout', '1'], mode='hang')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('container was stopped', result.stderr)
        args = json.loads((self.root / 'docker-args.json').read_text())
        name = args[args.index('--name') + 1]
        self.assertTrue(name.startswith('site-reference-crawl-'))
        label = args[args.index('--label') + 1]
        self.assertTrue(label.startswith('io.kubellm.site-reference.capture-id='))
        self.assertEqual((self.root / 'docker-kills.txt').read_text(), name)
        self.assertFalse(list((self.root / 'references/sites/example-com-product').glob('.crawl-*')))

    def test_crawl_name_collision_does_not_stop_another_container(self):
        result = self.run_crawl(mode='collision')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('container name is already in use', result.stderr)
        self.assertFalse((self.root / 'docker-kills.txt').exists())

    def test_bad_screenshot_record_fails_before_replacing_pack(self):
        self.assertEqual(self.run_crawl().returncode, 0)
        site = self.root / 'references/sites/example-com-product'
        before = (site / 'clone/original.wacz').read_bytes(), (site / 'meta.json').read_text()
        result = self.run_crawl(bad_length=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('previous pack is preserved', result.stderr)
        self.assertEqual(((site / 'clone/original.wacz').read_bytes(), (site / 'meta.json').read_text()), before)

    def test_recrawl_replaces_stale_crawler_stills(self):
        self.assertEqual(self.run_crawl().returncode, 0)
        shots = self.root / 'references/sites/example-com-product/clone/shots'
        (shots / 'crawl-fullpage.png').write_bytes(b'stale desktop shot')
        (shots / 'live-desktop.png').write_bytes(b'separate live evidence')
        self.assertEqual(self.run_crawl().returncode, 0)
        self.assertFalse((shots / 'crawl-fullpage.png').exists())
        self.assertTrue((shots / 'crawl-view.png').exists())
        self.assertTrue((shots / 'live-desktop.png').exists())

    def test_profile_mounts_only_the_profile_file(self):
        profile_dir = self.root / 'private-profiles'
        profile_dir.mkdir()
        profile = profile_dir / 'profile.tar.gz'
        profile.write_bytes(b'fixture profile')
        self.assertEqual(self.run_crawl(['--profile', str(profile)]).returncode, 0)
        args = json.loads((self.root / 'docker-args.json').read_text())
        self.assertIn(f'type=bind,source={profile.resolve()},target=/profile/profile.tar.gz,readonly', args)
        self.assertEqual(args[args.index('--profile') + 1], '/profile/profile.tar.gz')
        meta_text = (self.root / 'references/sites/example-com-product/meta.json').read_text()
        self.assertIn('"login_profile": "used"', meta_text)
        self.assertNotIn('private-profiles', meta_text)
        comma = self.root / 'a,b'
        comma.mkdir()
        (comma / 'profile.tar.gz').write_bytes(b'x')
        self.assertEqual(self.run_crawl(['--profile', str(comma / 'profile.tar.gz')]).returncode, 2)

    def test_crawl_not_ready_names_install_step(self):
        for image, hint in (('missing', 'docker pull webrecorder/browsertrix-crawler:1.15.4'), ('daemon', 'colima start')):
            result = self.run_crawl(image=image)
            self.assertEqual(result.returncode, 127, result.stderr)
            self.assertIn(hint, result.stderr)
        self.assertFalse((self.root / 'references').exists())

    def test_authenticated_crawl_requires_ignored_profile_and_output(self):
        subprocess.run(['git', 'init', '--quiet'], cwd=self.root, check=True)
        profile = self.root / 'login.tar.gz'
        profile.write_bytes(b'profile')
        result = self.run_crawl(['--profile', str(profile)])
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('authenticated capture output must be outside Git or under an ignored path', result.stderr)
        self.assertFalse((self.root / 'references').exists())
        self.assertFalse((self.root / 'docker-args.json').exists())

    def test_authenticated_crawl_accepts_ignored_local_root_and_profile(self):
        subprocess.run(['git', 'init', '--quiet'], cwd=self.root, check=True)
        (self.root / '.gitignore').write_text('/.local/\n')
        profile = self.root / '.local/login.tar.gz'
        profile.parent.mkdir()
        profile.write_bytes(b'profile')
        output = self.root / '.local/site-reference'
        output.mkdir()
        result = self.run_crawl(['--root', str(output), '--profile', str(profile)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output / 'references/sites/example-com-product/clone/original.wacz').is_file())

    def test_crawl_failures_preserve_previous_pack(self):
        self.assertEqual(self.run_crawl().returncode, 0)
        site = self.root / 'references/sites/example-com-product'
        before = (site / 'clone/original.wacz').read_bytes(), (site / 'meta.json').read_text()
        for mode, message in (('nowacz', 'share this folder'), ('fail', 'could not load the requested page'),
                              ('unshared', 'cannot see the project folder')):
            result = self.run_crawl(mode=mode)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn(message, result.stderr)
            self.assertEqual(((site / 'clone/original.wacz').read_bytes(), (site / 'meta.json').read_text()), before)
            self.assertFalse(list(site.glob('.crawl-*')))

    def test_crawl_refuses_replay_and_live_action_claims(self):
        for extra in (['--replay-validated'], ['--tested-state', 'menu'], ['--action', 'clicked'], ['--import-wacz', 'x.wacz']):
            self.assertEqual(self.run_crawl(extra).returncode, 2)

    def test_spec_layout_wacz_imports_and_incomplete_layout_is_rejected(self):
        good = self.make_crawl_wacz(self.root / 'spec.wacz')
        result = self.import_wacz(good, url='https://example.com/product')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['index_files'], ['indexes/index.cdxj'])
        for name, kwargs in (('no-index.wacz', {'with_index': False}), ('bad-profile.wacz', {'profile': 'other'})):
            result = self.import_wacz(self.make_crawl_wacz(self.root / name, **kwargs), url='https://example.com/product',
                                      slug='other-pack')
            self.assertEqual(result.returncode, 1, result.stderr)

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
        result = subprocess.run([sys.executable, str(CAPTURE), '--doctor', '--docker', str(self.root / 'no-docker')],
                                cwd=self.root,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['root'], str(self.root))
        after = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        self.assertEqual(after, before)

    def test_doctor_reports_routes_and_install_hints(self):
        spec = importlib.util.spec_from_file_location('capture_doctor', CAPTURE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        routes, install = module.capture_routes({'archiveweb_app': [], 'replayweb_app': [],
                                                 'single_file': None, 'chrome': '/usr/bin/chrome'})
        self.assertFalse(routes['wacz_original']['ready'])
        self.assertEqual(routes['wacz_original']['missing'], ['archiveweb_app', 'replayweb_app'])
        self.assertFalse(routes['singlefile_partial']['ready'])
        self.assertEqual(list(install), ['archiveweb_app', 'replayweb_app', 'single_file', 'browsertrix_crawler'])
        self.assertFalse(routes['wacz_crawl']['ready'])
        self.assertIn('docs.docker.com', install['browsertrix_crawler'])
        self.assertIn('archiveweb.page', install['archiveweb_app'])
        self.assertIn('replayweb.page', install['replayweb_app'])
        ready, nothing = module.capture_routes({'archiveweb_app': ['/Applications/ArchiveWeb.page.app'],
                                                'replayweb_app': [], 'single_file': '/bin/sf', 'chrome': '/bin/c',
                                                'crawler_status': 'ready'})
        self.assertTrue(ready['wacz_crawl']['ready'])
        self.assertTrue(ready['wacz_original']['ready'])
        self.assertEqual(ready['wacz_original']['replay'], 'replayweb.page web app in a browser')
        self.assertEqual(list(nothing), ['replayweb_app'])
        result = subprocess.run([sys.executable, str(CAPTURE), '--doctor', '--docker', str(self.root / 'no-docker')],
                                cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue({'replayweb_app', 'docker', 'crawler_status', 'routes', 'install', 'policy'}
                        <= set(json.loads(result.stdout)))

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
