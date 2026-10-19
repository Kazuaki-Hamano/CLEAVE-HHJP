# DYA trackpad settings trial

Branch `feature/dya-trackpad-settings`, based on main `fd760238`.

## User-facing settings

In DYA Settings, custom settings are grouped by registered subsystem:

| Subsystem | Key | Default | Range | Applies to |
| --- | --- | --- | --- | --- |
| cleave_right_trackpad | right_speed_percent | 200 | 30-800 | Right cursor base speed |
| cleave_right_trackpad | right_acceleration_percent | 0 | 0-300 | Right cursor acceleration |
| cleave_right_trackpad | right_max_gain_percent | 300 | 100-800 | Right cursor acceleration gain cap, before base speed |
| cleave_right_trackpad | right_native_scroll_percent | 100 | 10-400 | Right ASIC wheel events only |
| cleave_left_scroll | left_scroll_percent | 100 | 10-400 | Left vertical and horizontal scrolling |

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

Source commit `c876370e`; both UF2s report firmware ID `63390cea`. Artifacts: `output/firmware/c876370e/`, Actions run `39286178153`. UF2 integrity, actual merged Kconfig/Devicetree, central-only registry keys, retired Report 7, retained HID reports, split worker stacks, 30-minute deep sleep and keymap checks passed. Host tests passed for the production adapter event/cache behavior and independent pointer/scroll processing. `build-logs.zip` archives complete per-job logs with provenance. Real-device DYA visibility/edit/save and motion verification remain pending. Main is unchanged.
