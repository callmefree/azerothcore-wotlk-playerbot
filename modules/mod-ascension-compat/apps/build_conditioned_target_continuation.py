"""Restore proven nearby-entry targets without rewriting the Ascension layer."""
from pathlib import Path
from build_encounter_dbc_continuation import ROOT, read_rows, encode

NAME = 'Spell.dbc4-conditioned-npc-targets'
# Each has source-type 13, effect mask 1 conditions naming creature entries.
# Spell effects/aura types still match v20; only the selected-unit target changed.
IDS = {10259, 12938, 15281, 16637, 28159, 30834, 34156, 36089, 36090, 36196,
       36197, 36198, 42542, 45581, 46474, 49555, 51024, 52238, 56393, 59807}


def corrected_rows(stock, ascension):
    assert set(stock) == set(ascension) == IDS
    result = {}
    for spell in sorted(IDS):
        before, reference = ascension[spell], stock[spell]
        assert before[136] == reference[136], spell
        assert before[71:74] == reference[71:74], spell
        assert before[95:98] == reference[95:98], spell
        assert before[86] == (21 if spell == 16637 else 25), spell
        assert before[89] == reference[89] == 0, spell
        assert reference[86] == 38, spell
        row = before.copy()
        row[86] = reference[86]
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
