import sys
sys.path.insert(0, 'tools/battery')
import tkinter as tk
import pystray
from pathlib import Path
from unittest.mock import patch
import battery_monitor as monitor
import firmware_update as updater

objects = {}
results = []
original_tk, original_icon = tk.Tk, pystray.Icon
firmware_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('output/firmware/bc546789')
firmware_path = next(firmware_root.glob('*right*.uf2')).resolve()
left_path = next(firmware_root.glob('*left*.uf2')).resolve()

def make_icon(*args, **kwargs):
    objects['icon'] = original_icon(*args, **kwargs)
    return objects['icon']

def descendants(widget):
    return [child for direct in widget.winfo_children() for child in [direct] + descendants(direct)]

def create_window(*args, **kwargs):
    window = original_tk(*args, **kwargs)
    objects['window'] = window
    def open_dialog():
        objects['icon'].menu.items[1](objects['icon'])
    def run_update():
        dialog = next(w for w in window.winfo_children() if isinstance(w, tk.Toplevel))
        controls = descendants(dialog)
        entry = next(w for w in controls if w.winfo_class() == 'TEntry')
        entry.insert(0, str(firmware_path))
        button = next(w for w in controls if w.winfo_class() == 'TButton' and w.cget('text') == '更新開始')
        button.invoke()
        results.append('Update dialog opens from tray and validates selected UF2')
    def finish():
        assert objects['calls'] == [(1, True), (0, True)]
        dialog = next(w for w in window.winfo_children() if isinstance(w, tk.Toplevel))
        labels = [w for w in descendants(dialog) if w.winfo_class() == 'TLabel' and w.cget('textvariable')]
        assert any('右側のバージョンも一致' in window.getvar(w.cget('textvariable')) for w in labels)
        results.append('Initial right pending result is verified after left update; no real flash performed')
        objects['icon'].menu.items[-1](objects['icon'])
    def update_left():
        dialog = next(w for w in window.winfo_children() if isinstance(w, tk.Toplevel))
        controls = descendants(dialog)
        next(w for w in controls if w.winfo_class() == 'TCombobox').set('左（親機）')
        entry = next(w for w in controls if w.winfo_class() == 'TEntry')
        entry.delete(0, 'end')
        entry.insert(0, str(left_path))
        next(w for w in controls if w.winfo_class() == 'TButton' and w.cget('text') == '更新開始').invoke()
    window.after(700, open_dialog)
    window.after(1200, run_update)
    window.after(1700, update_left)
    window.after(2300, finish)
    window.after(10000, window.destroy)
    return window

def fake_update(firmware, manual, progress):
    objects.setdefault('calls', []).append((firmware.side, manual))
    progress('テスト進捗')
    return {'verified': firmware.side == 0, 'message': 'テスト完了'}

def fake_info(side):
    if side == 0:
        raise RuntimeError('old firmware')
    return {'build': updater.validate_firmware(firmware_path, 1).build}

tk.Tk, pystray.Icon = create_window, make_icon
sys.argv = ['battery_monitor.py']
with patch.object(updater, 'perform_update', side_effect=fake_update), \
     patch.object(updater, 'read_info', side_effect=fake_info):
    assert monitor.main() == 0
assert len(results) == 2
print('\n'.join(results))
