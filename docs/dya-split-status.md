# DYA split status RPC correction

Branch `feature/dya-split-status`, based on main `b5d2f9c6` (accepted DYA trackpad settings).

## Scope

The pinned BLE management module returned `peripheral_connected=false` on the central regardless of the actual connection. GetSplitInfo now queries the registered central split transports on each request and returns true only when a transport is available, enabled and reports SOME_CONNECTED or ALL_CONNECTED. CLEAVE has one BLE peripheral and no wired transport, so this represents the right half. It is not a host-PC BLE connection, battery freshness or bonding inference. No source means disconnected. Existing peripheral-role `central_bonded` semantics and non-split fields are unchanged.

This corrects the RPC data for future clients. The inspected DYA Studio source `fa5f4ef55422f7f0806b28fc4d9da4ba41297400` does not render GetSplitInfo in its Connection page, so this firmware does not add a new DYA display. There is no notification or polling added; clients must request status again to refresh it. Link loss can take the BLE supervision timeout to be detected.

## Local dependency

The six required build/license files from cormoran/zmk-module-ble-management `57738cc4fc6ba80e82a7ac57741a0339cb186cd4` are snapshotted under `modules/ble-management`, with provenance in UPSTREAM.md. Root CMake and Kconfig include them directly and the former west dependency is removed, avoiding duplicate subsystem registration. The protobuf contract is unchanged. The handler change only replaces the central constant with the on-demand helper. The original profile/output/bond code is retained; no callback is replaced and no periodic work can inhibit sleep.

## Validation

`python tools/dya-studio/test_split_status.py` compiles the actual production helper and actual GetSplitInfo handler with transport mocks for central, peripheral and non-split roles. It checks absent APIs, disconnect/connect/reconnect transitions, unavailable/disabled transports, unknown status values and unchanged role/bond fields. It does not prove real BLE transitions.

Firmware build/artifact checks pending. Hardware verification pending. Main does not include this correction yet.

## Hardware acceptance

1. Flash both trial UF2s without settings reset. Check normal typing, both pads and saved trackpad settings.
2. A GetSplitInfo client should report disconnected with the right powered off, connected after right reconnection, and disconnected after right power-off is detected. Repeat reconnect and a deep-sleep/own-side-key-wake cycle.
3. The original BLE management Web UI at https://cormoran.github.io/zmk-module-ble-management/ has a Split Keyboard card with Peripheral Status and a Refresh button in its source. If that published UI is usable, disconnect DYA first, connect the left over serial there, and use Refresh after each transition. Only the status query is needed; Reset Split Connection clears bonds and is not part of this test. Published UI compatibility has not been hardware verified.
