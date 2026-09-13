"""Replay the guarded item display migration without a live database."""

from pathlib import Path
import sqlite3
import unittest


ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / 'data/sql/updates/pending_db_world/rev_20260912_01_stacked_dbc_item_displays.sql'


class StackedItemDisplays(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.addCleanup(self.db.close)
        self.db.execute('CREATE TABLE item_template (entry INTEGER PRIMARY KEY, displayid INTEGER, name TEXT)')
        self.sql = MIGRATION.read_text(encoding='utf-8')

    def test_preserves_conflicting_and_unrelated_templates(self):
        self.db.executemany('INSERT INTO item_template VALUES (?, ?, ?)', [
            (629930, 18662, 'Painted Plank Shield'),
            (2000004, 999999, 'Independently changed'),
            (42, 10, 'Unrelated item'),
        ])
        self.db.executescript(self.sql)
        expected = [(42, 10, 'Unrelated item'), (629930, 143525, 'Painted Plank Shield'),
                    (2000004, 999999, 'Independently changed')]
        self.assertEqual(self.db.execute('SELECT * FROM item_template ORDER BY entry').fetchall(), expected)
        self.db.executescript(self.sql)
        self.assertEqual(self.db.execute('SELECT * FROM item_template ORDER BY entry').fetchall(), expected)



if __name__ == '__main__':
    unittest.main()
