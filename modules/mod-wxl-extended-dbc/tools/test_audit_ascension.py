import struct
import tempfile
from pathlib import Path
import unittest

from audit_ascension import read_dbc, uint


class DbcAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'fixture.dbc'

    def write(self, rows, fields, size, strings=b'\0'):
        self.path.write_bytes(struct.pack('<4s4I', b'WDBC', len(rows), fields, size, len(strings))
                              + b''.join(rows) + strings)

    def test_map_only_rows_keep_their_own_ids(self):
        self.write([struct.pack('<III', 1000, 1760, 0xFFFFFFFF),
                    struct.pack('<III', 1001, 1761, 0xFFFFFFFF)], 3, 12)
        rows = read_dbc(self.path, 'nii')
        self.assertEqual(set(rows), {1000, 1001})
        self.assertEqual(uint(rows[1001], 1), 1761)
        with self.assertRaisesRegex(ValueError, 'overflows'):
            read_dbc(self.path, 'xin')

    def test_game_table_uses_implicit_ids(self):
        self.write([struct.pack('<f', 0.5), struct.pack('<f', 0.75)], 1, 4)
        self.assertEqual(set(read_dbc(self.path, 'df')), {0, 1})

    def test_rejects_bad_strings_and_truncated_records(self):
        self.write([struct.pack('<II', 1, 2)], 2, 8)
        with self.assertRaisesRegex(ValueError, 'invalid string'):
            read_dbc(self.path, 'ns')
        self.path.write_bytes(self.path.read_bytes()[:-1])
        with self.assertRaisesRegex(ValueError, 'length'):
            read_dbc(self.path, 'ns')

    def test_continuation_wins_without_removing_base_only_rows(self):
        self.write([struct.pack('<II', 1, 10), struct.pack('<II', 2, 20)], 2, 8)
        rows = read_dbc(self.path, 'ni')
        self.write([struct.pack('<II', 2, 200), struct.pack('<II', 3, 30)], 2, 8)
        rows.update(read_dbc(self.path, 'ni'))
        self.assertEqual({key: uint(row, 1) for key, row in rows.items()}, {1: 10, 2: 200, 3: 30})


if __name__ == '__main__':
    unittest.main()
