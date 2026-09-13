"""Replay creation data migration against the supplied export without a live server."""
import importlib.util
from pathlib import Path
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('audit_donor', Path(__file__).resolve().parents[1] / 'apps/audit_donor.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class AllRaceClassCreation(unittest.TestCase):
    def test_complete_matrix_and_preserve_existing_starts(self):
        export = ROOT / '_CURRENT-DATABASE/acore_world'
        if not export.exists():
            self.skipTest('Local world export is not present')
        records = [row for _, row in AUDIT.rows(export / 'playercreateinfo.sql')]
        columns = list(records[0])
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('CREATE TABLE playercreateinfo (' + ','.join('`' + key + '` NUMERIC' for key in columns)
                   + ', PRIMARY KEY (race, class))')
        db.executemany('INSERT INTO playercreateinfo VALUES (' + ','.join('?' for _ in columns) + ')',
                       [list(row.values()) for row in records])
        before = {(row[0], row[1]): row for row in db.execute('SELECT * FROM playercreateinfo')}
        sql = (ROOT / 'data/sql/updates/pending_db_world/rev_20260912_03_all_race_class_creation.sql').read_text()
        db.executescript(sql)
        after = {(row[0], row[1]): row for row in db.execute('SELECT * FROM playercreateinfo')}
        races = (1, 2, 3, 4, 5, 6, 7, 8, 10, 11)
        classes = tuple(range(1, 10)) + tuple(range(11, 33))
        self.assertEqual(set(after), {(race, cls) for race in races for cls in classes})
        self.assertEqual(len(after) - len(before), 38)
        self.assertTrue(all(after[pair] == row for pair, row in before.items()))
        self.assertEqual(after[10, 30], before[10, 30])
        for (race, cls), row in after.items():
            if (race, cls) not in before:
                self.assertTrue(any(old[0] == race and old[1] != 6 and old[2:] == row[2:]
                                    for old in before.values()))
        db.executescript(sql)
        self.assertEqual(after, {(row[0], row[1]): row for row in db.execute('SELECT * FROM playercreateinfo')})
        stats = {(int(row['Class']), int(row['Level'])) for _, row in AUDIT.rows(export / 'player_class_stats.sql')}
        self.assertTrue(all((cls, level) in stats for cls in classes for level in range(55 if cls == 6 else 1, 81)))
        self.assertEqual({int(row['Race']) for _, row in AUDIT.rows(export / 'player_race_stats.sql')}, set(races))


if __name__ == '__main__':
    unittest.main()
