"""Verify instruction operands, the reported overflow, and guarded installation."""
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import capstone
from capstone.x86_const import X86_OP_MEM, X86_REG_EBP
import pefile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'apps'))
import patch_client_default_class_buffer as fix


class DefaultClassBuffer(unittest.TestCase):
    def test_reported_frame_overwrite_and_new_capacity(self):
        # Disassemble actual old/new instructions, then model their DWORD stores.
        md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
        md.detail = True
        for code, allocation in ((fix.ORIGINAL, 120), (fix.corrected_function(), 128)):
            instructions = list(md.disasm(code, 0x4E0F50))
            self.assertEqual(sum(i.size for i in instructions), len(code))
            reserve = instructions[2]
            signed_allocation = reserve.operands[1].imm
            self.assertEqual(-signed_allocation if reserve.mnemonic == 'add' else signed_allocation, allocation)
            indexed = [op.mem for i in instructions for op in i.operands
                       if op.type == X86_OP_MEM and op.mem.base == X86_REG_EBP and op.mem.index]
            self.assertEqual(len(indexed), 3)
            self.assertTrue(all(m.disp == -allocation and m.scale == 4 for m in indexed))
            stack = bytearray(160)
            frame = 128
            sentinel = 0x0454F930
            struct.pack_into('<I', stack, frame, sentinel)
            for index in range(31):
                value = 32 if index == 30 else index + 1
                struct.pack_into('<I', stack, frame + indexed[0].disp + index * 4, value)
            saved_frame = struct.unpack_from('<I', stack, frame)[0]
            self.assertEqual(saved_frame, 32 if allocation == 120 else sentinel)
            if allocation == 128:
                for count in range(1, 33):
                    self.assertLess(indexed[0].disp + (count - 1) * 4, 0)
            else:
                self.assertEqual((saved_frame - 0x170) & 0xFFFFFFFF, 0xFFFFFEB0)

    def test_preserves_other_bytes_and_rejects_unknown_function(self):
        image = Path('F:/Ascension-client/Ascension.exe').read_bytes()
        pe = pefile.PE(data=image, fast_load=True)
        offset = pe.get_offset_from_rva(fix.RVA)
        original = image[:offset] + fix.ORIGINAL + image[offset + len(fix.ORIGINAL):]
        after = fix.patch_image(original)
        self.assertEqual(len(original), len(after))
        self.assertEqual(sum(a != b for a, b in zip(original, after)), 5)
        self.assertEqual(original[:offset], after[:offset])
        self.assertEqual(original[offset + len(fix.ORIGINAL):], after[offset + len(fix.ORIGINAL):])
        self.assertEqual(fix.patch_image(after), after)
        broken = bytearray(original)
        broken[offset] ^= 1
        with self.assertRaises(ValueError):
            fix.patch_image(bytes(broken))

    def test_install_guards_and_backup(self):
        image = Path('F:/Ascension-client/Ascension.exe').read_bytes()
        offset = pefile.PE(data=image, fast_load=True).get_offset_from_rva(fix.RVA)
        before = image[:offset] + fix.ORIGINAL + image[offset + len(fix.ORIGINAL):]
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / 'Ascension.exe'
            backup = exe.with_name(exe.name + '.pre-default-class-buffer')
            exe.write_bytes(before)
            running = subprocess.CompletedProcess([], 0, '"Ascension.exe","123"', '')
            with patch.object(fix.subprocess, 'run', return_value=running):
                with self.assertRaisesRegex(RuntimeError, 'Close Ascension'):
                    fix.install(exe)
            self.assertEqual(exe.read_bytes(), before)
            self.assertFalse(backup.exists())
            stopped = subprocess.CompletedProcess([], 0, 'No tasks', '')
            with patch.object(fix.subprocess, 'run', return_value=stopped):
                backup.write_bytes(b'unrelated backup')
                with self.assertRaisesRegex(RuntimeError, 'Existing backup differs'):
                    fix.install(exe)
                self.assertEqual(exe.read_bytes(), before)
                backup.write_bytes(before)
                fix.install(exe)
                fix.install(exe)
            self.assertEqual(backup.read_bytes(), before)
            self.assertEqual(exe.read_bytes(), fix.patch_image(before))


if __name__ == '__main__':
    unittest.main()
