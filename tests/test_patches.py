from paths import ROOT
import os
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from patches import (compile_patches, external_patches, external_selection, compile_external,
                     game_profile, selected_patches, patch_requirements, GAMES, merge_patch_files,
                     resolution_names, default_enabled)

SYNTHETIC_BASE = ROOT / 'patches/CUSA99998.xml'
ULTRAWIDE = ROOT / 'extras/mods/Ultrawide/patches/Ultrawide.xml'
RATCHET_IDS = {'CUSA99998'}
SEGMENTS = [(0, 0x6000000)]


EXTERNAL = """<?xml version="1.0"?>
<Patch>
  <TitleID><ID>CUSA99998</ID></TitleID>
  <Metadata Title="RatchetPort" Name="On" Author="x" PatchVer="1.0" AppVer="01.02" AppElf="eboot.bin" isEnabled="true">
    <PatchList><Line Type="bytes" Address="0x00401000" Value="9090"/></PatchList>
  </Metadata>
  <Metadata Title="RatchetPort" Name="Off" Author="x" PatchVer="1.0" AppVer="01.02" AppElf="eboot.bin">
    <PatchList><Line Type="bytes32" Address="0x00402000" Value="0x12345678"/></PatchList>
  </Metadata>
  <Metadata Title="RatchetPort" Name="Mask" Author="x" PatchVer="1.0" AppVer="01.02" AppElf="eboot.bin" isEnabled="true">
    <PatchList><Line Type="mask" Value="90 ?? 90" Offset="0"/></PatchList>
  </Metadata>
  <Metadata Title="RatchetPort" Name="Old" Author="x" PatchVer="1.0" AppVer="01.00" AppElf="eboot.bin" isEnabled="true">
    <PatchList><Line Type="bytes" Address="0x00403000" Value="90"/></PatchList>
  </Metadata>
</Patch>"""


class ExternalPatchTests(unittest.TestCase):
    def test_selection_and_unsupported_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'extra.xml').write_text(EXTERNAL)
            (folder / 'other.xml').write_text(EXTERNAL.replace('CUSA99998', 'CUSA99999'))
            (folder / 'broken.xml').write_text('<Patch>')
            found = external_patches(folder, '01.02', SYNTHETIC_BASE, RATCHET_IDS)
            self.assertEqual([key for key, _, _ in found],
                             ['extra.xml/On', 'extra.xml/Off', 'extra.xml/Mask'])
            # The file's isEnabled; the mask patch is skipped as a whole.
            writes = compile_external(external_selection(found, None), SEGMENTS)
            self.assertEqual(writes, [(0x1000, bytes.fromhex('9090'))])
            config = folder / 'patches.json'
            config.write_text('{"enabled": ["extra.xml/Off"], "disabled": ["extra.xml/On"]}')
            writes = compile_external(external_selection(found, config), SEGMENTS)
            self.assertEqual(writes, [(0x2000, (0x12345678).to_bytes(4, 'little'))])

    def test_built_in_file_is_not_external(self):
        self.assertEqual(external_patches(SYNTHETIC_BASE.parent, '01.02', SYNTHETIC_BASE, RATCHET_IDS), [])


class GameProfileTests(unittest.TestCase):

    def test_unavailable_frame_rate_patch_falls_back_to_the_highest_lower_one(self):
        from graphics_options import restrict_to_available
        available = {'Bug Fix - Texture Corruption Fix', 'Frame Rate Patch - 120 FPS'}
        self.assertEqual(restrict_to_available(['Bug Fix - Texture Corruption Fix', 'Frame Rate Patch - 240 FPS'],
                                               available),
                         ['Bug Fix - Texture Corruption Fix', 'Frame Rate Patch - 120 FPS'])
        self.assertEqual(restrict_to_available(['Resolution Patch - 8K'], available), [])





