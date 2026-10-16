import json
from pathlib import Path
import re
import sys
import zipfile

sys.path.insert(0, str(Path('tools/battery').resolve()))
import firmware_update

root = Path(sys.argv[1])
builds = {}
with zipfile.ZipFile(root / 'build-logs.zip') as logs:
    for side, name in enumerate(('left', 'right')):
        uf2 = next(root.glob(f'*{name}*.uf2'))
        firmware = firmware_update.validate_firmware(uf2, side)
        builds[name] = firmware.build
        entry = next(n for n in logs.namelist() if name in n and 'Devicetree file' in n)
        dts = '\n'.join(line.split('Z ', 1)[-1] for line in logs.read(entry).decode().splitlines())
        match = re.search(r'default_layer\s*\{.*?bindings\s*=\s*<(.*?)>;', dts, re.S)
        bindings = [' '.join(binding.split()) for binding in re.findall(r'&[^&]+', match.group(1))]
        assert len(bindings) == 70
        assert bindings[60] == '&lt 0x1 0x7008b', bindings[60]
        assert bindings[63] == '&lt 0x1 0x7008a', bindings[63]
        assert bindings[64] == '&kp 0x70090', bindings[64]
        assert 'tapping-term-ms = < 0xc8 >;' in dts
        fn_match = re.search(r'fn_layer\s*\{.*?bindings\s*=\s*<(.*?)>;', dts, re.S)
        fn_bindings = [' '.join(binding.split()) for binding in re.findall(r'&[^&]+', fn_match.group(1))]
        assert fn_bindings[16] == '&mkp 0x1', fn_bindings[16]
        assert fn_bindings[18] == '&mkp 0x2', fn_bindings[18]
        if name == 'left':
            assert not re.search(r'fn_scroll\s*\{', dts), 'Fn must preserve right pointer movement'

        print(name, 'INT5/Fn, INT4/Fn, Kana LANG1 and 200ms hold-tap: PASS', firmware.build)
assert builds['left'] == builds['right']
(root / 'keymap-verification.json').write_text(json.dumps({'builds': builds, 'positions': {'60': 'INT5/Fn', '63': 'INT4/Fn', '64': 'LANG1/Kana'}, 'verified': True}, indent=2), encoding='utf-8')
