import unittest
from unittest.mock import patch
import battery_monitor as monitor


class ChargingReportTests(unittest.TestCase):
    def test_independent_states_and_age(self):
        state = monitor.decode_power([2, 1, 3, 1, 5, 0])
        self.assertEqual(state['left_power'], 'charging')
        self.assertEqual(state['right_power'], 'battery')
        self.assertEqual(state['right_power_age_seconds'], 5)

    def test_unknown_peer_does_not_imply_zero_or_full(self):
        state = monitor.decode_power([2, 1, 2, 0, 255, 255])
        self.assertEqual(state['left_power'], 'usb_idle')
        self.assertIsNone(state['right_power'])
        self.assertIsNone(state['right_power_age_seconds'])

    def test_bad_version_and_state_rejected(self):
        for report in ([2, 2, 1, 1, 0, 0], [2, 1, 4, 1, 0, 0], [2, 1, 1]):
            with self.assertRaises(ValueError):
                monitor.decode_power(report)

    def test_old_firmware_keeps_real_battery_levels(self):
        class OldDevice:
            def open_path(self, path): pass
            def close(self): pass
            def get_feature_report(self, report_id, size):
                if report_id == 2:
                    raise OSError('Unsupported report')
                return [1, 1, 71, 0, 1, 10, 0]
        with patch.object(monitor.hid, 'enumerate', return_value=[
            {'usage_page': 0xff60, 'usage': 1, 'path': b'keyboard'}]), \
             patch.object(monitor.hid, 'device', return_value=OldDevice()):
            state = monitor.read()
        self.assertEqual((state['left'], state['right']), (71, 0))
        self.assertIsNone(state['left_power'])
        self.assertIsNone(state['right_power'])

    def test_tooltip_uses_states_not_percentages(self):
        text = monitor.tooltip({'left': 100, 'right': 0,
                                'left_power': 'charging', 'right_power': 'usb_idle'})
        self.assertIn('左 100%（充電中）', text)
        self.assertIn('右 0%（USB給電）', text)
        self.assertNotIn('満充電', text)

    def test_windows_feature_report_padding(self):
        class Device:
            def open_path(self, path): pass
            def close(self): pass
            def get_feature_report(self, report_id, size):
                if size != 32:
                    raise OSError('Feature buffer too small')
                return [1, 1, 71, 55, 1, 10, 0] if report_id == 1 else [2, 1, 3, 2, 5, 0, 0]
        with patch.object(monitor.hid, 'enumerate', return_value=[
            {'usage_page': 0xff60, 'usage': 1, 'path': b'keyboard'}]), \
             patch.object(monitor.hid, 'device', return_value=Device()):
            state = monitor.read()
        self.assertEqual(state['left_power'], 'charging')
        self.assertEqual(state['right_power'], 'usb_idle')


if __name__ == '__main__':
    unittest.main()
