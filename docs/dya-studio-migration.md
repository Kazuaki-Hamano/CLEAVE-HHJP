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

Implementation and CI validation are in progress. No real-device DYA connection or runtime behavior has been verified.
