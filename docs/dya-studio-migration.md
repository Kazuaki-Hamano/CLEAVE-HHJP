# DYA Studio migration trial

## Isolation and scope

- Branch: `feature/dya-studio`.
- Base: `ab9b9c44` on `battery/peripheral-fetch`, including existing dual-trackpad and battery work. This is not based directly on the older `main`; review those inherited changes before eventual integration.
- Worktree: `V:/Projects/CLEAVE-HHJP-dya-studio`.
- Existing uncommitted assembly-guide and case changes remain in the original worktree.
- No firmware flashing, settings reset, release publication, or main merge is part of the build trial.

## Stage 1

Use the DYA custom RPC baseline plus keymap, macro, combo, pressed-key stream, and physical-layout modules. Upstream sample: https://github.com/cormoran/zmk-config-dya-studio-sample/pull/3 and /pull/4.

ZMK, Zephyr, and DYA feature modules are pinned to exact commits in `config/west.yml`. The CI reusable workflow uses the same ZMK commit. The XIAO target changes from `seeeduino_xiao_ble` to `xiao_ble//zmk` for Zephyr 4.1.

Both sides use explicit side-specific `.conf` files. Artifact inspection showed that the common `.conf` was not loaded for the right either, so the peripheral baseline is placed in `cleave_hhjp_right.conf`. No idle/sleep or save-debounce override is introduced; inspect the merged Kconfig rather than assuming the common file is active. Existing Cirque processing and the custom battery/trackpad HID interface remain the implementation for those functions; PMW3610 sample wiring and drivers are not imported.

DYA connection/OS controls, generic settings, diagnostics, and a Cirque settings adapter are deferred until the baseline passes actual device testing.

## Zephyr 4.1 compatibility

The new Zephyr includes its own Cirque driver and bindings. To retain CLEAVE's tested relative-mode driver (including native scroll, runtime sensitivity, and sleep interval), the local driver uses `cleave,pinnacle` / `CONFIG_CLEAVE_INPUT_PINNACLE`. This avoids both a duplicate devicetree binding and a Kconfig dependency cycle with Zephyr's `INPUT_PINNACLE`. The driver behavior and wiring are unchanged.

The RGB LED module is updated and commit-pinned for the new endpoint API and XIAO board name. The local input status callback includes Zephyr 4.1's new user-data argument. Both halves reserve a 4096-byte custom-settings worker stack.

## Acceptance before main integration

1. All matrix entries build: left central, right peripheral, and settings-reset image. Inspect merged Kconfig, devicetree, memory use, UF2 identifiers, and HID descriptors.
2. Preserve a copy of the currently working left/right firmware and saved key assignments before a user-directed flash. A Zephyr upgrade may change Bluetooth/settings behavior; do not assume saved state is compatible.
3. Flash the trial to both halves and confirm USB enumeration, split reconnection, and all key positions, including Fn tap/hold.
4. Connect DYA Studio over USB, inspect physical layout and all layers, then edit/save one reversible assignment and verify it survives reconnection and power cycling. Confirm official ZMK Studio compatibility separately.
5. Verify both trackpads, left Fn scrolling/navigation, right cursor movement, sensitivity application, idle wake, and existing Windows battery/settings application.
6. Verify macro/combo editing and execution, with saved-state persistence.
7. Review the full diff against main, including inherited battery branch changes; merge only after hardware acceptance.

## Validation status

Trial source commit: `203164f6`. Firmware identity: `692c95d6` on both halves.

CI: https://github.com/Kazuaki-Hamano/CLEAVE-HHJP/actions/runs/39252611959 ? all three matrix entries passed.

Artifacts: `output/firmware/203164f6/` in this worktree, with `checksums.json`, `dya-verification.json`, `keymap-verification.json`, and `build-logs.zip`.

Passed checks:

- UF2 block integrity/family, keyboard/mouse/battery/charging/update HID signatures, and existing central battery-fetch configuration.
- Actual merged DYA configuration on both halves, with the local Cirque driver enabled and Zephyr's competing driver disabled.
- Equal left/right update identities; settings-reset UF2 present.
- 70-key layout; INT5/Fn, INT4/Fn, Kana, 200ms hold-tap; Fn mouse buttons and the side-specific native-scroll settings.
- Existing actual-driver packet reporter and persisted trackpad storage migration tests.

Memory use: left Flash 338736 bytes (41.98%), RAM 139260 bytes (53.12%); right Flash 229060 bytes (28.39%), RAM 86784 bytes (33.11%).

Recheck artifacts with:

```powershell
python tools/battery/verify_firmware.py output/firmware/203164f6
python tools/dya-studio/verify_build.py output/firmware/203164f6
# Requires hidapi; use the existing battery build-env Python if needed.
python tools/battery/dev/verify_current.py output/firmware/203164f6
```

The upstream build still reports warnings (including deprecated KSCAN and DYA source warnings); build success does not establish runtime correctness. No firmware has been flashed, no settings reset has been performed, and no real-device DYA connection or runtime behavior has been verified. Main remains unchanged. Complete the hardware acceptance steps above before integration.
