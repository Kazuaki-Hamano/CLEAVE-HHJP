# DYA diagnostics: device information and key switches

Branch `feature/dya-diagnostics`, based on accepted main `499d398c`.

## Scope

This stage enables the existing DYA Troubleshooting/?? page's Device Info and Key Switches sections. Device Info reads the connected left/central build versions, GNU build-id, board, hardware ID, reset cause, flash/RAM capacity, compile-time configuration, uptime and initialized Zephyr devices. It is local information, not a report of the right half's reset cause or uptime. Build version fields are reported as available from the actual build environment; config revision may be absent if the workflow copies the config outside a Git checkout. GNU build-id identifies the linked image independently.

Key-switch diagnostics collects logical position press/release counts and timing information and exposes matrix topology. Both halves include the module so right-side topology can be queried through the left. These counters are RAM-only and restart on boot (or Reset Stats). They are post-kscan logical events, not an oscilloscope/raw electrical-contact capture; chatter indications are diagnostic hints rather than proof of a physical fault. No counters are written to flash per key.

The PMW3610 sensor diagnostics does not apply to the installed Cirque Pinnacle pads. Watchdog incident logging and devtool stack sampling are separate follow-up stages; neither module is enabled here. This firmware does not add a new frontend or represent those sections as supported.

## Dependencies and configuration

Pinned module revisions:

- zmk-feature-device-info `8cedd2dd9f04e19ea5a17b94914dd47a09d8db11`
- zmk-feature-kscan-diagnostics `1432f7fe0cfe903cd7d3c9931ae6bd6f2e1f328e`

Device-info RPC and key-diagnostic Studio RPC are central-only. Key-diagnostic collectors and split relay are enabled on both halves, with 70 position slots matching the current physical layout and a dedicated 4096-byte relay thread. The existing split payload limit of 240 is retained: the module's actual relay reply struct is 195 bytes and its build-time assertion checks the limit (its README recommends 256 for smaller defaults). Existing 2048-byte split transport stacks and 4096-byte low-priority/system stacks are unchanged.

Read access follows the keyboard's existing unlocked Studio configuration: DEVICE_INFO_STUDIO_RPC_REQUIRE_UNLOCK=n and KSCAN_DIAGNOSTICS_STUDIO_RPC_UNSECURED=y. HWINFO was already enabled in the prior firmware and is checked again in the merged config. The device-info module adds a GNU build-id flash note, which is checked in the actual UF2.

No keyboard keymap, sensor driver, activity settings, pending settings outbox, BLE profiles or battery/update HID behavior is changed. Passive counter listeners do not generate input/activity events or periodic traffic. Right-side queries run only when requested; no periodic wake request is added.

## Verification

Build/artifact and hardware checks pending. Main unchanged.

## Hardware acceptance

1. Flash both trial UF2s without settings reset. Check normal keys, right cursor, left scroll and saved tuning/timeouts.
2. Open DYA's ?? tab and expand Device Info/??????. Confirm build/hardware/runtime data loads and uptime changes after Refresh. Note any actual named device reported not ready rather than assuming the card itself is broken.
3. Expand Key Switches/??????. Confirm topology/statistics load; press a few distinct keys on each half, refresh statistics and check their counts/positions. Confirm right-side topology can be retrieved while the right is awake.
4. Use Copy Support Report and check it contains device info and kscan data. No fabricated watchdog/PMW3610 results should appear.
5. Leave the diagnostics idle/close the page and confirm normal sleep/wake remains usable. After restart, counters should begin again while saved keyboard settings remain.
