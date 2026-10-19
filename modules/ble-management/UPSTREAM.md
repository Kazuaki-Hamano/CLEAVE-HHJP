# BLE management module snapshot

Source: https://github.com/cormoran/zmk-module-ble-management
Revision: 57738cc4fc6ba80e82a7ac57741a0339cb186cd4
License: MIT (LICENSE retained).

Only build inputs are vendored. Root CMake/Kconfig includes this module directly,
replacing the former west dependency. Proto and existing RPC contracts are unchanged.
Local delta: central GetSplitInfo queries transport status through
include/cleave_split_status.h instead of always returning false. Both central
and peripheral role guards, profile/output/bond behavior remain upstream behavior.
No upstream callback is replaced and no periodic work is introduced.
