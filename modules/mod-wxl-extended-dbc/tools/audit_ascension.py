"""Read-only audit of v20 + dbc1-ascension. SQL overlays and runtime scripts are not evaluated."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct


def uint(row, column):
    return struct.unpack_from('<I', row, column * 4)[0]


def read_dbc(path, fmt):
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError(f'{path.name}: truncated header')
    magic, count, fields, size, strings = struct.unpack_from('<4s4I', data)
    if magic != b'WDBC' or len(data) != 20 + count * size + strings:
        raise ValueError(f'{path.name}: invalid header or length')
    if fmt == 'df' and (fields, size) == (1, 4):
        fmt = 'f'
    if fields != len(fmt):
        raise ValueError(f'{path.name}: {fields} fields, expected {len(fmt)}')
    offset, index = 0, None
    string_fields = []
    for code in fmt:
        width = 1 if code in 'bX' else 4
        if code not in 'xX' and offset + width > size:
            raise ValueError(f'{path.name}: used field exceeds record size')
        if code in 'nd':
            index = offset
        if code == 's':
            string_fields.append(offset)
        offset += width
    rows = {}
    view = memoryview(data)
    pool = data[20 + count * size:]
    for number in range(count):
        row = view[20 + number * size:20 + (number + 1) * size]
        key = struct.unpack_from('<I', row, index)[0] if index is not None else number
        if key == 0xFFFFFFFF:
            raise ValueError(f'{path.name}: row {number} overflows the index')
        for field in string_fields:
            value = struct.unpack_from('<I', row, field)[0]
            if value >= strings or pool.find(b'\0', value) < 0:
                raise ValueError(f'{path.name}: row {number} has an invalid string')
        rows[key] = row
    return rows


def audit(root, data):
    def source(name):
        return (root / name).read_text(encoding='utf-8')

    core = source('src/server/game/DataStores/DBCStores.cpp')
    formats = dict(re.findall(r'char constexpr (\w+)\[\] = "([^"]+)";',
                             source('src/server/shared/DataStores/DBCfmt.h')))
    stores = dict(re.findall(r'DBCStorage\s*<[^>]+>\s*(\w+)\s*\(\s*(\w+)\s*\)', core))
    registry = set(re.findall(r'WXL_DBC\(\w+, "([^"]+)"',
                             source('modules/mod-wxl-extended-dbc/src/WxlDbcRegistry.cpp')))
    tables, errors = {}, []
    loaded = 0
    for store, name in re.findall(r'LOAD_DBC\(\s*(\w+),\s*"([^"]+)"', core):
        try:
            rows = read_dbc(data / 'dbc' / name, formats[stores[store]])
            overlay = data / 'dbc-continuations' / (name + '1-ascension')
            if name in registry and overlay.exists():
                rows.update(read_dbc(overlay, formats[stores[store]]))
                loaded += 1
            tables[name] = rows
        except (ValueError, OSError) as error:
            errors.append(str(error))
    if errors:
        return {'errors': errors}

    def constant(name, text):
        return int(re.search(r'\b' + name + r'\s*=\s*(\d+)', text)[1])

    shared = source('src/server/shared/SharedDefines.h')
    effect_limit = constant('TOTAL_SPELL_EFFECTS', shared)
    aura_limit = constant('TOTAL_AURAS', source('src/server/game/Spells/Auras/SpellAuraDefines.h'))
    effect_nulls = set(map(int, re.findall(r'&Spell::EffectNULL,\s*//\s*(\d+)',
                                         source('src/server/game/Spells/SpellEffects.cpp'))))
    aura_nulls = set(map(int, re.findall(r'&AuraEffect::Handle(?:NULL|Unused),\s*//\s*(\d+)',
                                       source('src/server/game/Spells/Auras/SpellAuraEffects.cpp'))))
    effects, auras = {}, {}
    references = Counter()

    def reference(label, value, table):
        if value and value not in tables[table]:
            references[label] += 1

    for key, row in tables['Spell.dbc'].items():
        for slot in range(3):
            effect, aura = uint(row, 71 + slot), uint(row, 95 + slot)
            if effect >= effect_limit or aura >= aura_limit:
                errors.append(f'Spell {key} slot {slot}: effect/aura outside core bounds')
            if effect in effect_nulls and effect > 164:
                effects.setdefault(effect, set()).add(key)
            if effect in (6, 27, 35, 65, 119, 128, 129, 143, 190) and aura in aura_nulls:
                auras.setdefault(aura, set()).add(key)
            reference('Spell.TriggerSpell', uint(row, 116 + slot), 'Spell.dbc')
            reference('Spell.Radius', uint(row, 92 + slot), 'SpellRadius.dbc')
        for column, table in ((28, 'SpellCastTimes.dbc'), (40, 'SpellDuration.dbc'),
                              (46, 'SpellRange.dbc')):
            reference('Spell.' + table, uint(row, column), table)

    criteria_types = Counter()
    excluded = set()
    enums = source('src/server/shared/DataStores/DBCEnums.h')
    criteria_limit = constant('ACHIEVEMENT_CRITERIA_TYPE_TOTAL', enums)
    condition_limit = constant('ACHIEVEMENT_CRITERIA_CONDITION_TOTAL', enums)
    timer_limit = constant('ACHIEVEMENT_TIMED_TYPE_ITEM', enums) + 1
    for key, row in tables['Achievement_Criteria.dbc'].items():
        kind = uint(row, 2)
        if kind >= criteria_limit:
            criteria_types[kind] += 1
        if kind >= criteria_limit or uint(row, 5) >= condition_limit or uint(row, 7) >= condition_limit or (
                uint(row, 29) and uint(row, 27) >= timer_limit):
            excluded.add(uint(row, 1))
        reference('Criteria.Achievement', uint(row, 1), 'Achievement.dbc')

    for key, row in tables['TalentTab.dbc'].items():
        if uint(row, 22) >= 3:
            errors.append(f'TalentTab {key}: page outside three-page array')
    for key, row in tables['Talent.dbc'].items():
        reference('Talent.Tab', uint(row, 1), 'TalentTab.dbc')
        for column in range(4, 9):
            reference('Talent.Spell', uint(row, column), 'Spell.dbc')
    for key in tables['TaxiNodes.dbc']:
        if key > 448:
            errors.append(f'TaxiNodes {key}: exceeds 448-bit mask')
    for key, row in tables['TaxiPathNode.dbc'].items():
        path = uint(row, 1)
        reference('TaxiPathNode.Path', path, 'TaxiPath.dbc')
        if path > max(tables['TaxiPath.dbc'], default=0) or uint(row, 2) == 0xFFFFFFFF:
            errors.append(f'TaxiPathNode {key}: path/node index exceeds storage bounds')
    map_only = []
    for key, row in tables['WorldMapArea.dbc'].items():
        area = struct.unpack_from('<i', row, 8)[0]
        if area == -1:
            map_only.append(key)
        elif area < -1:
            errors.append(f'WorldMapArea {key}: unknown negative area {area}')
        else:
            reference('WorldMapArea.Area', area, 'AreaTable.dbc')
        reference('WorldMapArea.Map', uint(row, 1), 'Map.dbc')
    return {
        'scope': 'v20 files + dbc1-ascension; excludes SQL overlays and runtime scripts',
        'tables_checked': len(tables), 'overlays_checked': loaded, 'errors': errors,
        'map_only_row_ids': map_only,
        'placeholder_effect_spell_ids': {k: sorted(v) for k, v in effects.items()},
        # Some native auras are queried elsewhere rather than dispatched by a handler.
        'null_handler_aura_spell_ids': {k: sorted(v) for k, v in auras.items()},
        'unsupported_criteria_types': dict(criteria_types),
        'excluded_achievement_ids': sorted(excluded),
        'missing_reference_counts': dict(references),
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--details', action='store_true', help='Include full affected spell and achievement ID lists')
    args = parser.parse_args()
    result = audit(args.repo, args.data)
    if not args.details:
        for name in ('placeholder_effect_spell_ids', 'null_handler_aura_spell_ids'):
            if name in result:
                result[name.replace('_ids', '_counts')] = {k: len(v) for k, v in result.pop(name).items()}
        if 'excluded_achievement_ids' in result:
            result['excluded_achievement_count'] = len(result.pop('excluded_achievement_ids'))
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result['errors']))
