# Studio BLE transport stabilization trial

Branch: `fix/dya-ble-transport`, based on accepted main rather than the local-web
client patch branch. Source `b0c9f322`. User reports candidates are visible but
selection leaves DYA connecting indefinitely, with USB unplugged. Public and
local DYA both fail, so the browser-only patch is not a complete remedy.

## Demonstrated defects

Pinned ZMK `e5c9b6915b56801193e359dd9bad4a167ce0d1b8` sizes indications from
link-layer `tx_max_len`, ignoring ATT MTU and its three-byte indication header.
For ATT MTU 23 and data length 27 it removes 27 bytes from the RPC ring, attempts
an oversized indication, and loses that chunk on error. Mock reproduction sends
an 80-byte frame and demonstrates invalid indications and data loss. The fix uses
`bt_gatt_get_mtu(conn) - 3`, bounded by the existing 27-byte buffer; default payload
is 20 bytes. It does not enlarge stacks/buffers, change UUIDs/security or alter USB.

The TX callback also obtains the active connection and returns without unref
when its indication semaphore is busy. The same production callback mock proves
one retained reference per busy call. The fix unrefs on that return path.

These are verified source defects, not a capture of the user's negotiated MTU
or first on-device failure. Other BLE/browser problems may remain. A successful
build or initial connection will not be treated as full stability acceptance.

## Integration / checks

A pinned local snapshot of only the GATT source and its private uuid header is
used. Root CMake defers source replacement to the end of app configuration,
requires exactly one upstream GATT source, then compiles the corrected source
once. Right retains its original single-link split role. The source override is
checked in the actual CI logs. ZMK and reusable workflow revisions stay pinned.

`python tools/dya-studio/test_gatt_mtu.py` compiles the actual original and patched
sizing/TX functions using ring-buffer, ATT and reference-count mocks. Original
MTU overflow/data loss and busy reference leak reproduce. Patched MTU23/247
transfers retain all 80 ordered bytes; busy and invalid-size paths release their
references. Build and artifact evidence follows below.

## Hardware procedure

1. Flash both trial halves, retaining existing keymap, settings and pairings.
2. Unplug USB, confirm Bluetooth typing works on the intended PC profile.
3. Use one DYA tab for the test, initially the public site. Press Fn+U and select
   CLEAVE HHJP. Wait for actual keymap/settings loading, rather than just discovery.
4. Change one trackpad value, wait for RAM write, save and verify unsaved clears.
   Reconnect and read back; keyboard reboot/readback checks durable persistence.
5. Repeat connect/disconnect a few times and retain a session beyond the 60-second
   discovery window. Verify typing, right input, sleep/wake and USB Studio.
6. Report whether failure is selection/service discovery, initial RPC loading,
   RAM write or save/readback; preserve the first displayed error if present.

The local web server/client patch remains available separately. No additional
browser changes are bundled with this firmware trial. Main integration waits for
hardware confirmation of actual reading and saving, not discovery alone.

## ?????

- ???: `b0c9f322`???????: `e05954d3`
- Actions: https://github.com/Kazuaki-Hamano/CLEAVE-HHJP/actions/runs/39349698671
- ????: `V:\Projects\CLEAVE-HHJP\output\firmware\b0c9f322`
- UF2???????????????????GATT??????????????????: PASS?????SHA256???
- ??????????????????????????????main????????
