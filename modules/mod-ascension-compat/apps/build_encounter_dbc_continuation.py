"""Build a new Spell continuation; never rewrite the stock or Ascension layers.

Only restore data required by the existing encounter scripts. Preserve Ascension
damage, duration, descriptions and all other fields, including Explode Bug's timer.
"""
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[3]
NAME = 'Spell.dbc2-native-encounter-hooks'
STRINGS = tuple(i for start in (136, 153, 170, 187) for i in range(start, start + 16))
IDS = {802, 804, 818, 9347, 21094, 23487}


def read_rows(path, ids=IDS):
    data = path.read_bytes()
    magic, count, fields, size, string_size = struct.unpack_from('<4s4I', data)
    assert (magic, fields, size) == (b'WDBC', 234, 936)
    end = 20 + count * size
    assert len(data) == end + string_size
    strings = data[end:]
    rows = {}
    for offset in range(20, end, size):
        spell = struct.unpack_from('<I', data, offset)[0]
        if spell not in ids:
            continue
        assert spell not in rows
        row = list(struct.unpack_from('<234I', data, offset))
        for index in STRINGS:
            start = row[index]
            assert start < len(strings)
            row[index] = strings[start:strings.index(b'\0', start)]
        rows[spell] = row
    return rows


def corrected_rows(stock, ascension):
    assert set(ascension) == IDS
    rows = {spell: row.copy() for spell, row in ascension.items()}
    # Both bosses cast AOE with no selected unit. Their script selects one eligible
    # scarab/scorpion from TARGET_UNIT_SRC_AREA_ENTRY; target 25 supplies no list.
    for spell in (802, 804):
        assert rows[spell][86:95] == [25, 25, 25, 0, 0, 0, 0, 0, 0]
        assert stock[spell][86:92] == [22, 22, 22, 7, 7, 7]
        rows[spell][86:95] = stock[spell][86:95]
        rows[spell][46] = stock[spell][46]
    # Restore the summon destination used by the campfire floor-height correction.
    assert rows[818][71] == 50 and rows[818][86] == 47
    assert stock[818][86] == 32
    rows[818][86] = stock[818][86]
    # Anubisath's script requires a periodic trigger and reads its trigger spell.
    assert rows[9347][95] == 4 and rows[9347][98] == rows[9347][116] == 0
    assert (stock[9347][95], stock[9347][98], stock[9347][116]) == (23, 11000, 24573)
    for index in (95, 98, 116):
        rows[9347][index] = stock[9347][index]
    # These server encounter helpers are defined as periodic dummy, 1000 ms, in
    # data/sql/base/db_world/spell_dbc.sql. The later Ascension layer erases the timer.
    for spell in (21094, 23487):
        assert rows[spell][71] == 6 and rows[spell][95] == 4 and rows[spell][98] == 0
        rows[spell][95] = 226
        rows[spell][98] = 1000
    return rows


def encode(rows):
    strings = bytearray(b'\0')
    offsets = {b'': 0}
    records = bytearray()
    for spell in sorted(rows):
        row = rows[spell].copy()
        for index in STRINGS:
            value = row[index]
            if value not in offsets:
                offsets[value] = len(strings)
                strings.extend(value + b'\0')
            row[index] = offsets[value]
        records.extend(struct.pack('<234I', *row))
    return struct.pack('<4s4I', b'WDBC', len(rows), 234, 936, len(strings)) + records + strings


def main():
    stock = read_rows(ROOT / 'env/dist/bin/data/dbc/Spell.dbc')
    ascension = read_rows(ROOT / 'env/dist/bin/data/dbc-continuations/Spell.dbc1-ascension')
    output = ROOT / 'env/dist/bin/data/dbc-continuations' / NAME
    data = encode(corrected_rows(stock, ascension))
    if output.exists() and output.read_bytes() != data:
        raise RuntimeError('Existing continuation differs; allocate a new tier/name instead')
    output.write_bytes(data)
    print(f'{output}: {len(IDS)} rows, {len(data)} bytes')


if __name__ == '__main__':
    main()
