"""Restore encounter selectors required by the existing native target filters."""
from build_encounter_dbc_continuation import ROOT, read_rows, encode

NAME = 'Spell.dbc5-scripted-encounter-targets'
IDS = {23410, 23414, 23418, 23425, 23436, 24778, 30843, 31298, 62166, 63981}


def corrected_rows(stock, ascension):
    assert set(stock) == set(ascension) == IDS
    result = {}
    for spell in sorted(IDS):
        before, reference = ascension[spell], stock[spell]
        assert before[136] == reference[136], spell
        assert before[71:74] == reference[71:74], spell
        assert before[86:95] != reference[86:95], spell
        # Dream Fog uses a destination-area filter; the others use source-area enemy filters.
        target = 16 if spell == 24778 else 15
        for effect in range(3):
            if before[71 + effect]:
                assert reference[89 + effect] == target, spell
                assert reference[92 + effect] != 0, spell
        row = before.copy()
        row[86:95] = reference[86:95]
        result[spell] = row
    return result


def main():
    data = ROOT / 'env/dist/bin/data'
    stock = read_rows(data / 'dbc/Spell.dbc', IDS)
    ascension = read_rows(data / 'dbc-continuations/Spell.dbc1-ascension', IDS)
    binary = encode(corrected_rows(stock, ascension))
    output = data / 'dbc-continuations' / NAME
    if output.exists() and output.read_bytes() != binary:
        raise RuntimeError('Allocate a new continuation instead of overwriting an existing change')
    output.write_bytes(binary)
    print(f'{output}: {len(IDS)} rows, {len(binary)} bytes')


if __name__ == '__main__':
    main()
