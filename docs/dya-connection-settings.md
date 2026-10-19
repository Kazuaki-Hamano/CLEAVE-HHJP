# DYA connection and settings trial

Branch: `feature/dya-connection-settings`, based on main `95fdb6e5`.

Scope: BLE profile listing, names, active profile and output preference via BLE Management, plus activity settings (idle/sleep timeout API) via Settings RPC. The settings event handlers are enabled on both halves so the right can report/apply relayed activity settings. No keymap, wiring, pointer processing, default layer, OS detection, or idle/sleep default changes are introduced. The existing 2048-byte split workers are retained.

Dependencies are commit-pinned in `config/west.yml`. References: https://github.com/cormoran/zmk-config-dya-studio-sample/pull/6 and https://github.com/cormoran/zmk-config-dya-studio-sample/pull/7. Only BLE Management is adopted from the connection sample; OS/default-layer modules are deferred.

This exposes the existing activity API; it does not enable deep sleep when `CONFIG_ZMK_SLEEP` is disabled. Custom Cirque controls still use the existing Windows app/HID interface and are not yet registered as DYA custom settings.

## Acceptance

1. Build all three targets; inspect actual left/right Kconfig, UF2 identities/HID, existing keymap, split roles and stack sizes.
2. Flash left and right trial images, without settings reset; confirm split reconnection and existing input.
3. In DYA Connection, read profiles/status and output preference. Set a reversible profile label, reconnect and confirm it is retained. Optional switching should target an already paired device; removing a bond is not needed for acceptance.
4. In DYA Settings, read both halves' activity values. Record original values, change idle timeout to a valid nearby value, confirm both halves report it, reconnect/power-cycle and verify persistence, then restore the original value.
5. Check both trackpads and the Windows battery/settings app. Do not merge before hardware confirmation.

Build/artifact and hardware validation pending. Main is unchanged by this trial.
