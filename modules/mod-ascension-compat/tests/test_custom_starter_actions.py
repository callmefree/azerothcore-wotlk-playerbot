"""Check starter data and permission dependencies; native login still needs acceptance."""
from pathlib import Path
import re
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / 'env/dist/bin/data'
sys.path.insert(0, str(ROOT / 'modules/mod-ascension-compat/apps'))
from build_encounter_dbc_continuation import read_rows


class CustomStarterActions(unittest.TestCase):
    def test_thrown_permission_matches_existing_baseline_grants(self):
        header = (ROOT / 'modules/mod-ascension-compat/src/AscensionLiveBaselineData.h').read_text()
        spells = header.split('Spells =', 1)[1].split('}};', 1)[0]
        classes = {int(c) for c in re.findall(r'\{(\d+), 0, 2764\}', spells)}
        name = 'SkillRaceClassInfo.dbc5-custom-class-thrown'
        before = {}
        for file in [DATA / 'dbc/SkillRaceClassInfo.dbc', *sorted((DATA / 'dbc-continuations').glob('SkillRaceClassInfo.dbc*'))]:
            if file.name == name:
                continue
            data = file.read_bytes()
            count = struct.unpack_from('<I', data, 4)[0]
            for row in struct.iter_unpack('<8I', data[20:20 + count * 32]):
                before[row[0]] = row
        patch = (DATA / 'dbc-continuations' / name).read_bytes()
        self.assertEqual(struct.unpack_from('<4s4I', patch), (b'WDBC', 1, 8, 32, 1))
        self.assertEqual(len(patch), 53)
        row = struct.unpack_from('<8I', patch, 20)
        self.assertNotIn(row[0], before)
        sql = (ROOT / '_CURRENT-DATABASE/acore_world/skillraceclassinfo_dbc.sql').read_text()
        self.assertNotRegex(sql, rf'^\s*\({row[0]},')
        missing = {c for c in classes if not any(r[1] == 176 and r[2] == 0xffffffff and
                   r[3] & (1 << (c - 1)) for r in before.values())}
        self.assertEqual(row, (981, 176, 0xffffffff, sum(1 << (c - 1) for c in missing), 128, 0, 0, 0))
        self.assertIn(14, missing)
        self.assertNotIn(13, missing)  # Its earlier continuation remains authoritative.
        self.assertTrue(all(c >= 12 for c in missing))
        # Darnassian's native race gate must remain Night Elf only.
        self.assertEqual([r[2] for r in before.values() if r[1] == 113], [8])

    def test_starter_catalog_has_active_abilities_for_every_custom_class(self):
        source = (ROOT / 'modules/mod-ascension-compat/src/AscensionCustomClassData.h').read_text()
        block = source.split('ClassSpells =', 1)[1].split('}};', 1)[0]
        starters = [(int(c), int(s)) for c, s in re.findall(r'\{(\d+), 1, (\d+)\}', block)]
        ids = {s for _, s in starters}
        spells = read_rows(DATA / 'dbc/Spell.dbc', ids)
        for path in sorted((DATA / 'dbc-continuations').glob('Spell.dbc*')):
            if path.is_file():
                spells.update(read_rows(path, ids))
        self.assertEqual(set(spells), ids)
        for cls in range(12, 33):
            # Exclude passive grants and generic attacks/profession training.
            active = {s for c, s in starters if c == cls and not spells[s][4] & 64
                      and s not in {6603, 2764, 3018, 5019, 8613}}
            self.assertTrue(active, cls)
            self.assertLessEqual(len(active) + 1, 12, cls)
            if cls == 14:
                self.assertEqual(active, {801901, 802060})
                self.assertEqual({spells[s][136] for s in active}, {b'Twin Slice', b'Sargeron Smite'})


if __name__ == '__main__':
    unittest.main()
