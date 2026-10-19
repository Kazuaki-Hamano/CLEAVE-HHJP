# DYA Studio over Bluetooth

Branch: `feature/dya-ble-discovery`; firmware source `025d2c68`.
The accepted firmware already compiles Studio's encrypted GATT RPC transport.
Windows discovery additionally needs advertising after the paired PC connects.
In the pinned cormoran fork, `zmk_ble_set_directed_advertising(true)` requests
ordinary connectable advertising; the function name is historical.

## Implementation

Central only: new zero-parameter `Studio BLE Discovery` behavior, stock Fn+U
(Fn position 22). Work queued by the press unlocks Studio, requests advertising
and schedules expiry after 60 seconds. Repeated presses renew the window.
Expiry clears the advertising override, preserving existing HID, split and
Studio connections. It preserves output, profile and pairing state. A failed
start clears the override and cancels expiry. No window opens at boot.
Normal pairing/reconnection advertising still applies to empty/disconnected
profiles after expiry. USB and the existing unlocked Studio configuration remain.
Automatic unbounded advertising on generic Studio Unlock is disabled.
Right remains a single-link split peripheral with no host Studio service.

## Connection procedure

1. Flash both trial UF2s, retaining existing settings and pairings.
2. If a saved keymap overrides Fn+U, connect DYA via USB, assign
   `Studio BLE Discovery` to U on Fn and save. The whole keymap can be retained.
3. Select the PC's existing Bluetooth profile and confirm Bluetooth typing.
   For the first test unplug USB so the selected output is BLE. When keeping USB
   attached, select Bluetooth output priority in DYA first. Studio selects its
   active transport according to the output endpoint.
4. Open https://studio.dya.cormoran.works/ in Chrome or Edge, disconnect the USB
   Studio session, press Fn+U, click Bluetooth and select CLEAVE HHJP in the
   browser chooser within 60 seconds. Repeat Fn+U if needed.
5. Check keymap, trackpad, settings and diagnostics. Save a reversible change and
   restore it. Keep DYA connected beyond 60 seconds and confirm it stays usable,
   ordinary typing works and right-side input remains available.
6. Disconnect DYA; check ordinary typing, both-half sleep/wake and USB Studio.

The browser uses GATT on the paired PC link, not another keyboard profile.
BLE loading may take longer than USB. If the chooser is empty, first check
profile, Fn+U assignment, Bluetooth typing and browser Bluetooth support.

## Validation

`python tools/dya-studio/test_ble_discovery.py` compiles production callbacks
with a deterministic work-queue mock: manual start, release, 60-second renewal,
expiry and failed-start cleanup passed. Keymap comparison confirms Default is
unchanged and only Fn position 22 changes from transparent to discovery.
Build/artifact checks and hardware acceptance will be recorded below.

## Trial artifacts

Actions run `39343268952`; source `025d2c68`; firmware identity `d76ea2d0`.
Both side build jobs succeeded. UF2 integrity/HID, actual USB and BLE transports,
left-only discovery behavior/source, stock Fn+U, unchanged original Default keys,
prior host layers, split roles/stacks, sleep, trackpads, settings sync, layout and
diagnostics configuration checks passed. Unit callback checks passed.
Left GNU build-id: `cba5e754a324e46046016d53f082554af41170db`.
Artifacts: `output/firmware/025d2c68/`, copied with matching SHA-256 hashes to the
canonical workspace. Real Windows browser discovery, BLE RPC/edit/save, continued
operation after expiry and sleep/wake still require hardware acceptance.
Main is unchanged.

## Hardware acceptance

On 2026-10-20, the user confirmed successful Bluetooth connection to DYA Studio.
This confirms browser discovery and connection and accepts the feature for main
integration. The report did not separately confirm edit/save, operation beyond
60 seconds or sleep/wake; those checks are not claimed hardware verified.
Firmware source remains `025d2c68`, identity `d76ea2d0`. The merge requires no
additional flash or settings reset.
