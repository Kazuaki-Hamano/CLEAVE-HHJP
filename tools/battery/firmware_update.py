"""Offline CLEAVE UF2 validation; no device access or firmware writes."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import struct

SIDE_NAMES = ("左（親機）", "右（子機）")

@dataclass(frozen=True)
class Firmware:
    path: Path
    side: int
    build: str
    data: bytes
    sha256: str


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
