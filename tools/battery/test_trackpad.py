import unittest
from unittest.mock import patch
import struct
import trackpad_settings as tp


def response(config=tp.Config(), flags=2, applied=1, save_error=0):
    data = bytearray(tp.encode(config))
    data[2] = flags
    data[11] = applied
    data[13] = save_error & 255
    return bytes(data)


class TrackpadProtocolTests(unittest.TestCase):
    def test_submission_and_response_wait_are_distinct(self):
        status = tp.decode(response(flags=1, applied=0))
        status['transport'] = {'stage': 2}
        self.assertIn('送信処理', tp.pending_message(status))
        status['transport'] = {'stage': 7}
        self.assertIn('送信済み', tp.pending_message(status))

    def test_transport_diagnostics_and_missing_characteristic(self):
        data = bytearray(response(flags=1))
        data[16:23] = bytes([1, 4, 2, 10, 0, 0, 0])
        struct.pack_into('<HH', data, 24, 17, 17)
        status = tp.decode(data)
        self.assertEqual(status['transport']['attempts'], 17)
        self.assertIn('右側のファームウェア更新', tp.pending_message(status))

    def test_old_firmware_error_is_not_endless_generic_wait(self):
        status = tp.decode(response(flags=1, applied=0))
        status['sensor_error'] = -128
        self.assertIn('取得できません', tp.pending_message(status))

    def test_transport_failure_and_security_wait_are_distinct(self):
        status = tp.decode(response(flags=1, applied=0))
        status['transport'] = {'stage': 1, 'security': 1}
        self.assertIn('暗号化', tp.pending_message(status))
        status['transport'] = {'stage': 3, 'submit_error': -12}
        self.assertIn('-12', tp.pending_message(status))

    def test_wire_offsets_and_padding(self):
        config = tp.Config(275, 80, 450, 3)
        data = tp.encode(config, save=True)
        self.assertEqual(data[:4], bytes([7, 1, 1, 0]))
        self.assertEqual(struct.unpack_from('<HHHB', data, 4), (275, 80, 450, 3))
        self.assertEqual(data[11:], bytes(21))
        self.assertEqual(tp.decode(response(config, applied=3))['config'], config)

    def test_invalid_values_rejected_before_io(self):
        for c in (tp.Config(0), tp.Config(801), tp.Config(acceleration=301),
                  tp.Config(maximum=99), tp.Config(sensitivity=0), tp.Config(sensitivity=5)):
            with self.assertRaises(ValueError): tp.encode(c)

    def test_old_or_corrupt_reports_rejected(self):
        for data in (bytes(32), bytes([7, 2])+bytes(30), response()[:16]):
            with self.assertRaises(ValueError): tp.decode(data)

    def test_status_does_not_confuse_requested_with_applied(self):
        s = tp.decode(response(tp.Config(sensitivity=4), flags=1, applied=2))
        self.assertFalse(s['applied'])
        self.assertTrue(s['dirty'])
        self.assertEqual(s['sensor_sensitivity'], 2)

    def test_unsupported_device_never_written_and_closed(self):
        from unittest.mock import Mock
        d = Mock()
        d.get_feature_report.return_value = bytes(32)
        with patch.object(tp, 'connect', return_value=d):
            with self.assertRaises(ValueError): tp.write(tp.Config())
        d.send_feature_report.assert_not_called()
        d.close.assert_called_once()

    def test_short_write_is_not_success(self):
        from unittest.mock import Mock
        d = Mock(); d.get_feature_report.return_value = response()
        d.send_feature_report.return_value = 5
        with patch.object(tp, 'connect', return_value=d):
            with self.assertRaises(OSError): tp.write(tp.Config())
        d.close.assert_called_once()

    def test_save_requires_sensor_ack(self):
        with patch.object(tp, 'read', return_value=tp.decode(response(flags=1))), \
             patch.object(tp, 'write') as write:
            with self.assertRaises(RuntimeError): tp.save_and_wait(tp.Config())
            write.assert_not_called()

    def test_save_waits_until_flash_worker_completes(self):
        initial = tp.decode(response(flags=3))
        pending = tp.decode(response(flags=7))
        done = tp.decode(response(flags=2))
        with patch.object(tp, 'read', side_effect=[initial, pending, done]), \
             patch.object(tp, 'write') as write, patch.object(tp.time, 'sleep'):
            self.assertEqual(tp.save_and_wait(tp.Config()), done)
            write.assert_called_once_with(tp.Config(), save=True)

    def test_flash_failure_is_reported(self):
        with patch.object(tp, 'read', side_effect=[tp.decode(response(flags=3)),
                           tp.decode(response(flags=3, save_error=-1))]), \
             patch.object(tp, 'write'):
            with self.assertRaises(OSError): tp.save_and_wait(tp.Config())


if __name__ == '__main__': unittest.main()
