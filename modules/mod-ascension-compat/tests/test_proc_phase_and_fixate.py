"""Check the new proc migration against the export and preserve the Ascension Fixate row."""
import importlib.util
from pathlib import Path
import re
import sqlite3
import struct
import unittest

ROOT = Path(__file__).resolve().parents[3]
IDS = {22648, 46910, 46911, 51123, 51127, 51128, 51129, 51130}
SPEC = importlib.util.spec_from_file_location(
    'encounter_dbc', ROOT / 'modules/mod-ascension-compat/apps/build_encounter_dbc_continuation.py')
DBC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DBC)


class ProcPhaseAndFixate(unittest.TestCase):
    def test_export_replay_changes_only_the_eight_missing_phases(self):
        source = (ROOT / '_CURRENT-DATABASE/acore_world/spell_proc.sql').read_text(encoding='utf-8')
        columns = re.findall(r'^  `([^`]+)`', source, re.M)
        values = [tuple(float(v.strip()) if '.' in v else int(v.strip()) for v in row.split(','))
                  for row in re.findall(r'^\s*\(([-\d., ]+)\)[,;]', source, re.M)]
        self.assertGreater(len(values), 1000)
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('CREATE TABLE spell_proc (' + ','.join(f'`{c}` NUMERIC' for c in columns) + ')')
        db.executemany('INSERT INTO spell_proc VALUES (' + ','.join('?' for _ in columns) + ')', values)
        before = dict((r[0], r) for r in db.execute('SELECT * FROM spell_proc'))
        migration = (ROOT / 'data/sql/updates/pending_db_world/rev_20260912_08_melee_proc_hit_phase.sql').read_text()
        for _ in range(2):
            db.executescript(migration)
            after = dict((r[0], r) for r in db.execute('SELECT * FROM spell_proc'))
            self.assertEqual({key for key in before if before[key] != after[key]}, IDS)
            for spell in IDS:
                changed = [i for i, (old, new) in enumerate(zip(before[spell], after[spell])) if old != new]
                self.assertEqual(changed, [columns.index('SpellPhaseMask')])
                self.assertEqual(after[spell][8], 2)
        db.execute('UPDATE spell_proc SET SpellPhaseMask=4 WHERE SpellId=22648')
        db.executescript(migration)
        self.assertEqual(db.execute('SELECT SpellPhaseMask FROM spell_proc WHERE SpellId=22648').fetchone()[0], 4)

    def test_proc_contracts_and_trigger_dependencies(self):
        path = ROOT / 'env/dist/bin/data/dbc-continuations/Spell.dbc1-ascension'
        spells = DBC.read_rows(path, IDS)
        triggers = {row[116] for row in spells.values()}
        self.assertNotIn(0, triggers)
        self.assertEqual(set(DBC.read_rows(path, triggers)), triggers)
        self.assertEqual(set(spells), IDS)
        for row in spells.values():
            self.assertEqual(row[71], 6)
            self.assertEqual(row[95], 42)
            self.assertTrue(row[34] & 0x10)  # DONE_SPELL_MELEE_DMG_CLASS: requires spell phase.
        header = (ROOT / 'src/server/game/Spells/SpellMgr.h').read_text()
        self.assertRegex(header, r'PROC_SPELL_PHASE_HIT\s*=\s*0x0000002')

    def test_fixate_preserves_every_other_field_and_string(self):
        folder = ROOT / 'env/dist/bin/data/dbc-continuations'
        before = DBC.read_rows(folder / 'Spell.dbc1-ascension', {12021})[12021]
        after = DBC.read_rows(folder / 'Spell.dbc3-scholomance-fixate', {12021})[12021]
        self.assertEqual([i for i, pair in enumerate(zip(before, after)) if pair[0] != pair[1]], [95])
        self.assertEqual((after[71], after[95], after[86]), (6, 4, 6))
        binary = (folder / 'Spell.dbc3-scholomance-fixate').read_bytes()
        self.assertEqual(struct.unpack_from('<I', binary, 4)[0], 1)


if __name__ == '__main__':
    unittest.main()
