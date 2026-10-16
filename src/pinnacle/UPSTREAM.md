# Driver provenance

Based on petejohanson/cirque-input-module commit
`0de55f36bc720b5be3d8880dc856d4d78baf5214`:
https://github.com/petejohanson/cirque-input-module/tree/0de55f36bc720b5be3d8880dc856d4d78baf5214

Local changes: asynchronous runtime ADC sensitivity selection and recalibration,
serialized with the existing packet worker; bounded calibration/ERA polling.
SPI and the original movement/tap configuration remain unchanged.
Bindings and Kconfig are retained with this driver so Actions builds the reviewed
local source, rather than downloading an unpatched external module.
