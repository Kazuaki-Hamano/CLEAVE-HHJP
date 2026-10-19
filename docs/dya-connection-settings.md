# DYA connection management trial

Branch: `feature/dya-connection-settings`, based on main `95fdb6e5`.

Scope: BLE profile listing/status, persistent profile labels, profile selection, and USB/BLE output preference through BLE Management. The existing split stack capacities remain 2048 bytes. No keymap, wiring, trackpad processing, OS detection, default layer, or idle/sleep changes are introduced.

The BLE module is commit-pinned in `config/west.yml`. Reference: https://github.com/cormoran/zmk-config-dya-studio-sample/pull/6. Only BLE Management is adopted from that sample; OS/default-layer modules are deferred.

## Why settings RPC is deferred

Source inspection found that zmk-module-settings-rpc `78f86df9e6c5edaf57bef3ccbd7f360cfdf49291` always calls both `zmk_activity_set_idle_ms()` and `zmk_activity_set_sleep_ms()` when saving. The pinned ZMK returns false from the latter when `CONFIG_ZMK_SLEEP` is disabled, as on this keyboard. The RPC then reports failure after already changing idle on the central, and suppresses relay to the peripheral. Do not ship that behavior or enable sleep merely to bypass it. The module was removed before the hardware trial. Activity-settings support needs a separate fix/implementation. TM040040 controls also remain on the existing Windows app/HID interface until a separate DYA adapter is implemented.

## Hardware acceptance

1. Build all three targets; inspect actual left/right Kconfig, UF2 identities/HID, existing keymap, split roles and stack sizes.
2. Flash left and right trial images without settings reset; confirm split reconnection and existing input.
3. In DYA Connection, inspect BLE profiles/status and output preference. Set a reversible profile label, reconnect and confirm it is retained after allowing the settings debounce to finish.
4. Optionally switch to an already paired host or change output preference and restore it. Removing host or split bonds is not needed for this test.
5. Check both trackpads and the Windows battery/settings app. Do not merge before hardware confirmation.

Build/artifact and hardware validation pending. Main is unchanged by this trial.
