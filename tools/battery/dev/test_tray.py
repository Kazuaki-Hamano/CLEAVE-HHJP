import importlib.util
import json
from pathlib import Path
import sys
import tkinter as tk
import pystray
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

spec = importlib.util.spec_from_file_location('monitor', 'tools/battery/battery_monitor.py')
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)
real_tk, real_icon = tk.Tk, pystray.Icon
objects = {}
results = []

def create_icon(*args, **kwargs):
    objects['icon'] = real_icon(*args, **kwargs)
    return objects['icon']

def create_window(*args, **kwargs):
    window = real_tk(*args, **kwargs)
    objects['window'] = window
    def check_hidden():
        assert window.state() == 'withdrawn'
        assert objects['icon'].visible
        assert '左' in objects['icon'].title and '右' in objects['icon'].title
        results.append('Native tray visible, tooltip contains live USB values, window hidden')
        objects['icon'].menu.items[0](objects['icon'])
    def check_open():
        assert window.state() == 'normal'
        results.append('Open menu action displays window')
        window.tk.call(window.protocol('WM_DELETE_WINDOW'))
    def check_close():
        assert window.state() == 'withdrawn' and objects['icon'].visible
        results.append('Closing window retains tray')
        objects['icon'].menu.items[-1](objects['icon'])
    window.after(1000, check_hidden)
    window.after(1500, check_open)
    window.after(2000, check_close)
    window.after(10000, window.destroy)
    return window

tk.Tk, pystray.Icon = create_window, create_icon
sys.argv = ['battery_monitor.py']
assert monitor.main() == 0
assert len(results) == 3
objects['icon']._thread.join(timeout=2)
assert not objects['icon']._thread.is_alive()
assert objects['icon']._hwnd not in objects['icon']._HWND_TO_ICON
results.append('Exit menu action shuts down and removes tray icon')
Path('output/battery/tray-test.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
print('\n'.join(results))
