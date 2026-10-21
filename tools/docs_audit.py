from pathlib import Path
import re
from urllib.parse import unquote

docs = [Path('README.md')] + list(Path('docs').glob('*.md')) + list(Path('build-guide').rglob('*.md')) + list(Path('tools').rglob('*.md'))
pattern = re.compile(r'!?\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)|(?:src|href)="([^"]+)"')
bad = []
total = 0
for doc in docs:
    text = doc.read_text(encoding='utf-8-sig')
    for match in pattern.finditer(text):
        dest = match.group(1) or match.group(2)
        if dest.startswith(('http:', 'https:', 'mailto:')):
            continue
        filename, _, anchor = dest.partition('#')
        target = doc.parent / unquote(filename) if filename else doc
        total += 1
        if not target.exists():
            bad.append((str(doc), dest, 'missing file'))
        elif anchor and target.suffix == '.md':
            headings = re.findall(r'^#+\s+(.+)$', target.read_text(encoding='utf-8-sig'), re.M)
            slugs = {re.sub(r'[^\w\- ]', '', h.lower()).replace(' ', '-') for h in headings}
            if unquote(anchor) not in slugs:
                bad.append((str(doc), dest, 'missing heading'))
print(f'Documents: {len(docs)}, local links: {total}, issues: {len(bad)}')
for issue in bad:
    print(*issue)

# Source facts described by the current design document.
design = Path('docs/firmware_design.md').read_text(encoding='utf-8-sig')
keymap = Path('config/cleave_hhjp.keymap').read_text()
for layer in ('default_layer', 'fn_layer'):
    bindings = re.search(layer + r'\s*\{.*?bindings\s*=\s*<(.*?)>;', keymap, re.S).group(1)
    assert bindings.count('&') == 70, layer
    assert layer in design
assert 'mouse_layer {' not in keymap
assert '&lt 1 INT4' in keymap
for source, tokens in {
    'config/boards/shields/cleave_hhjp/cleave_hhjp_left.conf': ['CONFIG_ZMK_POINTING=y', 'CONFIG_USB_HID_DEVICE_COUNT=2', 'CONFIG_ZMK_STUDIO_LOCKING=n'],
    'config/west.yml': ['revision: e5c9b6915b56801193e359dd9bad4a167ce0d1b8', 'revision: 63363d92c475ad203b35e9047cef7ecd8706a6fc'],
    'build.yaml': ['board: xiao_ble//zmk', 'snippet: studio-rpc-usb-uart'],
    'config/cleave_hhjp.keymap': ['#include <behaviors/runtime_macro.dtsi>', '&lt 1 INT5'],
    'config/boards/shields/cleave_hhjp/cleave_hhjp_right.conf': ['CONFIG_ZMK_SPLIT_BLE_PERIPHERAL_STACK_SIZE=2048', 'CONFIG_ZMK_SLEEP=y'],
    'src/app_update.c': ['K_MSEC(250)', 'K_SECONDS(5)', '<= 20000'],
    'tools/battery/firmware_update.py': ['def validate_firmware(', '0x27000', '0xec000'],
}.items():
    content = Path(source).read_text(encoding='utf-8')
    for token in tokens:
        assert token in content, (source, token)
assert 'trackpad_scroll' in design
assert 'Feature 7' in design
print('Documented source constants and 2 x 70 bindings: OK')
raise SystemExit(bool(bad))
