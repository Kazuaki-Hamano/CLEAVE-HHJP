# Awake battery LED renderer

Source: https://github.com/caksoylar/zmk-rgbled-widget
Revision: e6b467792a1dabef8cfa5c9fd26bfefc9c16662b
File: src/widget.c. MIT license is retained in LICENSE.

Root CMake replaces exactly one upstream widget translation unit on the two
CLEAVE shields. The upstream Kconfig, RGB GPIO bindings, public behavior API,
startup battery/connection sequence and notification colors remain in use.
The settings_reset shield does not receive this replacement.

Local changes:
- After initialization, restore each half's own cached battery color after every
  notification. Use the same get_battery_color thresholds as the startup display.
- ACTIVE and IDLE both keep that color. SLEEP synchronously turns LEDs off before
  power management suspends devices; a sleep gate also suppresses queued blinks.
- Refresh the resting color on battery events, without extra ADC sampling/timers.
- Replace GPIO on/off output with hardware PWM1 on R/G/B pins P0.26/P0.30/P0.06.
  Disable the board's sample PWM0 on CHG P0.17 and the GPIO LED driver.
- Serialize PWM writes with a mutex; never hold it during blink delays.
- Notifications always use 100%; resting output reads the runtime brightness
  setting even when its color did not change. The setting defaults to 100%.
- brightness.c is local code: central DYA registration, preview/persist distinction,
  peripheral fallback storage, and acknowledged/retried split synchronization.
- Persistent layer colors are deliberately incompatible with this renderer.

The upstream zero-percent/unknown convention (magenta) is preserved; measured
80% and above is green, 20-79% yellow, and below 20% red. Battery estimates while
USB-powered/charging retain their existing measurement limitations.

`tools/dya-studio/test_led_settings.py` exercises registry and split synchronization
through the pinned relay macros and BLE receive callback. In the pinned transport,
central-to-peripheral raw source 0 becomes application source 1 after HANDLE;
the peripheral must accept that value rather than the macro comment's source-0 convention.
`tools/dya-studio/test_awake_led.py` compiles production renderer/state functions
with deterministic GPIO, queue and activity mocks, including sleep during a
blink and a saturated queue. On 2026-10-25, the user confirmed brightness changes
on both halves and saving with firmware 648c54f4 (embedded ID c94fa28a).
Reboot restoration and reconnect synchronization remain automated-test evidence;
battery consumption has not been measured. The C harness does not measure current.
