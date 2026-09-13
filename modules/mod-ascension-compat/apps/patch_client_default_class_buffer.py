"""Fix the build-12340 default-class picker overflow without removing available classes.

The client selects from a 30-DWORD stack array at 004E0F50. patch-T's Troll list
has 31 entries, ending in class 32; its 31st write corrupts the saved EBP with 32.
ResetCharCustomize subsequently writes through that EBP and crashes at 004E204F.
Reserve 32 DWORDs and move all three indexed accesses together. No control-flow,
class filtering, random selection, or unrelated executable bytes change.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess

import pefile

RVA = 0xE0F50
ORIGINAL = bytes.fromhex(
    '558bec83ec78565733f6e811fa1c000fb6b82d2f00008b15a8b1b60033c085d2762c'
    '3bc2538b1dacb1b600720433c9eb038b0c833b792c7c098b09894cb58883c60183c001'
    '3bc272e885f65b7f0c33c08b4485885f5e8be55dc36830fab200e8cc35f8fff7e683'
    'c404b120e8f03df3ff8b4485885f5e8be55dc3')


def corrected_function():
    code = bytearray(ORIGINAL)
    # ADD ESP, -128: SUB ESP, imm8 cannot encode positive 128 (signed immediate).
    code[3:6] = bytes.fromhex('83c480')
    for offset, instruction in ((0x3B, '894cb588'), (0x50, '8b448588'), (0x70, '8b448588')):
        assert code[offset:offset + 4] == bytes.fromhex(instruction)
        code[offset + 3] = 0x80  # [EBP + index*4 - 128]
    return bytes(code)


def patch_image(image):
    pe = pefile.PE(data=image, fast_load=True)
    if pe.FILE_HEADER.Machine != 0x14C or pe.OPTIONAL_HEADER.ImageBase != 0x400000:
        raise ValueError('Unexpected client executable format')
    offset = pe.get_offset_from_rva(RVA)
    old = image[offset:offset + len(ORIGINAL)]
    new = corrected_function()
    if old == new:
        return image
    if old != ORIGINAL:
        raise ValueError('Default-class function does not match the inspected client; refusing to patch')
    return image[:offset] + new + image[offset + len(ORIGINAL):]


def install(path):
    path = path.resolve(strict=True)
    before = path.read_bytes()
    after = patch_image(before)
    if before == after:
        print('Already patched; no changes')
        return
    # A conservative name guard also avoids replacing any running client variant.
    result = subprocess.run(
        ['tasklist', '/FI', 'IMAGENAME eq Ascension.exe', '/FO', 'CSV', '/NH'],
        capture_output=True, text=True, check=True)
    if 'ascension.exe' in result.stdout.lower():
        raise RuntimeError('Close Ascension.exe before installing this executable patch')
    backup = path.with_name(path.name + '.pre-default-class-buffer')
    if backup.exists():
        if backup.read_bytes() != before:
            raise RuntimeError('Existing backup differs; preserve it and review before installing')
    else:
        with backup.open('xb') as stream:
            stream.write(before)
    if backup.read_bytes() != before or path.read_bytes() != before:
        raise RuntimeError('Backup verification failed or executable changed during preparation')
    path.write_bytes(after)
    if path.read_bytes() != after:
        raise RuntimeError('Installed executable verification failed; original remains in backup')
    print(f'Patched {path}; changed {sum(a != b for a, b in zip(before, after))} bytes')
    print(f'Backup: {backup}')
    print(f'SHA256: {hashlib.sha256(after).hexdigest()}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executable', type=Path)
    args = parser.parse_args()
    install(args.executable)
