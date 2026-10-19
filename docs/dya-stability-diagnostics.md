# DYA stability and stack diagnostics trial

Branch `feature/dya-stability-diagnostics`, based on accepted main `1b931a46`.

## Features and limits

Both halves record fatal errors and software task-watchdog freezes. The existing DYA Stability/Watchdog card can query local (Central) or right-side (Peripheral 1) history through the left. Maximum stored incidents is 16 per half; a full log stops recording until entries are deleted rather than continually overwriting flash. The module stages fatal/freeze details in retained no-init RAM and attempts to persist them after reboot; a full power loss before conversion can lose the pending record. Enabling diagnostics is not proof that freezes can never occur or all failures can be recovered.

Freeze monitoring covers the system and ZMK low-priority work queues. It does not monitor every thread, nor a hard CPU lockup that prevents the software timer interrupt itself from running. The detector starts 30000ms after boot, uses a 30000ms timeout and feeds each monitored queue every 15000ms. This is deliberately less frequent than the module's defaults: upstream documents sensitivity of nRF BLE controller timing to extra timers, particularly during startup. The delay and longer period reduce timer load but do not establish hardware stability; normal-use and sleep/wake checks remain necessary.

No hardware watchdog/fallback is armed: TASK_WDT_HW_FALLBACK=n and the module calls task_wdt_init(NULL). This preserves the module's software-only design and avoids its documented nRF hardware-watchdog soft-reset/clock-startup failure mode. Fatal error handling records details and reboots; the reviewed application/local modules have no competing k_sys_fatal_error_handler override. Intentional fault injection and all boot self-tests are disabled. No deliberate crash/freeze is needed for the user acceptance check.

The module audits and clears chip reset-cause bits at boot to avoid duplicate incidents. The earlier Device Info card reads those live bits, so after the audit its reset-cause row may be empty/zero; relevant unexpected causes are instead recorded in Stability. Normal pin/power-on resets are not incidents. There is no intentional change to keys, pads, settings sync or BLE profiles.

Stack usage is central-only: devtool's GetStackUsage enumerates left threads and returns allocated size and peak/high-water usage since thread creation, measured from painted unused stack bytes. It is not instantaneous usage, a memory-leak detector, or a report of right-side stacks. Readings can be unavailable for some threads. The UI can poll while watched; firmware has no stack polling loop. THREAD_MONITOR/THREAD_STACK_INFO/THREAD_NAME/INIT_STACKS add bookkeeping/startup cost and are enabled only on the left.

Key injection, event tap, log capture and layer-control RPC feature flags are disabled. The devtool's base status/reboot APIs remain part of the upstream module, but are not needed for these checks. No fault-injection APIs are enabled. Existing device/key diagnostics remain enabled.

## Pinned dependencies

- zmk-feature-watchdog `84ad14c6c3645dc40b23f45d08ab45418655f912`
- zmk-module-devtool `9938a2c73c06d6e65ba2c0b68c9aa044a467eafc`

Reviewed DYA source `fa5f4ef55422f7f0806b28fc4d9da4ba41297400`: public watchdog GetStatus/List/Delete and PeripheralResponse contracts are retained. New injection fields are unused/disabled. Internal streamed split incident chunks are reassembled by the firmware central into the existing host response. Devtool stack changes are comments only; field numbers/types match. No frontend fork is added.

The current reusable build exports UF2s, not matching ELF files. Fatal PC/LR addresses can be recorded/reported, but this trial does not supply an ELF for DYA symbol/source-line resolution. That optional artifact export can be added separately.

## Validation

Source `fa4c082c`, firmware ID `1cd934eb`, Actions run `39319415474`, artifacts `output/firmware/fa4c082c/`. UF2 integrity/HID, actual merged configuration/DTS, conservative watchdog timing, software-only fallback setting, disabled test/development flags, central-only stack RPC/instrumentation, both-half watchdog relay, prior diagnostic modules, settings sync, trackpad tuning, sleep defaults and keymap checks passed. Left GNU build-id is `c4668804335dcb556de7207b09d08a353d2b1fd8`.

Static linker RAM allocation: left 153656/262144 bytes (58.62%), right 96828/262144 (36.94%). This is not runtime stack headroom. Module-source review confirms fatal handling records to pending RAM before reboot and does not attempt an ISR/fault-context flash write. No deliberate failure/reboot was triggered by the assistant. Actual screen display, right-side history query, monitored normal-use stability and sleep/wake acceptance remain pending. Main unchanged.

## Hardware acceptance

1. Flash both UF2s without settings reset. Use normally for at least a minute after boot so the delayed watchdog is armed; confirm normal typing, pads and BLE stay stable.
2. In DYA Diagnostics expand Stability/Watchdog. Check Central and Peripheral 1 can be read while right is awake. An empty incident list is expected on a healthy unit, not a reason to deliberately induce a fault.
3. Expand Stack Usage, refresh after normal use and confirm thread names, allocated sizes and usage/percentages appear. Refresh after opening key diagnostics and editing a reversible setting to observe the high-water marks. Report any very small remaining headroom rather than automatically shrinking stacks.
4. Copy the support report and confirm watchdog status is included. The current DYA support-report builder does not include stack usage, so retain a screenshot separately if needed.
5. Check both halves can still deep-sleep and wake with their own keys. Restore preferred timeouts after any short-duration sleep test. Leave incident records intact if an unexpected reboot occurs, so its cause can be inspected.
