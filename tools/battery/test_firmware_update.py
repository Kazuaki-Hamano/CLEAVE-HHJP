import tempfile
from pathlib import Path
import struct
import unittest
from unittest.mock import Mock, patch
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
        self.drive = updater.BootDrive(self.temp.name, 1, 'nRF52840-Seeed_XIAO_nRF52840')

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

    def test_copy_uses_validated_snapshot(self):
        self.path.write_bytes(b'changed source')
        updater.copy_firmware(self.firmware, self.drive, lambda text: None, scan=lambda: {self.drive})
        self.assertEqual((Path(self.temp.name) / 'CLEAVE.UF2').read_bytes(), self.firmware.data)

    def test_existing_or_changed_drive_prevents_writes(self):
        boot = Mock()
        copy = Mock()
        with self.assertRaises(RuntimeError):
            updater.perform_update(self.firmware, False, lambda text: None,
                scan=lambda: {self.drive}, boot=boot, copier=copy)
        boot.assert_not_called()
        copy.assert_not_called()
        with self.assertRaises(RuntimeError):
            updater.copy_firmware(self.firmware, self.drive, lambda text: None, scan=lambda: set())

    def test_multiple_new_drives_prevent_selection(self):
        other = updater.BootDrive('X:\\', 2, self.drive.board)
        with self.assertRaises(RuntimeError):
            updater.wait_boot_drive(set(), scan=lambda: {self.drive, other}, timeout=0.1)

    def run_simulation(self, build):
        phase = {'value': 0}
        current = {'side': 0, 'build': build, 'uid': '1234'}
        def boot(side):
            phase['value'] = 1
            return {'uid': '1234'}
        def scan():
            return {self.drive} if phase['value'] == 1 else set()
        def copy(*args, **kwargs):
            phase['value'] = 2
        return updater.perform_update(self.firmware, False, lambda text: None,
            scan=scan, boot=boot, info=lambda side: current, copier=copy,
            drive_timeout=0.1, verify_timeout=0.01)

    def test_reconnect_with_expected_build_required(self):
        self.assertTrue(self.run_simulation('abcdef12')['verified'])
        self.assertFalse(self.run_simulation('wrongold')['verified'])

    def test_boot_command_is_explicit_and_padded(self):
        dev = Mock()
        dev.send_feature_report.return_value = 32
        with patch.object(updater, 'read_info', return_value={'usb': True}), \
             patch.object(updater, 'device', return_value=dev):
            updater.request_boot(1)
        dev.send_feature_report.assert_called_once_with(bytes([4, 1, 1]) + b'BOOT' + bytes(25))
        dev.close.assert_called_once()

    def test_no_usb_power_prevents_boot(self):
        with patch.object(updater, 'read_info', return_value={'usb': False}), \
             patch.object(updater, 'device') as device:
            with self.assertRaises(RuntimeError):
                updater.request_boot(1)
        device.assert_not_called()


if __name__ == '__main__':
    unittest.main()
