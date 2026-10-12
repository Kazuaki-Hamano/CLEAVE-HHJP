"""Validated, per-half UF2 update over the existing USB/BLE connection."""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import struct
import time
import hid

SIDE_NAMES = ('左（親機）', '右（子機）')


@dataclass(frozen=True)
class Firmware:
    path: Path
    side: int
    build: str
    data: bytes
    sha256: str


@dataclass(frozen=True)
class BootDrive:
    root: str
    serial: int
    board: str


def validate_firmware(path, side):
    path = Path(path)
    if side not in (0, 1) or path.suffix.lower() != '.uf2':
        raise ValueError('対象の左右とUF2ファイルを選択してください')
    with path.open('rb') as stream:
        data = stream.read(2 * 1024 * 1024 + 1)
    if not data or len(data) > 2 * 1024 * 1024 or len(data) % 512:
        raise ValueError('UF2ファイルのサイズが不正です')
    blocks = {}
    for offset in range(0, len(data), 512):
        block = data[offset:offset+512]
        m0, m1, flags, address, size, index, count, family = struct.unpack('<8I', block[:32])
        if (m0, m1, struct.unpack('<I', block[508:])[0]) != (0x0a324655, 0x9e5d5157, 0x0ab16f30):
            raise ValueError('UF2の形式が不正です')
        if flags != 0x2000 or family != 0xada52840 or size != 256:
            raise ValueError('対応するXIAO nRF52840用UF2ではありません')
        if count != len(data) // 512 or index >= count or index in blocks:
            raise ValueError('UF2のブロックが欠落・重複しています')
        if address < 0x27000 or address + size > 0xec000 or address % 256:
            raise ValueError('アプリ領域外への書き込みを含むUF2は使用できません')
        blocks[index] = (address, block[32:32+size])
    ordered = [blocks[i] for i in range(len(blocks))]
    if ordered[0][0] != 0x27000 or any(b[0] != a[0] + 256 for a, b in zip(ordered, ordered[1:])):
        raise ValueError('UF2のアプリ領域が連続していません')
    payload = b''.join(b[1] for b in ordered)
    identities = set(re.findall(rb'CLEAVE_HHJP_UPDATE1\|(LEFT|RIGHT)\|([0-9a-f]{8})\x00', payload))
    if len(identities) != 1:
        raise ValueError('左右を識別できる新しいCLEAVE用UF2を選択してください')
    name, build = identities.pop()
    actual_side = 0 if name == b'LEFT' else 1
    if actual_side != side:
        raise ValueError(f'選択したUF2は{SIDE_NAMES[actual_side]}用です。対象を確認してください')
    return Firmware(path, side, build.decode(), data, hashlib.sha256(data).hexdigest())


def device():
    candidates = [d for d in hid.enumerate() if d['usage_page'] == 0xff60 and d['usage'] == 1]
    if len(candidates) != 1:
        raise RuntimeError('USB接続されたCLEAVEの親機を1台だけ接続してください')
    result = hid.device()
    try:
        result.open_path(candidates[0]['path'])
    except Exception:
        result.close()
        raise
    return result


def read_info(side):
    if side not in (0, 1):
        raise ValueError('Invalid side')
    dev = device()
    try:
        report_id = 3 if side == 0 else 5
        data = dev.get_feature_report(report_id, 32)
        if len(data) != 32 or data[:3] != [report_id, 1, side] or bytes(data[12:16]) != b'CHHP' or not data[3] & 1:
            raise RuntimeError('対象の更新対応ファームウェアが見つかりません')
        build = bytes(data[4:12]).decode('ascii')
        if not re.fullmatch('[0-9a-f]{8}', build):
            raise RuntimeError('ファームウェアの識別情報が不正です')
        return {'side': side, 'build': build, 'usb': bool(data[3] & 2), 'uid': bytes(data[16:24]).hex()}
    finally:
        dev.close()


def request_boot(side):
    info = read_info(side)
    if not info['usb']:
        raise RuntimeError('更新する側にUSBデータケーブルを接続し、数秒待ってください')
    dev = device()
    try:
        # Feature collections have a maximum report length of 32 on Windows.
        # hidapi pads SET_FEATURE to that length; the firmware ignores zero padding.
        command = bytes([4, 1, side]) + b'BOOT' + bytes(25)
        if dev.send_feature_report(command) != len(command):
            raise RuntimeError('更新モードへの指示を送信できませんでした')
    finally:
        dev.close()
    return info


