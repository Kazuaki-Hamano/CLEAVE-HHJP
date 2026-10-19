# Deep-sleep hardware trial

Branch: `feature/deep-sleep-trial`, base main `80aab5d6`.

The keyboard deep-sleep enablement and inactivity timeout change on both halves: `CONFIG_ZMK_SLEEP=y`, `CONFIG_ZMK_IDLE_SLEEP_TIMEOUT=60000` (one minute). The existing 30-second idle state, Cirque sleep interval, pointer processing, keymap, DYA modules, and 2048-byte split stacks stay unchanged. No Settings RPC module, automatic settings reset, or bond clearing is added.

The key matrix already has `wakeup-source`. The local Cirque driver disables its data-ready interrupt during suspend, and the trackpad is not configured as a wake source. Touching the trackpad is therefore not the wake mechanism for this trial. Each sleeping half must be woken by a key on that half; a sleeping radio cannot receive a wake request from its peer.

## Required activity fix

The pinned ZMK activity callback treats every input event as activity. CLEAVE's one-second sensitivity status poll produces `INPUT_EV_MSC` replies on the central, so it would otherwise reset the idle timer indefinitely while the right is connected. With deep sleep enabled, polling is now performed only when the central detects USB power (charging or USB idle), where the USB settings app is available. Unknown/battery states skip the request and check power again after one second. Both ASICs already initialize to the fixed 1x sensitivity. Status freshness expires normally on battery; no stale acknowledgement is presented as current. Plugging in USB resumes polling and acknowledgement for the settings app. Pointer/key event handling is unchanged.

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

Source `daec4363`; matching firmware identity `b687fc98` on both halves.

CI https://github.com/Kazuaki-Hamano/CLEAVE-HHJP/actions/runs/39275774780 passed all three builds. Actual merged configuration confirms deep sleep, 60000ms timeout, device PM and poweroff on both halves; both generated devicetrees retain matrix `wakeup-source`. UF2/HID, split roles/stacks, DYA connection configuration and existing keymap checks passed.

The actual sensitivity poll was tested with deep sleep both disabled/enabled for all four power states: battery/unknown suppression only with sleep enabled, USB/charging requests, and periodic rescheduling passed. Existing actual packet reporter and saved-settings migration tests passed too.

Artifacts copied with byte-for-byte verification to `V:/Projects/CLEAVE-HHJP/output/firmware/daec4363/`, including checksums and build logs. Verification commands from the build worktree:

```powershell
python tools/battery/verify_firmware.py output/firmware/daec4363
python tools/dya-studio/verify_build.py output/firmware/daec4363 --stack-trial --connection --deep-sleep
python tools/battery/dev/verify_current.py output/firmware/daec4363
python tools/power/test_trackpad_sleep_poll.py
```

The user confirmed that both halves woke normally after the one-minute trial. This verifies the reported key-wake behavior on both halves. First-key delivery, exact current consumption and battery-life improvement were not reported separately. No firmware was flashed by the assistant.

## Normal-use timeout build

Following successful wake testing, both compiled sleep timeouts are changed from 60000ms to 1800000ms (30 minutes). No sleep/wake, trackpad-polling, keymap or BLE code changes accompany this timeout change. Source `687bbed3`, matching firmware identity `512905b2`, artifacts `V:/Projects/CLEAVE-HHJP/output/firmware/687bbed3/` (byte-for-byte verified copy). Left/right complete job logs confirm successful compilation and `CONFIG_ZMK_IDLE_SLEEP_TIMEOUT=1800000` on both halves. UF2 integrity/HID, existing keymap, matrix wake sources, PM/poweroff, DYA and split-stack configuration checks passed. The reset UF2 was also downloaded and integrity-checked. GitHub run 39278638880 metadata remained queued despite published artifacts and available left/right job logs; no overall CI-success claim is made. `build-logs.zip` is assembled from the unmodified left/right per-job logs, with provenance in README.txt.

Recheck the normal-use build with `python tools/dya-studio/verify_build.py output/firmware/687bbed3 --stack-trial --connection --deep-sleep --sleep-timeout-ms=1800000` plus the existing UF2/keymap verification scripts.

Main remains unchanged; normal-duration use and battery savings remain to be evaluated. The 30-minute build is ready for the user to flash on both halves without a settings reset.

## Integration acceptance

The subsequent DYA activity-settings trial includes this deep-sleep implementation. After key-wake acceptance on both halves, the user also accepted DYA setting changes and persistence. See [dya-activity-settings.md](dya-activity-settings.md) for final verification and integration evidence. Sleep defaults to 30 minutes unless overridden by saved DYA settings; battery savings remain unmeasured.
