"""Verify item corrections against independent exported SQL and stacked binary records."""
import importlib.util
from pathlib import Path
import re
import sqlite3
import struct
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('audit_donor', Path(__file__).resolve().parents[1] / 'apps/audit_donor.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class ItemDbcMigrations(unittest.TestCase):
    def test_exported_values_and_effective_dbc(self):
        export = ROOT / '_CURRENT-DATABASE/acore_world/item_template.sql'
        paths = [ROOT / '_data/dbc/Item.dbc', ROOT / '_data/dbc-continuations/Item.dbc1-ascension']
        if not all(path.exists() for path in [export] + paths):
            self.skipTest('Local export and DBCs are not present')
        items = {}
        for path in paths:
            data = path.read_bytes()
            magic, count, fields, size, strings = struct.unpack_from('<4s4I', data)
            self.assertEqual((magic, fields, size), (b'WDBC', 8, 32))
            self.assertEqual(len(data), 20 + count * size + strings)
            items.update({row[0]: row for row in struct.iter_unpack('<8i', data[20:20 + count * size])})
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('CREATE TABLE item_template (entry INTEGER PRIMARY KEY, displayid INTEGER, Material INTEGER)')
        db.executemany('INSERT INTO item_template VALUES (?, ?, ?)',
                       ((int(row['entry']), int(row['displayid']), int(row['Material']))
                        for _, row in AUDIT.rows(export)))
        for suffix, column, field, expected_count in (
                ('01_stacked_dbc_item_displays', 'displayid', 5, 24),
                ('04_stacked_dbc_item_materials', 'Material', 4, 5)):
            sql = (ROOT / f'data/sql/updates/pending_db_world/rev_20260912_{suffix}.sql').read_text()
            changes = re.findall(r'SET `' + column + r'` = (\d+) WHERE `entry` = (\d+) AND `'
                                 + column + r'` = (\d+)', sql)
            self.assertEqual(len(changes), expected_count)
            for new, entry, old in changes:
                self.assertEqual(db.execute(f'SELECT {column} FROM item_template WHERE entry = ?',
                                            (int(entry),)).fetchone()[0], int(old))
                self.assertEqual(items[int(entry)][field], int(new))
            before = dict(db.execute(f'SELECT entry, {column} FROM item_template'))
            db.executescript(sql)
            expected = dict(before)
            expected.update({int(entry): int(new) for new, entry, old in changes})
            self.assertEqual(dict(db.execute(f'SELECT entry, {column} FROM item_template')), expected)
            db.executescript(sql)
            self.assertEqual(dict(db.execute(f'SELECT entry, {column} FROM item_template')), expected)
            new, entry, old = map(int, changes[0])
            db.execute(f'UPDATE item_template SET {column} = 999999 WHERE entry = ?', (entry,))
            db.executescript(sql)
            self.assertEqual(db.execute(f'SELECT {column} FROM item_template WHERE entry = ?', (entry,)).fetchone()[0],
                             999999)


if __name__ == '__main__':
    unittest.main()
