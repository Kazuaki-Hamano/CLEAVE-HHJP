# Default layer snapshot

Upstream: https://github.com/cormoran/zmk-feature-default-layer
Revision: ef1f5b61b14e4f78172d3b6590afb3a39412fafe
MIT license retained. Build inputs, headers, protocol and source only.
Root CMake/Kconfig loads this snapshot instead of a west project.

Local change: track and release only the previously selected host layer by stable
layer ID, rather than sweeping an index range. Unrelated momentary layers (Fn)
remain active during OS detection, settings changes and endpoint transitions.
Invalid/deleted targets fall back to the global default layer.
RPC writes reject layer slots that have not been added to the keymap.
Endpoint and OS mappings remain stock unset defaults.
