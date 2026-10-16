import unittest
from battery_diagnostics import decode_diagnostics


class DiagnosticReportTests(unittest.TestCase):
    def test_valid_voltage_and_independent_sensor_percent(self):
        data = bytes([6, 1, 84, 2]) + (3735).to_bytes(2, 'little') + bytes([39, 3]) + (321).to_bytes(4, 'little') + (7).to_bytes(4, 'little')
        result = decode_diagnostics(data)
        self.assertEqual(result['firmware_percent'], 84)
        self.assertEqual(result['sensor_percent'], 39)
        self.assertEqual(result['voltage_mv'], 3735)
        self.assertEqual(result['uptime_seconds'], 321)
        self.assertEqual(result['percent_change_age_seconds'], 7)

    def test_missing_values_are_unknown_not_zero(self):
        data = bytes([6, 1, 0, 0, 0, 0, 0, 0]) + bytes(4) + bytes([255] * 4)
        result = decode_diagnostics(data)
        self.assertIsNone(result['voltage_mv'])
        self.assertIsNone(result['sensor_percent'])
        self.assertIsNone(result['percent_change_age_seconds'])

    def test_malformed_data_rejected(self):
        for data in (bytes(16), bytes([6, 1, 101, 2]) + bytes(12),
                     bytes([6, 1, 40, 2, 0, 0, 101, 2]) + bytes(8),
                     bytes([6, 1, 40, 2, 0, 0, 40, 4]) + bytes(8)):
            with self.assertRaises(ValueError):
                decode_diagnostics(data)
