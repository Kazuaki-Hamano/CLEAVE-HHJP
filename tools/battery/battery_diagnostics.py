"""Record raw HID reports and cached firmware voltage without triggering ADC sampling."""
import argparse
import datetime
import json
from pathlib import Path
import sys
import time

if not getattr(sys, 'frozen', False) and sys.prefix == sys.base_prefix:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'output/battery/python-packages'))
import hid
from battery_monitor import decode, decode_power


def decode_diagnostics(data):
    data = bytes(data)
    if len(data) != 16 or data[:2] != bytes([6, 1]) or data[2] > 100 or data[3] > 3:
        raise ValueError('Unexpected diagnostic report')
    flags = data[7]
    if flags & ~3 or (flags & 2 and data[6] > 100):
        raise ValueError('Invalid diagnostic flags/state')
    age = int.from_bytes(data[12:16], 'little')
    return {'firmware_percent': data[2], 'power_state': data[3],
            'voltage_mv': int.from_bytes(data[4:6], 'little') if flags & 1 else None,
            'sensor_percent': data[6] if flags & 2 else None,
            'uptime_seconds': int.from_bytes(data[8:12], 'little'),
            'percent_change_age_seconds': age if age != 0xffffffff else None}


def capture():
    candidates = [d for d in hid.enumerate() if d['usage_page'] == 0xff60 and d['usage'] == 1]
    if len(candidates) != 1:
        raise RuntimeError('USB接続された親機を1台だけ接続してください')
    dev = hid.device()
    try:
        dev.open_path(candidates[0]['path'])
        raw = list(dev.get_feature_report(1, 32))
        power = list(dev.get_feature_report(2, 32))
        result = {'raw_battery': raw, 'raw_power': power, **decode(raw[:7]), **decode_power(power[:6])}
        try:
            diagnostic = list(dev.get_feature_report(6, 32))
            result.update(raw_diagnostics=diagnostic, diagnostics=decode_diagnostics(diagnostic[:16]))
        except (OSError, ValueError) as error:
            result['diagnostic_error'] = str(error)
        return result
    finally:
        dev.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=float, default=600, help='Recording seconds (default: 600)')
    parser.add_argument('--interval', type=float, default=1, help='Polling seconds (default: 1)')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.duration <= 0 or args.interval <= 0:
        parser.error('duration and interval must be positive')
    now = datetime.datetime.now().astimezone()
    destination = args.output or Path('output/battery') / f"battery-diagnostics-{now:%Y%m%d-%H%M%S}.jsonl"
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f'Log: {destination.resolve()}\nCtrl+C to stop.', flush=True)
    deadline = time.monotonic() + args.duration
    last = None
    with destination.open('x', encoding='utf-8', buffering=1) as stream:
        try:
            while time.monotonic() < deadline:
                record = {'time': datetime.datetime.now().astimezone().isoformat()}
                try:
                    record.update(capture())
                    diag = record.get('diagnostics', {})
                    summary = (record['left'], record['right'], record['left_power'],
                               record['right_power'], diag.get('voltage_mv'))
                    if last is not None and isinstance(last, tuple):
                        record['left_change_points'] = record['left'] - last[0]
                except Exception as error:
                    record['error'] = str(error)
                    summary = record['error']
                stream.write(json.dumps(record, ensure_ascii=False) + '\n')
                if summary != last:
                    print(json.dumps(record, ensure_ascii=False), flush=True)
                last = summary
                time.sleep(min(args.interval, max(0, deadline - time.monotonic())))
        except KeyboardInterrupt:
            pass
    print('Recording finished.', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
