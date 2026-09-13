"""Exercise the pending skill migration and, when available, the supplied DBC stack and startup log."""

from pathlib import Path
import sqlite3
import struct
import unittest


ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / 'data/sql/updates/pending_db_world/rev_20260912_00_restore_stock_class_skill_permissions.sql'


def dbc_rows(path):
    data = path.read_bytes()
    magic, count, fields, size, strings = struct.unpack_from('<4s4I', data)
    assert (magic, fields, size) == (b'WDBC', 8, 32)
    assert len(data) == 20 + count * size + strings
    return {row[0]: row for row in struct.iter_unpack('<8I', data[20:20 + count * size])}


class StockSkillPermissions(unittest.TestCase):
    def test_hunter_thrown_permission_survives_continuations(self):
        baseline = ROOT / '_data/dbc/SkillRaceClassInfo.dbc'
        overlay = ROOT / '_data/dbc-continuations/SkillRaceClassInfo.dbc1-ascension'
        if not baseline.exists() or not overlay.exists():
            self.skipTest('Local DBCs are not present')
        rows, additions = dbc_rows(baseline), dbc_rows(overlay)
        self.assertEqual(rows[143], (143, 176, 4294967295, 4, 128, 0, 0, 0))
        sql = (ROOT / 'data/sql/updates/pending_db_world/rev_20260912_05_restore_hunter_thrown_permission.sql')
        self.db.executescript(sql.read_text())
        patch = self.db.execute('SELECT * FROM skillraceclassinfo_dbc WHERE ID = 529').fetchone()
        self.assertNotIn(529, rows)
        self.assertNotIn(529, additions)
        rows.update(additions)
        self.assertFalse(any(row[1] == 176 and row[3] & 4 for row in rows.values()))
        rows[529] = patch
        for race in (1, 2, 3, 4, 5, 6, 7, 8, 10, 11):
            self.assertTrue(any(row[1] == 176 and row[2] & (1 << (race - 1)) and row[3] & 4
                                for row in rows.values()))
        self.db.executescript(sql.read_text())
        self.assertEqual(self.db.execute('SELECT * FROM skillraceclassinfo_dbc WHERE ID = 529').fetchall(), [patch])

    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE skillraceclassinfo_dbc ('
                        'ID INTEGER PRIMARY KEY, SkillID INTEGER, RaceMask INTEGER, ClassMask INTEGER, '
                        'Flags INTEGER, MinLevel INTEGER, SkillTierID INTEGER, SkillCostIndex INTEGER)')
        self.sql = MIGRATION.read_text(encoding='utf-8')

    def test_migration_is_repeatable_and_preserves_other_permissions(self):
        self.db.execute('INSERT INTO skillraceclassinfo_dbc VALUES (3, 26, -1, 512, 1040, 0, 0, 0)')
        self.db.executescript(self.sql)
        before = self.db.execute('SELECT * FROM skillraceclassinfo_dbc ORDER BY ID').fetchall()
        self.db.executescript(self.sql)
        self.assertEqual(before, self.db.execute('SELECT * FROM skillraceclassinfo_dbc ORDER BY ID').fetchall())
        self.assertEqual(before[0], (3, 26, -1, 512, 1040, 0, 0, 0))
        self.assertEqual([(row[1], row[3]) for row in before[1:]], [(26, 1), (354, 256)])

    def test_real_stack_accepts_reported_race_class_pairs(self):
        baseline = ROOT / '_data/dbc/SkillRaceClassInfo.dbc'
        overlay = ROOT / '_data/dbc-continuations/SkillRaceClassInfo.dbc1-ascension'
        if not all(path.exists() for path in (baseline, overlay)):
            self.skipTest('Local DBCs are not present')
        rows, additions = dbc_rows(baseline), dbc_rows(overlay)
        self.db.executescript(self.sql)
        patches = self.db.execute('SELECT * FROM skillraceclassinfo_dbc').fetchall()
        for row in patches:
            self.assertNotIn(row[0], rows)
            self.assertNotIn(row[0], additions)
            rows[row[0]] = row
        rows.update(additions)  # Native load order: base, SQL, then continuations.
        rejected = [(skill, race, cls) for skill, cls in ((26, 1), (354, 9))
                    for race in (1, 2, 3, 4, 5, 6, 7, 8, 10, 11)]
        for skill, race, cls in set(rejected):
            self.assertTrue(any(row[1] == int(skill) and
                                (not row[2] or row[2] & (1 << (int(race) - 1))) and
                                (not row[3] or row[3] & (1 << (int(cls) - 1))) for row in rows.values()),
                            (skill, race, cls))
        for skill in (26, 354):
            self.assertTrue(any(row[1] == skill and row[3] & 512 for row in rows.values()))


if __name__ == '__main__':
    unittest.main()
