"""Fail closed on publication paths and common accidental private-data disclosures."""

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = frozenset({
    '.gitignore', '.githooks/pre-commit', 'README.md', 'report.md',
    'pyproject.toml', 'uv.lock', 'data/results.json', 'docs/index.html',
    'docs/style.css', 'docs/data/results.json', 'docs/.nojekyll',
    'tools/build_site.py', 'tools/check_site.py', 'tools/check_publication.py',
    'tests/test_site.py', 'tests/test_publication.py',
})
PRIVATE_PATH = re.compile(r'/(?:' + 'home|Users' + r')/[^\s<>"\']+')
PRIVATE_KEY = re.compile(r'-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----')
TOKEN = re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{24,})')
ATTRIBUTION = re.compile('|'.join((
    'Co-Authored-By' + r':\s*(?:Claude|OpenAI)',
    'Generated with ' + 'Claude Code',
    chr(0x1F916) + ' Generated with',
)), re.I)
LIMIT = 1024 * 1024


def check_files(files: dict[str, bytes]) -> None:
    unexpected = set(files) - ALLOWED
    if unexpected:
        raise ValueError('unapproved publication paths: ' + ', '.join(sorted(unexpected)))
    if not {'report.md', 'data/results.json', 'docs/index.html', 'docs/data/results.json'} <= files.keys():
        raise ValueError('missing report, site or aggregate data')
    for name, raw in files.items():
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or str(path) != name:
            raise ValueError('noncanonical publication path')
        if len(raw) > LIMIT:
            raise ValueError('oversized public artifact: ' + name)
        content = raw.decode('utf-8')
        if any(pattern.search(content) for pattern in (PRIVATE_PATH, PRIVATE_KEY, TOKEN, ATTRIBUTION)):
            raise ValueError('possible private data or disallowed attribution: ' + name)
    if files['data/results.json'] != files['docs/data/results.json']:
        raise ValueError('published aggregates differ from source aggregates')
    data = json.loads(files['data/results.json'])
    if data['frozen_live_pilot']['behavioral_status'] != 'intended_comparison_not_reached':
        raise ValueError('frozen study limitation missing')
    if data['post_hoc_interface_diagnostic']['status'] != 'failed':
        raise ValueError('post-hoc resource failure must remain failed')
    if any(row['resolved'] for row in data['focused_final_grading']['states']):
        raise ValueError('unresolved final source must not be presented as resolved')
    if data['controlled_receipt_trust_probe']['spoof_parser_passed'] is not True:
        raise ValueError('receipt trust counterexample missing')


def publication_files(staged: bool = False) -> dict[str, bytes]:
    if staged:
        listing = subprocess.run(['git', 'ls-files', '--cached', '-z'], cwd=ROOT,
                                 check=True, capture_output=True, timeout=10).stdout
        files = {}
        for raw_name in listing.split(b'\0'):
            if not raw_name:
                continue
            name = raw_name.decode('utf-8')
            if name not in ALLOWED:
                raise ValueError('unapproved staged publication path: ' + name)
            mode = subprocess.run(['git', 'ls-files', '--stage', '--', name], cwd=ROOT,
                                  check=True, capture_output=True, text=True, timeout=10).stdout.split()[0]
            if mode not in {'100644', '100755'}:
                raise ValueError('nonregular staged file: ' + name)
            files[name] = subprocess.run(['git', 'show', ':' + name], cwd=ROOT, check=True,
                                         capture_output=True, timeout=10).stdout
        return files
    files = {}
    for name in ALLOWED:
        path = ROOT / name
        if path.is_symlink():
            raise ValueError('symlink forbidden: ' + name)
        if path.is_file():
            files[name] = path.read_bytes()
    return files


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--staged', action='store_true', help='validate the actual Git index bytes')
    args = parser.parse_args()
    files = publication_files(args.staged)
    check_files(files)
    print(f'Publication allowlist/privacy/negative-result checks passed for {len(files)} files.')
    print('Heuristic privacy checks are not a complete secret or scientific-validity audit.')


if __name__ == '__main__':
    main()
