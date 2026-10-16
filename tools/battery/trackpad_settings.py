"""Trackpad controls over the existing 32-byte vendor HID collection."""
from dataclasses import dataclass
import struct
import time
import queue
import threading


@dataclass(frozen=True)
class Config:
    speed: int = 200
    acceleration: int = 0
    maximum: int = 300
    sensitivity: int = 1

    def validate(self):
        if not (25 <= self.speed <= 800 and 0 <= self.acceleration <= 300 and
                100 <= self.maximum <= 800 and 1 <= self.sensitivity <= 4):
            raise ValueError('設定値が範囲外です')
        return self


def encode(config, save=False):
    config.validate()
    result = bytearray(32)
    result[:4] = bytes((7, 1, int(save), 0))
    struct.pack_into('<HHHB', result, 4, config.speed, config.acceleration,
                     config.maximum, config.sensitivity)
    return bytes(result)


def decode(data):
    data = bytes(data)
    if len(data) != 32 or data[:2] != b'\x07\x01' or data[2] & ~7 or data[3]:
        raise ValueError('タッチパッド設定に対応したファームウェアへ左右を更新してください')
    config = Config(*struct.unpack_from('<HHHB', data, 4)).validate()
    if data[11] > 4:
        raise ValueError('検出感度の応答が不正です')
    return {'config': config, 'dirty': bool(data[2] & 1),
            'applied': bool(data[2] & 2), 'saving': bool(data[2] & 4),
            'sensor_sensitivity': data[11],
            'sensor_error': struct.unpack_from('b', data, 12)[0],
            'save_error': struct.unpack_from('b', data, 13)[0]}


def connect():
    import hid
    candidates = [d for d in hid.enumerate() if d['usage_page'] == 0xff60 and d['usage'] == 1]
    if len(candidates) != 1:
        raise RuntimeError('CLEAVEの左側をUSBで1台だけ接続してください')
    device = hid.device()
    try:
        device.open_path(candidates[0]['path'])
    except Exception:
        device.close()
        raise
    return device


def read():
    device = connect()
    try:
        return decode(device.get_feature_report(7, 32))
    finally:
        device.close()


def write(config, save=False):
    device = connect()
    try:
        # Probe before writing; an older firmware must never receive a command.
        decode(device.get_feature_report(7, 32))
        payload = encode(config, save)
        if device.send_feature_report(payload) != len(payload):
            raise OSError('設定を送信できませんでした')
        return decode(device.get_feature_report(7, 32))
    finally:
        device.close()


