# Studio GATT transport snapshot

Source: https://github.com/cormoran/zmk
Revision: e5c9b6915b56801193e359dd9bad4a167ce0d1b8
Files: app/src/studio/gatt_rpc_transport.c and uuid.h. MIT headers retained.

Root CMake defers an app source replacement until ZMK has added its transport.
It requires exactly one original GATT translation unit and replaces only that
unit, keeping transport UUIDs, registration, framing and security unchanged.
The reusable workflow and west ZMK revision stay pinned and unchanged.

Local fixes:
- Size indication payloads from bt_gatt_get_mtu(conn) minus three ATT header
  bytes, rather than the link-layer data length. Default ATT MTU 23 means 20
  payload bytes. Invalid zero payload sizes do not submit an indication.
- Release the acquired connection reference when an indication is already busy.

These are demonstrated code defects; the user's actual negotiated MTU and
on-device first failure have not been captured. Hardware acceptance is pending.
