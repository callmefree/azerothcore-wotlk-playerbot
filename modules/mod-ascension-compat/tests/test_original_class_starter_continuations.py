"""Check automatic starter grants against the bot factory and exported starting skills."""
from pathlib import Path
import re
import struct
import unittest

ROOT = Path(__file__).resolve().parents[3]
DIRECTORY = ROOT / 'env/dist/bin/data/dbc-continuations'


def rows(name, fields):
    data = (DIRECTORY / name).read_bytes()
    magic, count, width, size, strings = struct.unpack_from('<4s4I', data)
    assert (magic, width, size, strings) == (b'WDBC', fields, fields * 4, 1)
    assert len(data) == 20 + count * size + 1 and data[-1] == 0
    return [struct.unpack_from(f'<{fields}I', data, offset) for offset in range(20, 20 + count * size, size)]


class OriginalClassStarters(unittest.TestCase):
    def test_grants_match_factory_and_starting_skills(self):
        abilities = rows('SkillLineAbility.dbc2-original-class-starters', 14)
        permissions = rows('SkillRaceClassInfo.dbc4-original-class-starters', 8)
        factory = (ROOT / 'modules/mod-playerbots/src/Bot/Factory/PlayerbotFactory.cpp').read_text()
        factory = factory.split('void PlayerbotFactory::InitClassSpells()', 1)[1]
        skills = (ROOT / '_CURRENT-DATABASE/acore_world/playercreateinfo_skills.sql').read_text()
        classes = {1: 'WARRIOR', 2: 'PALADIN', 3: 'HUNTER', 4: 'ROGUE', 5: 'PRIEST',
                   7: 'SHAMAN', 8: 'MAGE', 9: 'WARLOCK', 11: 'DRUID'}
        self.assertEqual(len(abilities), 18)
        self.assertEqual(len(permissions), 9)
        for _, skill, race_mask, class_mask, flags, level, tier, cost in permissions:
            cls = class_mask.bit_length()
            self.assertIn(cls, classes)
            self.assertEqual(class_mask, 1 << (cls - 1))
            self.assertEqual((race_mask, flags, level, tier, cost), (0xffffffff, 1040, 0, 0, 0))
            self.assertRegex(skills, rf'\(0, {class_mask}, {skill}, 0,')
            block = factory.split('case CLASS_' + classes[cls] + ':', 1)[1].split('break;', 1)[0]
            grants = [row for row in abilities if row[1] == skill and row[4] == class_mask]
            self.assertEqual(len(grants), 2)
            for row in grants:
                self.assertRegex(block, rf'bot->learnSpell\({row[2]}, true\)')
                self.assertEqual((row[3], row[7], row[8], row[9]), (0, 1, 0, 2))

    def test_existing_warlock_skill_recovers_shadow_bolt_without_custom_class_grant(self):
        abilities = rows('SkillLineAbility.dbc2-original-class-starters', 14)
        permissions = rows('SkillRaceClassInfo.dbc4-original-class-starters', 8)
        # Native _LoadSkills calls learnSkillRewardedSpells for saved skills; class 9
        # also receives skill 354 from LearnDefaultSkills if it was previously removed.
        accessible = {r[1] for r in permissions if r[2] & 2 and r[3] & 256}
        learned = {r[2] for r in abilities if r[1] in accessible and r[4] & 256 and r[9] == 2}
        self.assertEqual(learned, {686, 687})
        for cls in (10, *range(12, 33)):
            self.assertFalse(any(r[4] & (1 << (cls - 1)) for r in abilities))


if __name__ == '__main__':
    unittest.main()
