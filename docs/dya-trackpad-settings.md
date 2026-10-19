# DYA trackpad settings trial

Branch `feature/dya-trackpad-settings`, based on main `fd760238`.

## User-facing settings

Open the **Settings (??)** tab, scroll down and expand **Advanced Settings (????)**. Settings are loaded lazily only when this section is expanded. Find `cleave_right_trackpad` and `cleave_left_scroll` there; edit a value and save the affected section to persist it.

The **Trackball** tab requires the runtime-input-processor RPC and PMW3610-specific driver RPC, neither of which this Cirque adapter implements. Its "subsystem not found" / no-processor display does not diagnose the generic settings editor. The **Subsystems** tab lists our two registered namespaces but has no Web UI link because the adapter intentionally supplies none. Use Settings ? Advanced Settings rather than either of those tabs.

Verified against DYA Studio source `fa5f4ef55422f7f0806b28fc4d9da4ba41297400` (`SettingsPage.tsx`, `AdvancedSettingsSection.tsx`, `useCustomSettings.ts`). This confirms UI routing and the generic RPC contract; actual device listing/editing still requires hardware confirmation.

Custom settings are grouped by registered subsystem:

| Subsystem | Key | Default | Range | Applies to |
| --- | --- | --- | --- | --- |
| cleave_right_trackpad | speed_percent | 200 | 30-800 | Right cursor base speed |
| cleave_right_trackpad | acceleration_percent | 0 | 0-300 | Right cursor acceleration |
| cleave_right_trackpad | max_gain_percent | 300 | 100-800 | Right cursor acceleration gain cap, before base speed |
| cleave_right_trackpad | native_scroll_percent | 100 | 10-400 | Right ASIC wheel events only |
| cleave_left_scroll | scroll_percent | 100 | 10-400 | Left vertical and horizontal scrolling |

All values are integer percentages. Native-scroll amount is a separate right-side setting, not cursor speed. Left is always the dedicated 2D scroll pad, with Fn back/forward swipes unchanged. ASIC sensitivity stays fixed at 1x. The existing navigation threshold/direction and scrolling direction are not made configurable in this first stage.

The generic DYA Settings custom-setting editor is used; this does not add a PMW3610-specific Trackball panel or a new web frontend. Each scalar is range-constrained in the custom-settings registry, applied after a change, and restored after the registry initialization event on boot. Save/discard/reset semantics are provided by the existing custom-settings module. User-saved DYA values are the sole settings authority.

Right and left config generations are independent, so changing the left scroll amount does not reset right cursor/native-wheel fractions; changing right cursor tuning does not reset left scroll fractions. All processing happens on the central, including right input received over BLE; tuning therefore needs no new sensor-setting relay to the right.

## Retired Windows settings path

Per user request, the old Windows trackpad settings protocol is not supported. HID Feature Report 7, the legacy trackpad GATT read service, the legacy settings codec/namespace and periodic sensitivity request/status traffic are removed. Old `cleave_trackpad/config` flash entries are left untouched but ignored. Old Windows tuning is not imported: this version starts at the standard defaults above. Existing Windows battery, charging, voltage diagnostics and guarded firmware-update HID reports remain supported. Windows tools are retained as historical source; their trackpad settings UI is not a supported control for this firmware.

The old storage/polling tests are retired with that code. Processor tests retain checks for right cursor/left scrolling, Fn navigation, buttons and native-wheel fractions, and add cross-group edit-isolation checks. Matrix/keymap/wiring/deep-sleep defaults and DYA activity settings are unchanged.

## Hardware acceptance

1. Flash both trial UF2s without settings reset. Confirm right cursor, left 2D scroll, Fn swipes/mouse buttons and both battery indicators.
2. Find both custom-setting groups in DYA Settings; confirm the defaults and valid ranges.
3. Change right speed and confirm left scroll amount stays unchanged. Change left scroll amount and confirm right cursor speed stays unchanged. Test native-wheel amount separately only if that gesture produces ASIC wheel events.
4. Use DYA Save, reconnect and power cycle, and confirm saved values and actual motion persist. Also verify a memory-only edit followed by Discard and restore defaults using the relevant group scope if supported by the UI. Avoid global factory reset for this trial.
5. Confirm one idle/deep-sleep/own-side-key-wake cycle: the removed sensitivity polling must not prevent sleep. Check DYA Connection and the Windows battery/updater information still load; no actual boot command is needed.

Initial trial source commit `c876370e`; both UF2s report firmware ID `63390cea`. Artifacts: `output/firmware/c876370e/`, Actions run `39286178153`. UF2 integrity, actual merged Kconfig/Devicetree, central-only registry keys, retired Report 7, retained HID reports, split worker stacks, 30-minute deep sleep and keymap checks passed. Host tests passed for the production adapter event/cache behavior and independent pointer/scroll processing. `build-logs.zip` archives complete per-job logs with provenance. The user confirmed both groups are visible and live edits affect motion. Saving the right group failed; see the correction below. Main is unchanged.

## Save-error correction

The first trial registered `right_acceleration_percent` and `right_native_scroll_percent` under `cleave_right_trackpad`. With the `custom_settings/` storage prefix, their storage paths required 65 and 66 bytes including NUL, exceeding the pinned Zephyr `SETTINGS_MAX_NAME_LEN` of 64. The registry permits RAM writes but returns `-ENAMETOOLONG` during persistence, reported by DYA as "Failed to process request". Partial saves are possible: the other two right keys fit and may already be saved.

All five item names now omit the role prefix: `speed_percent`, `acceleration_percent`, `max_gain_percent`, `native_scroll_percent`, and `scroll_percent`. The existing group names still identify right and left. Storage paths require 50-60 bytes including NUL. A production `BUILD_ASSERT` checks every declaration against Zephyr's real limit, and a host regression reproduces the old truncation and proves the guard rejects it. Processing, defaults and ranges are unchanged.

On the first boot, the three old keys that could persist (`right_speed_percent`, `right_max_gain_percent`, `left_scroll_percent`) are migrated. An already saved new key takes precedence. An old key is removed only after a successful copy, preventing a later reset from resurrecting it. Failed copies retain the source for retry. The two oversized old keys could never persist; re-enter their values after flashing. This is separate from the intentionally unsupported legacy Windows settings blob.

Save-error fix and prefix removal source `405d4595`, firmware ID `db2f3d84`, Actions run `39295841308`, artifacts `output/firmware/405d4595/`. Both firmware builds and UF2/configuration/keymap checks passed, as did adapter migration and storage-name regression tests. Hardware save/power-cycle persistence confirmation remains pending.

## Hardware acceptance of save correction

The user confirmed successful saving with the corrected trial on 2026-10-20, after previously confirming both custom setting groups were visible and changes affected motion. This accepts integration of the trackpad trial. Power-cycle retention and individual battery/deep-sleep checks were not separately reported for the correction and are not claimed as newly verified.
