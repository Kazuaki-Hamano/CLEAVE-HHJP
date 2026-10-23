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
- Serialize GPIO writes with a mutex; never hold it during blink delays.
- Persistent layer colors are deliberately incompatible with this renderer.

The upstream zero-percent/unknown convention (magenta) is preserved; measured
80% and above is green, 20-79% yellow, and below 20% red. Battery estimates while
USB-powered/charging retain their existing measurement limitations.

`tools/dya-studio/test_awake_led.py` compiles production renderer/state functions
with deterministic GPIO, queue and activity mocks, including sleep during a
blink and a saturated queue. Hardware behavior and battery life need evaluation
after flashing; the C harness does not measure current consumption.
