"""Replay the totem migration and validate its real DBC spell/model dependencies."""
from pathlib import Path
import re
import sqlite3
import struct
import unittest

ROOT = Path(__file__).resolve().parents[3]
SQL = ROOT / 'data/sql/updates/pending_db_world/rev_20260912_07_ascension_totem_templates.sql'


def records(table, ids):
    result = {}
    paths = [ROOT / f'env/dist/bin/data/dbc/{table}.dbc']
    paths += sorted((ROOT / 'env/dist/bin/data/dbc-continuations').glob(f'{table}.dbc[1-9]-*'))
    for path in paths:
        data = path.read_bytes()
        _, count, fields, size, _ = struct.unpack_from('<4s4I', data)
        for offset in range(20, 20 + count * size, size):
            key = struct.unpack_from('<I', data, offset)[0]
            if key in ids:
                result[key] = struct.unpack_from(f'<{fields}I', data, offset)
    return result


class TotemTemplates(unittest.TestCase):
    def test_migration_repeatability_and_unrelated_rows(self):
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        for table in ('creature_template', 'creature_template_model', 'creature_template_spell', 'spell_script_names'):
            source = (ROOT / f'_CURRENT-DATABASE/acore_world/{table}.sql').read_text(encoding='utf-8')
            columns = re.findall(r'^  `([^`]+)` ([^\n]+)', source, re.M)
            # Use the exported column names, retaining numeric affinity for values under test.
            definitions = [f'`{name}` ' + ('TEXT' if 'char' in kind else 'NUMERIC') for name, kind in columns]
            db.execute(f'CREATE TABLE `{table}` ({", ".join(definitions)})')
        db.execute('CREATE UNIQUE INDEX ct_id ON creature_template(entry)')
        db.execute('CREATE UNIQUE INDEX cm_id ON creature_template_model(CreatureID, Idx)')
        db.execute('CREATE UNIQUE INDEX cs_id ON creature_template_spell(CreatureID, `Index`)')
        db.execute('CREATE UNIQUE INDEX ss_id ON spell_script_names(spell_id, ScriptName)')
        db.execute("INSERT INTO creature_template(entry,name) VALUES (42,'preserve')")
        db.execute("INSERT INTO spell_script_names VALUES (1152041,'unrelated_script')")
        def apply():
            migration = SQL.read_text()
            # Evaluate MySQL session-variable assignments using the actual preceding SELECT.
            assignments = re.findall(r'SET (@\w+) := ([^;]+);', migration)
            for variable, expression in assignments:
                value = db.execute('SELECT ' + expression).fetchone()[0]
                migration = migration.replace(f'SET {variable} := {expression};', '')
                migration = migration.replace(variable, str(value))
            db.executescript(migration)
        for _ in range(2):
            apply()
            self.assertEqual(db.execute('SELECT entry,type,unit_class,faction FROM creature_template '
                                        'WHERE entry<>42 ORDER BY entry').fetchall(),
                             [(1102523, 11, 1, 35), (1103527, 11, 1, 35)])
            self.assertEqual(db.execute('SELECT CreatureID,Spell FROM creature_template_spell '
                                        'ORDER BY CreatureID').fetchall(), [(1102523, 1103606), (1103527, 1105672)])
            self.assertEqual(db.execute('SELECT CreatureDisplayID FROM creature_template_model '
                                        'ORDER BY CreatureID').fetchall(), [(4589,), (4587,)])
            self.assertEqual(db.execute('SELECT name FROM creature_template WHERE entry=42').fetchone()[0], 'preserve')
            self.assertEqual(db.execute('SELECT COUNT(*) FROM spell_script_names').fetchone()[0], 2)
        db.execute("UPDATE creature_template SET name='customized' WHERE entry=1102523")
        apply()
        self.assertEqual(db.execute('SELECT name FROM creature_template WHERE entry=1102523').fetchone()[0], 'customized')

    def test_summon_attack_heal_and_model_contracts(self):
        spells = records('Spell', {1103599, 1105394, 1103606, 1105672, 1152041, 52042, 55456})
        self.assertEqual(spells[1103599][110], 1102523)
        self.assertEqual(spells[1105394][110], 1103527)
        for spell in (1103599, 1105394):
            self.assertEqual(spells[spell][71], 28)
            self.assertEqual(spells[spell][80] + spells[spell][74], 5)
        attack = spells[1103606]
        self.assertEqual(attack[71], 2)
        cast_time = records('SpellCastTimes', {attack[28]})[attack[28]][1]
        self.assertGreater(cast_time, 0)  # Native TotemAI must classify it as active.
        self.assertEqual(tuple(spells[1105672][i] for i in (71, 95, 98, 116)), (6, 23, 2000, 1152041))
        self.assertEqual(spells[1152041][71], 3)  # Native healing script binds to this dummy.
        self.assertEqual(spells[52042][71], 10)
        self.assertIn(55456, spells)  # Native script's Validate dependency.
        displays = records('CreatureDisplayInfo', {4587, 4589})
        self.assertEqual(set(displays), {4587, 4589})
        models = {row[1] for row in displays.values()}
        self.assertEqual(set(records('CreatureModelData', models)), models)


if __name__ == '__main__':
    unittest.main()
