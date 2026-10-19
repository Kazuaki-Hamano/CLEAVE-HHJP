import datetime
import json
from pathlib import Path
import sys
import time
import hid

sys.path.insert(0, str(Path('tools/battery').resolve()))
import battery_monitor
destination = Path('output/battery/raw-battery-diagnostic.jsonl')
end = time.monotonic() + 75
last = None
with destination.open('a', encoding='utf-8', buffering=1) as stream:
    while time.monotonic() < end:
        record = {'time': datetime.datetime.now().astimezone().isoformat()}
        try:
            candidates = [d for d in hid.enumerate() if d['usage_page'] == 0xff60 and d['usage'] == 1]
            if len(candidates) != 1:
                raise RuntimeError(f'Expected one central: {len(candidates)}')
            dev = hid.device()
            try:
                dev.open_path(candidates[0]['path'])
                raw = list(dev.get_feature_report(1, 32))
                power = list(dev.get_feature_report(2, 32))
                record.update(raw_battery=raw, raw_power=power)
                record.update(battery_monitor.decode(raw[:7]))
                record.update(battery_monitor.decode_power(power[:6]))
            finally:
                dev.close()
            summary = (record['left'], record['right'], record['left_power'], record['right_power'])
        except Exception as error:
            record['error'] = str(error)
            summary = record['error']
        stream.write(json.dumps(record, ensure_ascii=False) + '\n')
        if summary != last:
            print(json.dumps(record, ensure_ascii=False), flush=True)
            last = summary
        time.sleep(1)
print('Saved', destination, flush=True)