class SignatureTests(unittest.TestCase):
    XML = """<?xml version="1.0"?>
<Patch>
  <Metadata Name="Found" AppVer="01.02">
    <PatchList><Line Type="bytes" Address="0x401004" Value="9090" Pattern="11 22 ?? 44 55 66" At="1"/></PatchList>
  </Metadata>
  <Metadata Name="Call" AppVer="01.02">
    <PatchList><Line Type="bytes" Address="0x401010" Value="e8{rel:there:0}" Pattern="aa bb cc dd ee" At="0"/></PatchList>
    <Target Name="there" Address="0x401100" Pattern="e9 ?? ?? ?? ?? 77 88" At="1" Ref="1"/>
  </Metadata>
  <Metadata Name="Missing" AppVer="01.02">
    <PatchList>
      <Line Type="bytes" Address="0x401004" Value="9090" Pattern="11 22 ?? 44 55 66" At="1"/>
      <Line Type="bytes" Address="0x401020" Value="90" Pattern="de ad be ef" At="0"/>
    </PatchList>
  </Metadata>
  <Metadata Name="Data" AppVer="01.02">
    <PatchList><Line Type="bytes32" Address="0x402000" Target="variable" Value="0x2"/></PatchList>
    <Target Name="variable" Address="0x402000" Pattern="44 89 35 ?? ?? ?? ?? c6" At="3" Ref="1"/>
  </Metadata>
</Patch>"""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.xml = Path(directory.name) / 'test.xml'
        self.xml.write_text(self.XML)
        image = bytearray(0x400)
        image[0x40:0x46] = bytes.fromhex('112233445566')
        image[0x80:0x85] = bytes.fromhex('aabbccddee')
        image[0x200:0x207] = bytes.fromhex('e9') + (0x300 - 0x205).to_bytes(4, 'little', signed=True) + bytes.fromhex('7788')
        # mov [rip+disp], r14d storing to 0x3f0, then the c6 of the next instruction.
        image[0x280:0x288] = bytes.fromhex('448935') + (0x3f0 - 0x287).to_bytes(4, 'little', signed=True) + b'\xc6'
        self.image = bytes(image)

    def test_sites_found_anywhere_and_rel32_recomputed(self):
        skipped = {}
        writes = compile_patches(self.xml, ['Found', 'Call', 'Missing'], None, [(0, 0x400)], self.image, skipped)
        call = (0x300 - (0x80 + 5)).to_bytes(4, 'little', signed=True)
        self.assertEqual(writes, [(0x41, b'\x90\x90'), (0x80, b'\xe8' + call)])
        # One site of the patch is missing: the whole patch is left out, with the reason.
        self.assertEqual(skipped, {'Missing': 'signature not found'})

    def test_ambiguous_signature_is_skipped(self):
        image = bytearray(self.image)
        image[0x100:0x106] = image[0x40:0x46]
        skipped = {}
        self.assertEqual(compile_patches(self.xml, ['Found'], None, [(0, 0x400)], bytes(image), skipped), [])
        self.assertEqual(skipped, {'Found': 'signature found more than once'})

    def test_without_the_image_the_reference_addresses_are_used(self):
        writes = compile_patches(self.xml, ['Found', 'Call'], '01.02', [(0, 0x10000)])
        self.assertEqual(writes[0], (0x1004, b'\x90\x90'))
        self.assertEqual(writes[1][0], 0x1010)

    def test_data_line_writes_at_its_target(self):
        # The variable has no bytes of its own to find: the code that stores to it points at it.
        self.assertEqual(compile_patches(self.xml, ['Data'], None, [(0, 0x400)], self.image, {}),
                         [(0x3f0, (2).to_bytes(4, 'little'))])
        self.assertEqual(compile_patches(self.xml, ['Data'], '01.02', [(0, 0x10000)]),
                         [(0x2000, (2).to_bytes(4, 'little'))])
        image = bytearray(self.image)
        image[0x280:0x288] = bytes(8)  # store not found: the whole patch is left out
        skipped = {}
        self.assertEqual(compile_patches(self.xml, ['Data'], None, [(0, 0x400)], bytes(image), skipped), [])
        self.assertEqual(skipped, {'Data': 'signature not found'})











