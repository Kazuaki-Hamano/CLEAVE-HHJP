"""Read the CLEAVE battery feature report; no Bluetooth pairing required."""
import argparse
import json
from pathlib import Path
import sys
import tkinter as tk
import ctypes
import queue

if not getattr(sys, 'frozen', False) and sys.prefix == sys.base_prefix:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'output/battery/python-packages'))
import hid


def decode(data):
    if len(data) != 7 or data[:2] != [1, 1] or data[2] > 100:
        raise ValueError('Unexpected battery report')
    if data[4] not in (0, 1) or (data[4] and data[3] > 100):
        raise ValueError('Invalid peripheral battery value')
    age = data[5] | data[6] << 8
    return {'left': data[2], 'right': data[3] if data[4] else None,
            'right_age_seconds': age if data[4] else None}


def read():
    candidates = [d for d in hid.enumerate() if d['usage_page'] == 0xff60 and d['usage'] == 1]
    if not candidates:
        raise RuntimeError('対応ファームウェアの親機が見つかりません')
    if len(candidates) > 1:
        raise RuntimeError('対応する親機が複数あります。1台だけ接続してください')
    device = hid.device()
    try:
        device.open_path(candidates[0]['path'])
        state = decode(device.get_feature_report(1, 7))
        state.update(left_power=None, right_power=None, right_power_age_seconds=None)
        try:
            # Windows uses the collection's largest FeatureReportByteLength (7).
            # Report 2 has six meaningful bytes; ignore any trailing padding.
            state.update(decode_power(device.get_feature_report(2, 7)[:6]))
        except (OSError, ValueError):
            # Old firmware exposes only report 1; retain its battery values.
            pass
        return state
    finally:
        device.close()


def decode_power(data):
    if len(data) != 6 or data[:2] != [2, 1] or data[2] > 3 or data[3] > 3:
        raise ValueError('Unexpected charging report')
    names = (None, 'battery', 'usb_idle', 'charging')
    return {'left_power': names[data[2]], 'right_power': names[data[3]],
            'right_power_age_seconds': (data[4] | data[5] << 8) if data[3] else None}


def side_label(side, level, power):
    percent = '未取得' if level is None else f'{level}%'
    suffix = {None: '充電不明', 'battery': 'バッテリー',
              'usb_idle': 'USB給電', 'charging': '充電中'}[power]
    return f'{side} {percent}（{suffix}）'


def tooltip(state):
    return 'CLEAVE：' + side_label('左', state['left'], state.get('left_power')) + ' ／ ' + \
        side_label('右', state['right'], state.get('right_power'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--window', action='store_true')
    parser.add_argument('--status-file', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.once:
        try:
            result = read()
            code = 0
        except Exception as error:
            result = {'error': str(error)}
            code = 1
        text = json.dumps(result, ensure_ascii=False)
        if args.output:
            args.output.write_text(text, encoding='utf-8')
        elif sys.stdout:
            print(text)
        return code

    import pystray
    from PIL import Image, ImageDraw

    # Hold a named mutex for the lifetime of the app to prevent duplicate icons.
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p)
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
    mutex = kernel.CreateMutexW(None, False, 'Local\\CLEAVE_Battery_Monitor')
    if not mutex:
        raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error() == 183:
        kernel.CloseHandle(mutex)
        return 0

    def picture(left=None, right=None, left_power=None, right_power=None):
        image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        for x, level, power in ((5, left, left_power), (35, right, right_power)):
            draw.rounded_rectangle((x, 10, x + 23, 57), radius=4, fill='#253341', outline='white', width=2)
            draw.rectangle((x + 7, 5, x + 16, 10), fill='white')
            if level is not None:
                height = max(1, round(39 * level / 100))
                color = '#ff6655' if level <= 20 else '#55d6a0'
                draw.rectangle((x + 4, 53 - height, x + 19, 53), fill=color)
            else:
                draw.line((x + 5, 28, x + 18, 41), fill='#aaaaaa', width=3)
                draw.line((x + 18, 28, x + 5, 41), fill='#aaaaaa', width=3)
            if power == 'charging':
                draw.polygon([(x+13, 19), (x+6, 34), (x+12, 34),
                              (x+9, 47), (x+19, 29), (x+13, 29)], fill='#ffff66')
        return image

    window = tk.Tk()
    window.title('CLEAVE バッテリー')
    window.geometry('430x220')
    if not args.window:
        window.withdraw()
    window.protocol('WM_DELETE_WINDOW', window.withdraw)
    levels = tk.StringVar(value='接続を確認しています…')
    detail = tk.StringVar()
    tk.Label(window, textvariable=levels, font=('Yu Gothic UI', 18)).pack(pady=(22, 8))
    tk.Label(window, textvariable=detail, wraplength=350).pack()
    commands = queue.Queue()
    current_state = {}
    icon = pystray.Icon('CLEAVE Battery', picture(), 'CLEAVE：接続を確認しています…',
        menu=pystray.Menu(
            pystray.MenuItem('残量ウィンドウを開く', lambda: commands.put('show'), default=True),
            pystray.MenuItem('終了', lambda: commands.put('quit'))))

    def handle_commands():
        while not commands.empty():
            command = commands.get_nowait()
            if command == 'quit':
                window.destroy()
                return
            window.deiconify()
            window.lift()
            window.focus_force()
        if args.status_file:
            args.status_file.write_text(json.dumps({
                'tooltip': icon.title, 'tray_visible': icon.visible,
                'window_hidden': window.state() == 'withdrawn',
                'battery': current_state,
            }, ensure_ascii=False), encoding='utf-8')
        window.after(100, handle_commands)

    def update():
        try:
            state = read()
            current_state.clear()
            current_state.update(state)
            levels.set(side_label('左', state['left'], state['left_power']) + '\n' +
                       side_label('右', state['right'], state['right_power']))
            age = state['right_age_seconds']
            icon.title = tooltip(state)
            icon.icon = picture(state['left'], state['right'], state['left_power'], state['right_power'])
            detail.set('右側の接続・通知を待っています' if age is None else
                       f'右側の残量は {age} 秒前に通知されました')
        except Exception as error:
            current_state.clear()
            current_state['error'] = str(error)
            levels.set('残量を取得できません')
            detail.set(str(error))
            icon.title = 'CLEAVE：未接続／残量を取得できません'
            icon.icon = picture()
        window.after(5000, update)

    try:
        icon.run_detached()
        window.after(0, update)
        window.after(100, handle_commands)
        window.mainloop()
    finally:
        icon.stop()
        kernel.CloseHandle(mutex)
    return 0


if __name__ == '__main__':
    sys.exit(main())
