"""Read-only checks for a prepared CoA data bundle. Does not run Git, build, SQL, or installation."""
import argparse
import hashlib
import json
import pathlib
import re
import sys


def digest(path):
    with path.open('rb') as stream:
        result = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
        return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=pathlib.Path, required=True)
    parser.add_argument('--server-dbc', type=pathlib.Path, required=True)
    parser.add_argument('--phase', choices=['before', 'after'], default='before')
    parser.add_argument('--config', type=pathlib.Path, help='The active mod_ascension_compat.conf, not its template')
    parser.add_argument('--repo', type=pathlib.Path, help='Repository or extracted bundle containing the SQL migrations')
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    manifest = json.loads((bundle / 'bundle.json').read_text(encoding='utf-8'))
    failures = []
    checked = 0

    def check(path, expected, label):
        nonlocal checked
        checked += 1
        if not path.is_file():
            failures.append(f'{label}: missing {path}')
        elif digest(path) != expected:
            failures.append(f'{label}: SHA-256 mismatch {path}')

    for relative, expected in manifest['payload_sha256'].items():
        path = (bundle / relative).resolve()
        if not path.is_relative_to(bundle):
            failures.append(f'Bundle path escapes its directory: {relative}')
            continue
        check(path, expected, 'bundle')
    expected_dbc = dict(manifest['baseline_dbc_sha256'])
    if args.phase == 'after':
        for relative, expected in manifest['payload_sha256'].items():
            if relative.startswith('dbc/'):
                expected_dbc[relative[4:]] = expected
    for relative, expected in expected_dbc.items():
        check(args.server_dbc / relative, expected, f'server {args.phase}')
    if args.repo:
        for relative, expected in manifest['migrations_sha256'].items():
            check(args.repo / relative, expected, 'migration file')
    else:
        print('NOT CHECKED: migration files (supply --repo).')

    if args.config:
        values = {}
        for line in args.config.read_text(encoding='utf-8-sig').splitlines():
            match = re.match(r'\s*(AscensionCompat\.\w+)\s*=\s*(.*?)\s*(?:#.*)?$', line)
            if match:
                values[match[1]] = match[2].strip().strip('"')
        if values.get('AscensionCompat.MapClass10ToWarrior') != '0':
            failures.append('Active config must explicitly set AscensionCompat.MapClass10ToWarrior = 0')
        if not values.get('AscensionCompat.DbcDirectory'):
            failures.append('Active config must explicitly set AscensionCompat.DbcDirectory')
        else:
            print('Configured collection directory:', values['AscensionCompat.DbcDirectory'])
            print('Resolve a relative collection directory from the worldserver working directory.')
    else:
        print('NOT CHECKED: active module configuration (supply --config).')
    for failure in failures:
        print('FAIL:', failure)
    print(f'{checked} file checks; {len(failures)} failures.')
    print('NOT CHECKED: live SQL state, deployed executable, client MPQs, or gameplay.')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