def scan_boot_drives():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetLogicalDriveStringsW.argtypes = (wintypes.DWORD, wintypes.LPWSTR)
    kernel.GetLogicalDriveStringsW.restype = wintypes.DWORD
    kernel.GetDriveTypeW.argtypes = (wintypes.LPCWSTR,)
    kernel.GetVolumeInformationW.argtypes = (wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p, ctypes.c_void_p, wintypes.LPWSTR, wintypes.DWORD)
    length = kernel.GetLogicalDriveStringsW(0, None)
    buffer = ctypes.create_unicode_buffer(length + 1)
    kernel.GetLogicalDriveStringsW(length + 1, buffer)
    found = set()
    for root in buffer[:length].split('\0'):
        if not root or kernel.GetDriveTypeW(root) not in (2, 3):
            continue
        try:
            with (Path(root) / 'INFO_UF2.TXT').open('rb') as stream:
                text = stream.read(8192).decode('utf-8', errors='replace')
            match = re.search(r'^Board-ID:\s*([^\r\n]+)', text, re.MULTILINE | re.IGNORECASE)
            if not match:
                continue
            serial = wintypes.DWORD()
            if kernel.GetVolumeInformationW(root, None, 0, ctypes.byref(serial), None, None, None, 0):
                found.add(BootDrive(root, serial.value, match[1].strip()))
        except OSError:
            pass
    return found


def wait_boot_drive(baseline, scan=scan_boot_drives, timeout=90):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        new = scan() - baseline
        if len(new) > 1:
            raise RuntimeError('UF2ドライブが複数あります。書き込みは行いませんでした')
        if new:
            drive = next(iter(new))
            board = drive.board.lower()
            if not all(word in board for word in ('seeed', 'xiao', 'nrf52840')):
                raise RuntimeError('検出したUF2ドライブは対応するXIAOではありません')
            return drive
        time.sleep(0.25)
    raise TimeoutError('UF2ドライブが見つかりません。USB接続とキー操作を確認してください')


def copy_firmware(firmware, drive, progress, scan=scan_boot_drives):
    if scan() != {drive}:
        raise RuntimeError('書き込み先のドライブが変わりました。コピーを中止しました')
    target = Path(drive.root) / 'CLEAVE.UF2'
    # Use the validated in-memory bytes, even if the source file changes later.
    with target.open('wb', buffering=0) as stream:
        for offset in range(0, len(firmware.data), 16384):
            chunk = firmware.data[offset:offset+16384]
            written = 0
            while written < len(chunk):
                amount = stream.write(chunk[written:])
                if not amount:
                    raise OSError('UF2の書き込みが完了しませんでした')
                written += amount
            progress(f'UF2を送信中… {min(offset+len(chunk), len(firmware.data))*100//len(firmware.data)}%')
        import os
        os.fsync(stream.fileno())


def perform_update(firmware, manual, progress, scan=scan_boot_drives,
                   boot=request_boot, info=read_info, copier=copy_firmware,
                   drive_timeout=90, verify_timeout=60):
    baseline = scan()
    if baseline:
        raise RuntimeError('既にUF2ドライブがあります。通常動作へ戻してから開始してください')
    old_info = None
    if manual:
        progress('対象をUSB接続し、Fn＋B（左）／Fn＋N（右）を2秒長押ししてください')
    else:
        progress('更新モードへ移行しています…')
        old_info = boot(firmware.side)
    drive = wait_boot_drive(baseline, scan, drive_timeout)
    progress(f'{drive.root} を検出しました。UF2を送信します')
    try:
        copier(firmware, drive, progress, scan=scan)
    except OSError:
        # Some bootloaders disappear while Windows completes the final flush.
        # A matching running build below is still required for verified success.
        if drive in scan():
            raise
    progress('再起動後のファームウェアを確認しています…')
    end = time.monotonic() + verify_timeout
    while time.monotonic() < end:
        if drive not in scan():
            try:
                current = info(firmware.side)
                same_device = not old_info or old_info['uid'] == '0000000000000000' or current['uid'] == old_info['uid']
                if current['side'] == firmware.side and current['build'] == firmware.build and same_device:
                    return {'verified': True, 'build': firmware.build,
                            'message': f'{SIDE_NAMES[firmware.side]}の更新と再起動を確認しました'}
            except (OSError, RuntimeError, ValueError):
                pass
        time.sleep(0.5)
    if drive in scan():
        raise RuntimeError('UF2送信後の再起動を確認できませんでした')
    return {'verified': False, 'build': firmware.build,
            'message': '再起動後のバージョン確認が未完了です。親機のUSB接続・左右の接続を確認してください'}
