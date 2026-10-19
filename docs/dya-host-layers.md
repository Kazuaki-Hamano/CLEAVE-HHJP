# DYA host and OS layers

Trial branch: `feature/dya-host-layers`. Main contains the accepted diagnostics,
but this host-layer feature stays separate until hardware acceptance.

## Behavior

Central (left) only: USB / BLE profile 1-5 default-layer mappings, per-OS mappings,
USB enumeration OS fingerprinting and passive BLE discovery fingerprinting.
All mappings initially unset, so the existing Default/Fn behavior is retained.
No Windows/macOS key bindings are guessed or installed by this trial.

OS guesses are heuristic, not an authoritative OS identity. Upstream has USB capture checks for several systems, but BLE cannot reliably
distinguish Windows/Linux or iOS/macOS. BLE manual OS override and fixed endpoint
layers are available when a guess is wrong. Additional
GATT client probing and the OS module's separate auto-layer controller are disabled.
There is one USB mapping, shared by USB hosts; BLE mappings are per pairing slot.

Four disabled, transparent host slots reserve layer capacity (six total). They do
not change active layers, Default ID 0, Fn ID 1 or saved binding IDs. Studio can
add them, customize them and persist their order. Reorder Fn ABOVE every host
layer so full host bindings cannot override Fn. Existing Fn bindings refer to
stable ID 1 and continue to work after reordering. Assign connection/OS mappings
AFTER setting the final layer order: upstream mappings store indices, not IDs.
Revisit mappings after later layer reordering/deletion.

## DYA procedure

1. Flash both halves without a settings reset, reconnect DYA Studio and open
   Connection. USB/BLE rows now expose a default-layer selector, OS information
   and BLE OS override. The Per-OS Default Layers section selects OS mappings.
2. Initially leave every default layer unset; confirm current typing, Fn,
   both trackpads, sleep/wake and USB/BLE switching still work.
3. For a reversible switching test, add one reserved layer in Keymap. It starts
   transparent and inherits Default. Give it a clear name (e.g. Test Host), change
   one harmless key, and move Fn above it. Save the keymap before mapping it.
4. Assign the test layer to one BLE profile or USB. Do not assign Fn as a default
   typing layer. Select Default/unset on another endpoint. Switch endpoints and
   verify the test key follows the endpoint; confirm Fn works on both.
5. To test OS selection, set the chosen endpoint to Follow OS detection and map
   its detected OS to the test layer. For BLE, manual OS override permits a
   controlled test if automatic detection is inaccurate. Restore Auto afterwards.
6. Reboot the left half, reconnect and confirm mappings, layer order and bindings
   persist. Revert endpoint/OS selectors to unset and remove the test layer if
   desired; the original Default/Fn remains usable.

RPC rejects mappings to slots not yet added in Keymap. Selectors report only
currently active layers; add/save the layer first. Invalid or deleted mapped
targets fall back to the global default at apply time. Only the previously managed
host layer is released, so an unrelated held Fn is not cleared by OS/settings
notifications. Core layer ordering still determines binding priority.

## Source and validation

OS detection: cormoran/zmk-feature-os-detection at
`3052679f645b8fc1997275c2eaa6b86bdd55ca01`.
Default layer: vendored cormoran/zmk-feature-default-layer at
`ef1f5b61b14e4f78172d3b6590afb3a39412fafe`, with local Fn preservation,
stable managed-layer IDs and unadded-slot rejection. MIT licenses retained.

`python tools/dya-studio/test_host_layers.py` compiles the actual application and
validation functions with a keymap mock and checks held Fn, endpoint/OS repeated
apply, host-to-host/default changes, reordering, invalid targets and activation
failure. Passing this test does not establish hardware or browser behavior.
Build, artifact and hardware acceptance details will be recorded below.

## Trial artifacts

Source `ea0c00bf`, firmware identity `3d6b3335`, Actions run
`39321937979`: UF2s at `output/firmware/ea0c00bf/`.
UF2 integrity/HID, actual merged configs/DTS, central-only OS/default-layer RPC,
USB/BLE detection, disabled probing/test/competing controller, four disabled
70-position capacity slots, unchanged Default/Fn bindings and prior sleep,
trackpad, split status, durable settings sync, diagnostics and watchdog checks
all passed. Left GNU build-id: `b5635776198700b41359d18486812286f504eb70`.
Production apply/validation/active-layer-count unit checks passed.
Actual DYA display, per-endpoint/OS switching, persisted mappings and Fn priority
still require the user's hardware check. Main does not include this trial.
