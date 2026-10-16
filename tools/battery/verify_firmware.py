import hashlib
import json
from pathlib import Path
import struct
import sys
import zipfile

root = Path(sys.argv[1])
checksums = {}
for path in root.glob('*.uf2'):
    data = path.read_bytes()
    assert len(data) % 512 == 0
    payloads = {}
    for offset in range(0, len(data), 512):
        block = data[offset:offset + 512]
        magic0, magic1, flags, address, size, index, count, family = struct.unpack('<8I', block[:32])
        assert (magic0, magic1) == (0x0a324655, 0x9e5d5157)
        assert struct.unpack('<I', block[508:])[0] == 0x0ab16f30
        assert size <= 476 and count == len(data) // 512
        assert flags & 0x2000 and family == 0xada52840
        assert index not in payloads
        payloads[index] = block[32:32 + size]
    assert len(payloads) == count
    payload = b''.join(payloads[i] for i in range(count))
    if 'left' in path.name:
        for label, signature in {
            'keyboard HID': '05010906a101',
            'mouse HID': '05010902a101',
            'battery HID': '0660ff0901a10185010902150026ff0075089506b102',
            'charging HID': '850209039505b102',
            'update command HID': '850409059507b102',
        }.items():
            assert bytes.fromhex(signature) in payload, label + ' missing'
            print(label, 'present')
    checksums[path.name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}

logs = zipfile.ZipFile(root / 'build-logs.zip')
config_name = next(n for n in logs.namelist() if 'left' in n and 'Kconfig file' in n)
config = logs.read(config_name).decode()
for value in ('CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING=y',
              'CONFIG_ZMK_BATTERY_REPORTING=y', 'CONFIG_USB_HID_DEVICE_COUNT=2',
              'CONFIG_ZMK_POINTING=y', 'CONFIG_ZMK_STUDIO=y'):
    assert value in config, value
    print(value)
(root / 'checksums.json').write_text(json.dumps(checksums, indent=2))
print('UF2 integrity and configuration: PASS')
