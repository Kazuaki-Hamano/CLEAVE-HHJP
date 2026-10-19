# Deep-sleep hardware trial

Branch: `feature/deep-sleep-trial`, base main `80aab5d6`.

Only the keyboard deep-sleep enablement and inactivity timeout change on both halves: `CONFIG_ZMK_SLEEP=y`, `CONFIG_ZMK_IDLE_SLEEP_TIMEOUT=60000` (one minute). The existing 30-second idle state, Cirque sleep interval, pointer processing, keymap, DYA modules, and 2048-byte split stacks stay unchanged. No Settings RPC module, automatic settings reset, or bond clearing is added.

The key matrix already has `wakeup-source`. The local Cirque driver disables its data-ready interrupt during suspend, and the trackpad is not configured as a wake source. Touching the trackpad is therefore not the wake mechanism for this trial. Each sleeping half must be woken by a key on that half; a sleeping radio cannot receive a wake request from its peer.

## Test

1. Flash the left and right trial UF2s. Do not flash the settings-reset image. Confirm normal typing and both trackpads before testing sleep.
2. Disconnect USB from both halves and use battery/Bluetooth. Keep another input device available to observe the PC.
3. Leave all keys and both trackpads untouched for at least 90 seconds. The timer observes input, not BLE keepalives.
4. Press and release a key on the left, then a key on the right. Confirm reconnection and normal subsequent typing; note first-key loss, duplicated/stuck keys, and any noticeable delay. Repeat with the right woken first.
5. Check both trackpads and Fn behavior after wake. Repeat the sleep/wake cycle several times. A transient disconnected/unknown peer battery indication while the right is asleep is expected.
6. Confirm the left stays usable over USB. Deep sleep is blocked when ZMK's USB-power check detects power; the peripheral has no normal USB HID endpoint, so do not assume its USB-power detection behaves identically.

Behavioral checks establish usability, not exact low-current state or battery-life improvement. Confirming System OFF consumption and the remaining Cirque-board load requires current measurement or a longer controlled battery comparison. A loss of BLE alone also cannot distinguish sleep from a crash; successful key wake over repeated cycles strengthens the evidence.

The fork loads persisted `activity/s` timeouts, if present, over compiled defaults. If a unit does not sleep on this test, inspect stored activity settings/logs rather than clearing all keyboard settings. No sleep-timeout edits have been intentionally made via the currently enabled DYA modules.

After hardware acceptance, use a separate build with a normal timeout (proposed 30 minutes) before main integration. Do not merge the one-minute trial into main.

Build/artifact checks and real-device acceptance pending.
