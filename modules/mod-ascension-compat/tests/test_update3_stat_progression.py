"""Replay the imported stat calculation against the matching export without a MySQL server."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location('audit_donor', Path(__file__).resolve().parents[1] / 'apps/audit_donor.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)
COLUMNS = 'Class Level BaseHP BaseMana Strength Agility Stamina Intellect Spirit'.split()


def fingerprint(rows):
    return hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()


class Update3StatProgression(unittest.TestCase):
    def test_matching_export_and_repeatable_progression(self):
        export = ROOT / '_CURRENT-DATABASE/acore_world'
        if not export.exists():
            self.skipTest('Local world export not present')
        records = sorted([row for _, row in AUDIT.rows(export / 'player_class_stats.sql')],
                         key=lambda row: (int(row['Class']), int(row['Level'])))
        classes = sorted([row for _, row in AUDIT.rows(export / 'ascension_custom_class.sql')],
                         key=lambda row: int(row['class']))
        inputs = {
            'classes': [[row['class'], row['fallback_class']] for row in classes if 12 <= int(row['class']) <= 32],
            'anchors': [[row[key] for key in COLUMNS] for row in records
                        if (1 <= int(row['Class']) <= 11 and 1 <= int(row['Level']) <= 80)
                        or (12 <= int(row['Class']) <= 32 and int(row['Level']) == 1)]}
        self.assertEqual(fingerprint(inputs), '288c771592499b058541f149b49836f5bb442a25a0bb15944399f947d7edabe8')
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.execute('CREATE TABLE player_class_stats (' + ','.join(key + ' INTEGER' for key in COLUMNS)
                   + ', PRIMARY KEY (Class, Level))')
        db.execute('CREATE TABLE ascension_custom_class (class INTEGER, fallback_class INTEGER)')
        db.executemany('INSERT INTO player_class_stats VALUES (?,?,?,?,?,?,?,?,?)',
                       [[int(row[key]) for key in COLUMNS] for row in records])
        db.executemany('INSERT INTO ascension_custom_class VALUES (?,?)',
                       [(int(row['class']), int(row['fallback_class'])) for row in classes])
        def custom_rows():
            return [[str(value) for value in row] for row in db.execute(
                'SELECT * FROM player_class_stats WHERE Class BETWEEN 12 AND 32 AND Level BETWEEN 2 AND 80 '
                'ORDER BY Class,Level')]
        self.assertEqual(fingerprint(custom_rows()), '502cb143aba816300bfb81b35c7247fdb14d0a0bb8369b05df9cbd07489fec46')
        unchanged = db.execute('SELECT * FROM player_class_stats WHERE Class < 12 OR Level = 1').fetchall()
        sql = (ROOT / 'data/sql/updates/pending_db_world/rev_20260912_00_custom_class_stat_progression.sql').read_text()
        # Translate only MySQL dialect syntax; execute the migration's actual expressions and joins.
        sql = sql.replace('CREATE TEMPORARY TABLE', 'CREATE TEMP TABLE').replace(' ENGINE=InnoDB AS', ' AS')
        sql = sql.replace('DROP TEMPORARY TABLE', 'DROP TABLE')
        sql = sql.replace('IF(', 'IIF(')
        sql = sql.replace('UPDATE `player_class_stats` AS `target`, `_coa_class_stat_progression` AS `source` SET',
                          'UPDATE `player_class_stats` AS `target` SET')
        for column in COLUMNS[2:]:
            sql = sql.replace(f'`target`.`{column}` =', f'`{column}` =')
        sql = sql.replace('WHERE `target`.`Class` =',
                          'FROM `_coa_class_stat_progression` AS `source` WHERE `target`.`Class` =')
        db.executescript(sql)
        self.assertEqual(fingerprint(custom_rows()), '627b12dfe796cd3fdb54168f88c76415efe451e183a1542bcd3c9dc20c851289')
        self.assertEqual(len(custom_rows()), 21 * 79)
        self.assertEqual(db.execute('SELECT * FROM player_class_stats WHERE Class < 12 OR Level = 1').fetchall(), unchanged)
        db.executescript(sql)
        self.assertEqual(fingerprint(custom_rows()), '627b12dfe796cd3fdb54168f88c76415efe451e183a1542bcd3c9dc20c851289')


if __name__ == '__main__':
    unittest.main()
