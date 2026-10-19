# Driver provenance

Based on petejohanson/cirque-input-module commit
`0de55f36bc720b5be3d8880dc856d4d78baf5214`:
https://github.com/petejohanson/cirque-input-module/tree/0de55f36bc720b5be3d8880dc856d4d78baf5214

Local changes: asynchronous runtime ADC sensitivity selection and recalibration,
serialized with the existing packet worker; bounded calibration/ERA polling.
Relative packets are read as four bytes (Intellimouse is enabled). The optional
`native-scroll` property forwards the signed fourth byte as a vertical wheel
event, before the final synchronized Y event. Only the right half enables it.
SPI and the original movement/tap configuration remain unchanged.
Bindings and Kconfig are retained with this driver so Actions builds the reviewed
local source, rather than downloading an unpatched external module.

For Zephyr 4.1, local bindings use `cleave,pinnacle` and Kconfig uses
`CLEAVE_INPUT_PINNACLE` to avoid collisions with the new upstream driver.
