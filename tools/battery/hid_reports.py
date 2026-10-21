"""Pure decoders for read-only battery diagnostics."""

def decode(data):
    if len(data) != 7 or data[:2] != [1, 1] or data[2] > 100:
        raise ValueError('Unexpected battery report')
    if data[4] not in (0, 1) or (data[4] and data[3] > 100):
        raise ValueError('Invalid peripheral battery value')
    age = data[5] | data[6] << 8
    return {'left': data[2], 'right': data[3] if data[4] else None,
            'right_age_seconds': age if data[4] else None}

def decode_power(data):
    if len(data) != 6 or data[:2] != [2, 1] or data[2] > 3 or data[3] > 3:
        raise ValueError('Unexpected charging report')
    names = (None, 'battery', 'usb_idle', 'charging')
    return {'left_power': names[data[2]], 'right_power': names[data[3]],
            'right_power_age_seconds': (data[4] | data[5] << 8) if data[3] else None}
