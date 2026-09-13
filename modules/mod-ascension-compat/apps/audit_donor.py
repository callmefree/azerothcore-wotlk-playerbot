"""Read-only comparison of line-oriented Ascension SQL and a HeidiSQL world export.

This inventories partial donor data; it never imports SQL or treats missing rows as safe inserts.
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


def cells(text):
    result, start, quoted, i = [], 0, False, 0
    while i < len(text):
        char = text[i]
        if char == "\\" and quoted:
            i += 2
            continue
        if char == "'":
            if quoted and i + 1 < len(text) and text[i + 1] == "'":
                i += 2
                continue
            quoted = not quoted
        elif char == ',' and not quoted:
            result.append(text[start:i].strip())
            start = i + 1
        i += 1
    if quoted:
        raise ValueError('Unterminated SQL string')
    return result + [text[start:].strip()]


def rows(path):
    table, columns = None, []
    with path.open(encoding='utf-8-sig') as source:
        for number, line in enumerate(source, 1):
            line = line.strip()
            if line.startswith('INSERT INTO'):
                match = re.fullmatch(r'INSERT INTO `(\w+)` \((.*)\) VALUES', line)
                if not match:
                    raise ValueError(f'{path}:{number}: unsupported INSERT layout')
                table = match[1]
                columns = re.findall(r'`(\w+)`', match[2])
            elif line.startswith('(') and table:
                values = line.rstrip(',;')
                if not values.endswith(')'):
                    raise ValueError(f'{path}:{number}: unsupported tuple layout')
                values = cells(values[1:-1])
                if len(values) != len(columns):
                    raise ValueError(f'{path}:{number}: column count mismatch')
                yield table, dict(zip(columns, values))


def dbc_ids(path):
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError(f'{path}: truncated DBC')
    magic, count, fields, size, strings = struct.unpack_from('<4s4I', data)
    if magic != b'WDBC' or size != fields * 4 or size < 4 or len(data) != 20 + count * size + strings:
        raise ValueError(f'{path}: invalid DBC header/length')
    return {struct.unpack_from('<I', data, 20 + index * size)[0] for index in range(count)}


def rank_audit(donor_rows, current_rows, spell_ids):
    def group(records):
        chains = {}
        for row in records:
            first, rank, spell = (int(row[key]) for key in ('first_spell_id', 'rank', 'spell_id'))
            chains.setdefault(first, []).append((rank, spell))
        return {key: sorted(value) for key, value in chains.items()}

    chains, current = group(donor_rows), group(current_rows)
    members = {}
    for first, chain in current.items():
        for rank, spell in chain:
            members[spell] = (first, rank)
    donor_members = {}
    for first, chain in chains.items():
        for _, spell in chain:
            donor_members.setdefault(spell, []).append(first)
    result = {key: [] for key in ('identical', 'invalid_structure', 'missing_spells',
                                  'conflicting_existing', 'candidate_new_chains')}
    for first, chain in sorted(chains.items()):
        ranks = [rank for rank, _ in chain]
        spells = [spell for _, spell in chain]
        if (ranks != list(range(1, len(chain) + 1)) or chain[0][1] != first or not 2 <= len(chain) <= 255
                or any(len(donor_members[spell]) != 1 for spell in spells)):
            status = 'invalid_structure'
        elif any(spell not in spell_ids for spell in spells):
            status = 'missing_spells'
        elif current.get(first) == chain:
            status = 'identical'
        elif first in current or any(spell in members for spell in spells):
            status = 'conflicting_existing'
        else:
            status = 'candidate_new_chains'
        result[status].append(first)
    return {'counts': {key: len(value) for key, value in result.items()}, 'chain_ids': result,
            'acceptance': 'Candidates still require spell semantics/progression review; not an import manifest.'}


def audit(donor, current, spell_dbcs=()):
    tables, sources = {}, []
    for path in sorted(donor.glob('rev_*.sql')):
        sources.append({'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        for table, row in rows(path):
            entry = tables.setdefault(table, {'rows': [], 'columns': set()})
            entry['rows'].append(row)
            entry['columns'].update(row)
    result = {'donor_files': sources, 'tables': {}, 'empty_name_candidates': []}
    for table, entry in sorted(tables.items()):
        path = current / f'{table}.sql'
        if not path.exists():
            raise ValueError(f'Missing target schema: {path}')
        schema = set()
        with path.open(encoding='utf-8-sig') as source:
            for line in source:
                match = re.match(r'  `(\w+)` ', line)
                if match:
                    schema.add(match[1])
                if ') ENGINE=' in line:
                    break
        summary = {'donor_rows': len(entry['rows']), 'columns': sorted(entry['columns']),
                   'unknown_columns': sorted(entry['columns'] - schema),
                   'target_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        if table in ('item_template', 'creature_template', 'quest_template',
                     'gameobject_template', 'spell_dbc', 'achievement_dbc', 'areatable_dbc'):
            key = 'entry' if 'entry' in entry['columns'] else 'ID'
            existing = {row[key]: row for _, row in rows(path)}
            summary['existing_ids'] = sum(row[key] in existing for row in entry['rows'])
            summary['absent_ids'] = summary['donor_rows'] - summary['existing_ids']
            for row in entry['rows']:
                old = existing.get(row[key])
                if old and old.get('name') == "''" and row.get('name', "''") != "''":
                    result['empty_name_candidates'].append({
                        'table': table, 'id': int(row[key]), 'donor_name_literal': row['name']})
        result['tables'][table] = summary
    if spell_dbcs:
        spell_ids = set()
        result['spell_dbc_files'] = []
        for path in spell_dbcs:
            spell_ids.update(dbc_ids(path))
            result['spell_dbc_files'].append({
                'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        spell_ids.update(int(row['ID']) for _, row in rows(current / 'spell_dbc.sql'))
        result['spell_ranks'] = rank_audit(tables['spell_ranks']['rows'],
                                         [row for _, row in rows(current / 'spell_ranks.sql')], spell_ids)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--donor', type=Path, required=True, help='Directory containing donor rev_*.sql')
    parser.add_argument('--current', type=Path, required=True, help='World export directory')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--spell-dbc', type=Path, action='append', default=[],
                        help='Repeat for the baseline and each active Spell.dbc continuation to audit rank references')
    args = parser.parse_args()
    result = audit(args.donor, args.current, args.spell_dbc)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f"Audited {len(result['tables'])} tables; {len(result['empty_name_candidates'])} empty-name candidates")