class ModPatchTests(unittest.TestCase):
    MOD = """<?xml version="1.0"?>
<Patch>
  <TitleID><ID>CUSA99998</ID></TitleID>
  <Metadata Name="Resolution Patch - 3440x1440" Note="Requires setting DMEM to 4608 MB or more." AppVer="01.02" AppElf="eboot.bin" isEnabled="false">
    <PatchList><Line Type="bytes" Address="0x00401000" Value="9090"/></PatchList>
  </Metadata>
  <Metadata Name="Resolution Patch - 2560x1080" AppVer="01.02" AppElf="eboot.bin" isEnabled="false">
    <PatchList><Line Type="bytes" Address="0x00401000" Value="9090"/></PatchList>
  </Metadata>
  <Metadata Name="Skip Any Video With X Button" Note="replaced by the mod" AppVer="01.02" AppElf="eboot.bin" isEnabled="true">
    <PatchList><Line Type="bytes" Address="0x00401002" Value="90"/></PatchList>
  </Metadata>
</Patch>"""
    OTHER_GAME = '<Patch><TitleID><ID>CUSA99999</ID></TitleID><Metadata Name="Elsewhere" AppVer="01.02"><PatchList/></Metadata></Patch>'

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.dir = Path(directory.name)
        self.mod = self.dir / 'mod.xml'
        self.mod.write_text(self.MOD)
        self.base = self.dir / 'base.xml'
        self.base.write_text(EXTERNAL.replace('Name="Off"', 'Name="Skip Any Video With X Button"'))

    def test_resolution_names_of_patch_files_smallest_first(self):
        self.assertEqual(resolution_names([self.mod]), ['2560x1080', '3440x1440'])
        self.assertEqual(resolution_names([self.dir / 'missing.xml']), [])

    def test_merge_adds_replaces_and_skips_other_titles(self):
        other = self.dir / 'other.xml'
        other.write_text(self.OTHER_GAME)
        merged = merge_patch_files(self.base, [self.mod, other], self.dir / 'out' / 'merged.xml')
        names = [m.get('Name') for m in ET.parse(merged).getroot().iter('Metadata')]
        self.assertIn('Resolution Patch - 3440x1440', names)
        self.assertNotIn('Elsewhere', names)
        self.assertEqual(names.count('Skip Any Video With X Button'), 1)  # replaced, not repeated
        note = next(m.get('Note') for m in ET.parse(merged).getroot().iter('Metadata')
                    if m.get('Name') == 'Skip Any Video With X Button')
        self.assertEqual(note, 'replaced by the mod')
        # The built-in patches are all still there, and the merged file is selectable like the original.
        self.assertTrue(set(m.get('Name') for m in ET.parse(self.base).getroot().iter('Metadata')) - {'Skip Any Video With X Button'} <= set(names))
        chosen = selected_patches(merged, '01.02', 'Resolution Patch - 3440x1440', only=True)
        self.assertIn('Resolution Patch - 3440x1440', chosen)  # (the startup fix is always added)
        self.assertNotIn('Resolution Patch - 2560x1080', chosen)
        self.assertEqual(patch_requirements(merged, ['Resolution Patch - 3440x1440'], '01.02'), (5056 + 4608, None))

    def test_a_broken_mod_file_is_left_out(self):
        broken = self.dir / 'broken.xml'
        broken.write_text('<Patch><Metadata')
        merged = merge_patch_files(self.base, [broken, self.mod], self.dir / 'merged.xml')
        self.assertIn('Resolution Patch - 2560x1080',
                      [m.get('Name') for m in ET.parse(merged).getroot().iter('Metadata')])

    def test_default_enabled_patches_of_a_mod(self):
        self.assertEqual(default_enabled([self.mod], '01.02'), ['Skip Any Video With X Button'])
        self.assertEqual(default_enabled([self.mod], '01.00'), [])

    # --- the Ultrawide mod (extras/mods/Ultrawide): ULTRAWIDE sizes -> (extra direct memory MiB, k)
    SIZES = {
        (2560, 1080): (3072, (2560 / 1080) / (16 / 9)),
        (3440, 1440): (4608, (3440 / 1440) / (16 / 9)),
        (3840, 1600): (6144, (3840 / 1600) / (16 / 9)),
        (5120, 1440): (6144, 2.0),
        (5120, 2160): (6144, (5120 / 2160) / (16 / 9)),
    }

    # 16:10, taller than 16:9: only the resolution and the aspect ratio (the camera's fixed horizontal view
    # already shows more at the top and bottom), so no field of view change.
    TALLER = {(1920, 1200): 3072, (2560, 1600): 4608, (1280, 800): 3072,
              (1440, 900): 3072, (1360, 768): 3072,
              (1280, 960): 3072, (1440, 1080): 3072, (1920, 1440): 3072, (2048, 1536): 3072, (2560, 1920): 4608}








if __name__ == '__main__':
    unittest.main()
