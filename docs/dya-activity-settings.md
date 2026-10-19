# DYA activity settings trial

Branch `feature/dya-activity-settings`, based on the accepted key-wake deep-sleep implementation and normal 30-minute timeout build. Main is unchanged pending hardware testing.

The inspected Settings RPC module is pinned to `78f86df9e6c5edaf57bef3ccbd7f360cfdf49291`. Both halves have `CONFIG_ZMK_SETTINGS_RPC=y`; only the left central exposes `CONFIG_ZMK_SETTINGS_RPC_STUDIO=y`. Deep sleep is compiled in on both halves, removing the previously identified save failure when `zmk_activity_set_sleep_ms()` returned false with sleep disabled. No vendor module patch is needed for this sleep-enabled configuration.

The module reads central/peripheral idle and sleep durations, changes them on the central and relays changes to the right. The pinned ZMK persists `activity/s` (sleep_ms followed by idle_ms) and restores it at startup. Compiled defaults remain idle 30 seconds and deep sleep 30 minutes. A saved value overrides compiled defaults after a normal flash. Sleep timeout 0 disables automatic deep sleep in the pinned activity implementation while leaving the compiled support available.

## Persistence and limitations

The existing settings-save debounce is 60000ms on both halves. RPC success means the runtime update was accepted, not that flash storage has already finished. Keep both halves awake and powered for at least 70 seconds after the last change before testing persistence. Activity settings can shorten an already-running idle timer, so use a sufficiently long test duration and keep both halves active while waiting for storage. The existing Windows trackpad save operation uses its own immediate-save path and is unchanged.

Changes are relayed to a connected right half; this module does not itself guarantee delivery/replay to an offline or sleeping peripheral or return a per-half durable-write acknowledgement. Keep the right awake while changing settings and verify both reported values. Do not assume a central success response means an offline right half changed. No reconnect-sync or offline-setting migration is added in this trial.

## Hardware checks

1. Flash both trial UF2s without resetting settings. Confirm typing, pads, split connection and DYA Connection still work.
2. Open DYA Settings with the left on USB and the right awake. Read the idle/deep-sleep values for both halves.
3. Change to a reversible deep-sleep duration, e.g. 5 minutes, keeping idle at 30 seconds. Confirm both halves report the new values.
4. Keep both halves awake for at least 70 seconds after the last change, then power cycle both. Reconnect DYA and verify both retained the duration.
5. With both on battery, check sleep and own-side key wake using the chosen duration. Restore 30 minutes for ordinary use if desired, allowing the same save interval.

Trial source `31d417b0`, matching left/right identity `13dc8a55`. Three UF2s were generated in run https://github.com/Kazuaki-Hamano/CLEAVE-HHJP/actions/runs/39279771579 and integrity/family/identity checked. Left keyboard/mouse/battery/charging/update HID signatures passed. Both firmware images contain the activity persistence key, change/report/request relay events, and exactly one compiled sleep/idle defaults pair (1800000/30000ms). The left includes the `zmk__settings` RPC registration.

Right complete job logs confirm `CONFIG_ZMK_SETTINGS_RPC=y` and `CONFIG_ZMK_SETTINGS_SAVE_DEBOUNCE=60000`. Left merged-configuration logs and run-level exports remained unavailable (404), with metadata stuck queued despite generated artifacts; the full merged-config verification is not claimed complete. `build-logs.zip` contains only the right log and a provenance note. `activity-binary-verification.json` explicitly records the remaining left-log check.

Verified copies of the artifacts and checksums are at `V:/Projects/CLEAVE-HHJP/output/firmware/31d417b0/`. No firmware or settings reset was written by the assistant. Real-device DYA reads/writes, split reflection, persistence, and selected-duration sleep/wake remain for hardware acceptance. Main remains unchanged.
