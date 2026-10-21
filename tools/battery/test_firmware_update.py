import tempfile
from pathlib import Path
import struct
import unittest
import firmware_update as updater


def uf2(side='LEFT', flags=0x2000, address=0x27000, family=0xada52840):
    result = bytearray()
    for index in range(2):
        marker = f'CLEAVE_HHJP_UPDATE1|{side}|abcdef12\0'.encode() if index == 0 else b''
        payload = marker.ljust(256, b'\0')
        result += struct.pack('<8I', 0x0a324655, 0x9e5d5157, flags,
                              address + 256*index, 256, index, 2, family)
        result += payload + bytes(220) + struct.pack('<I', 0x0ab16f30)
    return bytes(result)


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'firmware.uf2'
        self.path.write_bytes(uf2())
        self.firmware = updater.validate_firmware(self.path, 0)

    def test_wrong_side_rejected_without_filename_guessing(self):
        self.assertEqual(self.firmware.side, 0)
        with self.assertRaises(ValueError):
            updater.validate_firmware(self.path, 1)

    def test_foreign_family_and_protected_flash_rejected(self):
        for image in (uf2(address=0x0), uf2(address=0xec000), uf2(family=123), uf2(flags=0x2001)):
            self.path.write_bytes(image)
            with self.assertRaises(ValueError):
                updater.validate_firmware(self.path, 0)

    def test_missing_duplicate_or_unmarked_blocks_rejected(self):
        data = uf2()
        for image in (data[:512], data[:512] * 2, data.replace(b'CLEAVE_HHJP_UPDATE1', b'XXXXXXXXXXXXXXXXXXX')):
            self.path.write_bytes(image)
            with self.assertRaises(ValueError):
                updater.validate_firmware(self.path, 0)


if __name__ == '__main__': unittest.main()
