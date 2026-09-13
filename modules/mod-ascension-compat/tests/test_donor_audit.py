"""Check SQL parsing and conservative donor classification without a live database."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    'audit_donor', Path(__file__).resolve().parents[1] / 'apps/audit_donor.py')
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class DonorAuditTest(unittest.TestCase):
    def test_rank_conflicts_and_missing_references(self):
        def row(first, spell, rank):
            return dict(first_spell_id=str(first), spell_id=str(spell), rank=str(rank))
        donor = [row(10, 10, 1), row(10, 11, 2), row(20, 20, 1), row(20, 21, 2),
                 row(30, 30, 1), row(30, 31, 2), row(40, 40, 1), row(40, 41, 3),
                 row(50, 50, 1), row(50, 51, 2)]
        current = [row(10, 10, 1), row(10, 11, 2), row(20, 20, 1)]
        result = AUDIT.rank_audit(donor, current, {10, 11, 20, 21, 30, 40, 41, 50, 51})['chain_ids']
        self.assertEqual(result, dict(identical=[10], invalid_structure=[40], missing_spells=[30],
                                      conflicting_existing=[20], candidate_new_chains=[50]))

    def test_escaped_strings(self):
        self.assertEqual(AUDIT.cells("1, 'Champion''s, sword', 'a\\'b', ''"),
                         ['1', "'Champion''s, sword'", "'a\\'b'", "''"])
        with self.assertRaises(ValueError):
            AUDIT.cells("1, 'unfinished")

    def test_missing_and_nonempty_names_are_not_repair_candidates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            donor, current = root / 'donor', root / 'current'
            donor.mkdir()
            current.mkdir()
            (donor / 'rev_test.sql').write_text(
                "INSERT INTO `item_template` (`entry`, `name`) VALUES\n"
                "(1, 'Recovered'),\n(2, 'Different'),\n(3, 'Missing template');\n", encoding='utf-8')
            (current / 'item_template.sql').write_text(
                "CREATE TABLE `item_template` (\n  `entry` int,\n  `name` text\n) ENGINE=InnoDB;\n"
                "INSERT INTO `item_template` (`entry`, `name`) VALUES\n(1, ''),\n(2, 'Curated');\n",
                encoding='utf-8')
            result = AUDIT.audit(donor, current)
            self.assertEqual(result['tables']['item_template']['existing_ids'], 2)
            self.assertEqual(result['tables']['item_template']['absent_ids'], 1)
            self.assertEqual(result['tables']['item_template']['unknown_columns'], [])
            self.assertEqual([row['id'] for row in result['empty_name_candidates']], [1])

    def test_rejects_misaligned_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.sql'
            path.write_text("INSERT INTO `t` (`id`, `name`) VALUES\n(1);\n", encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'column count'):
                list(AUDIT.rows(path))


if __name__ == '__main__':
    unittest.main()