def save_and_wait(config, timeout=8):
    status = read()
    if status['config'] != config or not status['applied']:
        raise RuntimeError('設定が右側へ反映されてから保存してください')
    write(config, save=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = read()
        if status['save_error']:
            raise OSError('キーボードへの保存に失敗しました')
        if not status['saving'] and not status['dirty'] and status['config'] == config:
            return status
        time.sleep(0.1)
    raise TimeoutError('保存の完了を確認できませんでした')


def open_window(parent, is_busy=lambda: False):
    import tkinter as tk
    from tkinter import ttk

    window = tk.Toplevel(parent)
    window.title('CLEAVE タッチパッド設定')
    window.geometry('580x440')
    window.resizable(False, False)
    frame = ttk.Frame(window, padding=20)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='左側をUSB接続して調整します。変更はその場で反映されます。').pack(anchor='w')
    ttk.Label(frame, text='加速は指を動かす速さに応じて働きます。0%で加速なし。').pack(anchor='w', pady=(4, 16))
    values = [tk.IntVar(value=v) for v in (200, 0, 300, 1)]
    labels = [tk.StringVar() for _ in range(3)]
    status_text = tk.StringVar(value='現在の設定を読み込んでいます…')
    tasks, results = queue.Queue(), queue.Queue()
    closed = threading.Event()
    state = {'ready': False, 'loading': True, 'pending': None, 'last': None,
             'sending': False, 'save': False, 'debounce': None}
    controls = []

    def current():
        return Config(*(v.get() for v in values)).validate()

    def refresh_labels():
        labels[0].set(f'{values[0].get()/100:.2f} 倍')
        labels[1].set(f'{values[1].get()} %')
        labels[2].set(f'{values[2].get()/100:.2f} 倍')

    def queue_change():
        state['debounce'] = None
        if state['ready'] and not state['loading']:
            state['pending'] = current()
            status_text.set('変更を反映しています…')

    def changed(*args):
        refresh_labels()
        if state['loading']:
            return
        if state['debounce'] is not None:
            window.after_cancel(state['debounce'])
        state['debounce'] = window.after(200, queue_change)

    for index, (title, low, high) in enumerate((('基本速度', 25, 800),
                                                ('加速の強さ', 0, 300),
                                                ('加速の最大倍率', 100, 800))):
        row = ttk.Frame(frame)
        row.pack(fill='x', pady=7)
        ttk.Label(row, text=title, width=17).pack(side='left')
        slider = tk.Scale(row, from_=low, to=high, orient='horizontal',
                          variable=values[index], showvalue=False, resolution=1,
                          command=changed, length=250, state='disabled')
        slider.pack(side='left')
        ttk.Label(row, textvariable=labels[index], width=10).pack(side='left', padx=8)
        controls.append(slider)
    row = ttk.Frame(frame)
    row.pack(fill='x', pady=12)
    ttk.Label(row, text='検出感度', width=17).pack(side='left')
    for n in range(1, 5):
        radio = ttk.Radiobutton(row, text=f'{n}x', value=n, variable=values[3], command=changed)
        radio.pack(side='left', padx=10)
        radio.state(['disabled'])
        controls.append(radio)
    ttk.Label(frame, text='検出感度は触れ方への反応です。カーソル速度の倍率ではありません。',
              wraplength=530).pack(anchor='w', pady=4)
    ttk.Label(frame, textvariable=status_text, wraplength=530).pack(anchor='w', pady=12)
    buttons = ttk.Frame(frame)
    buttons.pack(fill='x')

    def save():
        state['save'] = True
        status_text.set('保存しています…')

    save_button = ttk.Button(buttons, text='キーボードに保存', command=save, state='disabled')
    save_button.pack(side='left')
    ttk.Button(buttons, text='閉じる', command=window.destroy).pack(side='right')
    refresh_labels()

    def worker():
        while not closed.is_set():
            task = tasks.get()
            if task is None:
                break
            operation, config = task
            try:
                if operation == 'save':
                    result = save_and_wait(config)
                elif operation == 'apply':
                    result = write(config)
                else:
                    result = read()
                results.put((operation, result, None))
            except Exception as error:
                results.put((operation, None, str(error)))

    threading.Thread(target=worker, daemon=True).start()
    next_read = [0.0]

    def poll():
        if not window.winfo_exists():
            return
        while not results.empty():
            operation, status, error = results.get_nowait()
            state['sending'] = False
            if error:
                status_text.set(error)
                state['last'] = None
                save_button.state(['disabled'])
                # A rejected setting stays visible and can be adjusted/retried.
                next_read[0] = time.monotonic() + 2
                continue
            if not state['ready']:
                state['loading'] = True
                c = status['config']
                for variable, value in zip(values, (c.speed, c.acceleration, c.maximum, c.sensitivity)):
                    variable.set(value)
                refresh_labels()
                for control in controls:
                    if isinstance(control, tk.Scale): control.configure(state='normal')
                    else: control.state(['!disabled'])
                state['ready'] = True
                state['loading'] = False
            state['last'] = status
            if operation == 'save':
                status_text.set('キーボードに保存しました。再起動後も維持されます。')
            elif status['save_error']:
                status_text.set('保存に失敗しました。もう一度保存してください。')
            elif not status['applied']:
                status_text.set('速度は反映済み。検出感度の右側への反映を待っています…')
            else:
                status_text.set('反映済み・未保存' if status['dirty'] else '反映済み・保存状態と一致')
        status = state['last']
        waiting = state['pending'] is not None or state['debounce'] is not None
        can_save = (status and status['applied'] and not status['saving'] and
                    status['config'] == current() and not waiting and not state['sending'] and
                    not is_busy())
        save_button.state(['!disabled'] if can_save else ['disabled'])
        if is_busy():
            status_text.set('ファームウェア更新中は設定を変更できません')
        elif not state['sending']:
            if state['pending'] is not None:
                tasks.put(('apply', state['pending']))
                state['pending'] = None
            elif state['save']:
                state['save'] = False
                tasks.put(('save', current()))
            elif time.monotonic() >= next_read[0]:
                tasks.put(('read', None))
                next_read[0] = time.monotonic() + 0.5
            else:
                window.after(100, poll)
                return
            state['sending'] = True
        window.after(100, poll)

    def destroyed(event):
        if event.widget is window:
            closed.set()
            tasks.put(None)
    window.bind('<Destroy>', destroyed)
    window.after(0, poll)
    return window
