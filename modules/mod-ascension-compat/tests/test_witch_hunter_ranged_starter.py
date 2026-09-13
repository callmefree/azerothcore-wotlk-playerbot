"""Replay the ranged starter correction; check permissions against real stacked DBCs."""
from pathlib import Path
import sqlite3
import struct
import unittest

ROOT = Path(__file__).resolve().parents[3]


class WitchHunterRangedStarter(unittest.TestCase):
    def test_rifle_guard_and_permission(self):
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('CREATE TABLE item_template (entry INTEGER PRIMARY KEY, class INTEGER, subclass INTEGER, '
                   'InventoryType INTEGER, RangedModRange REAL)')
        db.execute('CREATE TABLE skillraceclassinfo_dbc (ID INTEGER PRIMARY KEY, SkillID INTEGER, '
                   'RaceMask INTEGER, ClassMask INTEGER, Flags INTEGER, MinLevel INTEGER, '
                   'SkillTierID INTEGER, SkillCostIndex INTEGER)')
        db.executemany('INSERT INTO item_template VALUES (?,?,?,?,?)',
                       [(484364, 2, 3, 26, 0), (2510, 2, 3, 26, 100), (42, 2, 3, 26, 0)])
        db.execute('INSERT INTO skillraceclassinfo_dbc VALUES (184,11163,-1,4,1040,0,0,0)')
        sql = (ROOT / 'data/sql/updates/pending_db_world/rev_20260912_06_witch_hunter_ranged_starter.sql').read_text()
        continuation = ROOT / 'env/dist/bin/data/dbc-continuations/SkillRaceClassInfo.dbc2-witch-hunter-auto-shot'
        data = continuation.read_bytes()
        self.assertEqual(struct.unpack_from('<4s4I', data), (b'WDBC', 1, 8, 32, 1))
        self.assertEqual(len(data), 53)
        self.assertEqual(data[-1:], b'\0')
        patch = struct.unpack_from('<IIi5I', data, 20)
        db.execute('INSERT INTO skillraceclassinfo_dbc VALUES (?,?,?,?,?,?,?,?)', patch)
        db.executescript(sql)
        self.assertEqual(db.execute('SELECT entry,RangedModRange FROM item_template ORDER BY entry').fetchall(),
                         [(42, 0), (2510, 100), (484364, 100)])
        permissions = db.execute('SELECT * FROM skillraceclassinfo_dbc ORDER BY ID').fetchall()
        self.assertEqual(permissions[0], (184, 11163, -1, 4, 1040, 0, 0, 0))
        self.assertEqual(permissions[1], (530, 11163, -1, 16384, 1040, 0, 0, 0))
        db.executescript(sql)
        self.assertEqual(db.execute('SELECT * FROM skillraceclassinfo_dbc ORDER BY ID').fetchall(), permissions)
        db.execute('UPDATE item_template SET RangedModRange=120 WHERE entry=484364')
        db.executescript(sql)
        self.assertEqual(db.execute('SELECT RangedModRange FROM item_template WHERE entry=484364').fetchone()[0], 120)
        paths = [ROOT / '_data/dbc/SkillRaceClassInfo.dbc',
                 ROOT / '_data/dbc-continuations/SkillRaceClassInfo.dbc1-ascension']
        if not all(path.exists() for path in paths):
            self.skipTest('Local DBC collision check requires supplied files')
        rows = {}
        for path in paths:
            data = path.read_bytes()
            magic, count, fields, size, strings = struct.unpack_from('<4s4I', data)
            self.assertEqual((magic, fields, size), (b'WDBC', 8, 32))
            layer = {row[0]: row for row in struct.iter_unpack('<8I', data[20:20 + count * size])}
            self.assertNotIn(530, layer)
            rows.update(layer)
        self.assertFalse(any(row[1] == 11163 and row[3] & 16384 for row in rows.values()))
        rows[530] = permissions[1]
        for race in (1, 2, 3, 4, 5, 6, 7, 8, 10, 11):
            self.assertTrue(any(row[1] == 11163 and row[2] & (1 << (race - 1)) and row[3] & 16384
                                for row in rows.values()))


if __name__ == '__main__':
    unittest.main()
