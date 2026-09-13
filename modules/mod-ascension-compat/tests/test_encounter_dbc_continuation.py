"""Validate the shipped binary, hook contracts, and preservation of Ascension data."""
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    'encounter_dbc', ROOT / 'modules/mod-ascension-compat/apps/build_encounter_dbc_continuation.py')
dbc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dbc)


class EncounterContinuation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = ROOT / 'env/dist/bin/data/dbc-continuations'
        cls.original = dbc.read_rows(directory / 'Spell.dbc1-ascension')
        cls.fixed = dbc.read_rows(directory / dbc.NAME)
        cls.stock = dbc.read_rows(ROOT / 'env/dist/bin/data/dbc/Spell.dbc')

    def test_only_reviewed_fields_change(self):
        allowed = {802: {46, *range(86, 95)}, 804: {46, *range(86, 95)},
                   818: {86}, 9347: {95, 98, 116}, 21094: {95, 98}, 23487: {95, 98}}
        self.assertEqual(set(self.fixed), set(allowed))
        for spell, fields in allowed.items():
            changed = {i for i, (old, new) in enumerate(zip(self.original[spell], self.fixed[spell]))
                       if old != new}
            self.assertEqual(changed, fields, spell)
            for field in dbc.STRINGS:
                self.assertEqual(self.fixed[spell][field], self.original[spell][field])

    def test_native_hook_contracts_and_dependencies(self):
        for spell in (802, 804):
            self.assertEqual(self.fixed[spell][86:95], self.stock[spell][86:95])
        self.assertEqual(self.fixed[818][86], 32)
        self.assertEqual(tuple(self.fixed[9347][i] for i in (95, 98, 116)), (23, 11000, 24573))
        trigger = dbc.read_rows(ROOT / 'env/dist/bin/data/dbc-continuations/Spell.dbc1-ascension', {24573})
        self.assertIn(24573, trigger)
        sql = (ROOT / 'data/sql/base/db_world/spell_dbc.sql').read_text()
        for spell in (21094, 23487):
            # Check timer/aura against the independently maintained server helper definition.
            prefix = re.search(rf'^\({spell},(.+)', sql, re.M).group(0).split("'", 1)[0]
            fields = prefix.lstrip('(').rstrip(',').split(',')
            for field in (95, 98):
                self.assertEqual(self.fixed[spell][field], int(fields[field]))

    def test_deterministic_round_trip_and_guard(self):
        rows = dbc.corrected_rows(self.stock, self.original)
        binary = dbc.encode(rows)
        self.assertEqual(binary, (ROOT / 'env/dist/bin/data/dbc-continuations' / dbc.NAME).read_bytes())
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'Spell.dbc'
            path.write_bytes(binary)
            self.assertEqual(dbc.read_rows(path), rows)
        changed = {spell: row.copy() for spell, row in self.original.items()}
        changed[9347][116] = 123
        with self.assertRaises(AssertionError):
            dbc.corrected_rows(self.stock, changed)


if __name__ == '__main__':
    unittest.main()
