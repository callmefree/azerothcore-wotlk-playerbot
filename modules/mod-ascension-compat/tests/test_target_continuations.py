"""Cross-check target repairs against exported conditions and bound native filters."""
from pathlib import Path
import re
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'modules/mod-ascension-compat/apps'))
import build_conditioned_target_continuation as conditioned
import build_scripted_target_continuation as scripted
from build_encounter_dbc_continuation import read_rows

DATA = ROOT / 'env/dist/bin/data'
LAYERS = DATA / 'dbc-continuations'


class TargetContinuations(unittest.TestCase):
    def test_only_reviewed_target_fields_change(self):
        for builder in (conditioned, scripted):
            stock = read_rows(DATA / 'dbc/Spell.dbc', builder.IDS)
            before = read_rows(LAYERS / 'Spell.dbc1-ascension', builder.IDS)
            after = read_rows(LAYERS / builder.NAME, builder.IDS)
            self.assertEqual(set(after), builder.IDS)
            count = struct.unpack_from('<I', (LAYERS / builder.NAME).read_bytes(), 4)[0]
            self.assertEqual(count, len(builder.IDS))
            for spell in builder.IDS:
                changed = {i for i, pair in enumerate(zip(before[spell], after[spell])) if pair[0] != pair[1]}
                if builder is conditioned:
                    self.assertEqual(changed, {86}, spell)
                    self.assertEqual(after[spell][86], 38)
                else:
                    self.assertTrue(changed and changed <= set(range(86, 95)), spell)
                    self.assertEqual(after[spell][86:95], stock[spell][86:95], spell)
            # No later patch may silently undo these rows.
            for layer in LAYERS.glob('Spell.dbc*'):
                if layer.name > builder.NAME:
                    self.assertFalse(read_rows(layer, builder.IDS), layer.name)

    def test_nearby_targets_have_real_conditioned_creatures(self):
        source = (ROOT / '_CURRENT-DATABASE/acore_world/conditions.sql').read_text(encoding='utf-8')
        conditions = [tuple(map(int, match.split(','))) for match in
                      re.findall(r'^\s*\((13(?:,\s*-?\d+){12}),', source, re.M)]
        templates = (ROOT / '_CURRENT-DATABASE/acore_world/creature_template.sql').read_text(encoding='utf-8')
        entries = {int(value) for value in re.findall(r'^\s*\((\d+),', templates, re.M)}
        self.assertGreater(len(entries), 10000)
        for spell in conditioned.IDS:
            rows = [row for row in conditions if row[2] == spell]
            self.assertTrue(rows, spell)
            self.assertTrue(all(row[1] == 1 for row in rows), spell)
            creatures = [row for row in rows if row[5] == 31 and row[7] == 3 and row[10] == 0]
            self.assertTrue(creatures, spell)
            self.assertTrue(all(row[8] in entries for row in creatures), spell)
            # Every OR branch must constrain selection to an actual creature entry.
            self.assertEqual({row[4] for row in rows}, {row[4] for row in creatures}, spell)

    def test_encounter_bindings_and_area_filters(self):
        contracts = {
            'spell_class_call_handler': (
                'EasternKingdoms/BlackrockMountain/BlackwingLair/boss_nefarian.cpp',
                {23410, 23414, 23418, 23425, 23436}, 15, 'TARGET_UNIT_SRC_AREA_ENEMY'),
            'spell_dream_fog_sleep': ('World/boss_emerald_dragons.cpp', {24778}, 16,
                                     'TARGET_UNIT_DEST_AREA_ENEMY'),
            'spell_malchezaar_enfeeble': ('EasternKingdoms/Karazhan/boss_prince_malchezaar.cpp',
                                         {30843}, 15, 'TARGET_UNIT_SRC_AREA_ENEMY'),
            'spell_anetheron_sleep': ('Kalimdor/CavernsOfTime/BattleForMountHyjal/boss_anetheron.cpp',
                                      {31298}, 15, 'TARGET_UNIT_SRC_AREA_ENEMY'),
            'spell_ulduar_stone_grip_cast_target': ('Northrend/Ulduar/Ulduar/boss_kologarn.cpp',
                                                   {62166, 63981}, 15, 'TARGET_UNIT_SRC_AREA_ENEMY'),
        }
        bindings = (ROOT / '_CURRENT-DATABASE/acore_world/spell_script_names.sql').read_text()
        rows = read_rows(LAYERS / scripted.NAME, scripted.IDS)
        for name, (file, spells, target, constant) in contracts.items():
            source = (ROOT / 'src/server/scripts' / file).read_text()
            body = source.split('class ' + name + ' ', 1)[1].split('\n};', 1)[0]
            self.assertRegex(body, r'OnObjectAreaTargetSelect.*' + constant)
            for spell in spells:
                self.assertIn(f"({spell}, '{name}')", bindings)
                for effect in range(3):
                    if rows[spell][71 + effect]:
                        self.assertEqual(rows[spell][89 + effect], target)
                        self.assertGreater(rows[spell][92 + effect], 0)


if __name__ == '__main__':
    unittest.main()
