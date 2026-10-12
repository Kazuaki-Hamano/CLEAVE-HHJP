"""Read the CLEAVE battery feature report; no Bluetooth pairing required."""
import argparse
import json
from pathlib import Path
import sys
import tkinter as tk

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
        return decode(device.get_feature_report(1, 7))
    finally:
        device.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    if args.once:
        try:
            print(json.dumps(read(), ensure_ascii=False))
        except Exception as error:
            print(json.dumps({'error': str(error)}, ensure_ascii=False))
            return 1
        return 0
    window = tk.Tk()
    window.title('CLEAVE バッテリー')
    window.geometry('380x160')
    levels = tk.StringVar(value='接続を確認しています…')
    detail = tk.StringVar()
    tk.Label(window, textvariable=levels, font=('Yu Gothic UI', 22)).pack(pady=(22, 8))
    tk.Label(window, textvariable=detail, wraplength=350).pack()

    def update():
        try:
            state = read()
            right = '未取得' if state['right'] is None else str(state['right']) + '%'
            levels.set(f"左 {state['left']}%　右 {right}")
            age = state['right_age_seconds']
            detail.set('右側の接続・通知を待っています' if age is None else
                       f'右側の値は {age} 秒前に受信（古い値の場合は右側を起こしてください）')
        except Exception as error:
            levels.set('残量を取得できません')
            detail.set(str(error))
        window.after(5000, update)

    window.after(0, update)
    window.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
