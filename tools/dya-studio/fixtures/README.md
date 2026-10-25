# Pinned GATT regression fixture

`gatt_rpc_transport.upstream.c` is an unmodified copy of
`app/src/studio/gatt_rpc_transport.c` from cormoran/zmk commit
`e5c9b6915b56801193e359dd9bad4a167ce0d1b8` (MIT, original header retained).
It is test input only, never a compiled firmware source. The production source
and local changes are described in `src/studio/UPSTREAM.md`.

The test extracts the actual original and patched functions and verifies ATT
payload bounds, byte order, and connection-reference cleanup. Keeping this small
fixture makes the test independent of disposable research checkouts in output/.

`event_manager.upstream.h`: cormoran/zmk at
`e5c9b6915b56801193e359dd9bad4a167ce0d1b8`,
`app/include/zmk/event_manager.h` (MIT header retained).
Used to compile the real relay sender/receiver macros in LED synchronization
tests, rather than mocking away the transport registration.

`split_bluetooth_service.upstream.c`: cormoran/zmk at
`e5c9b6915b56801193e359dd9bad4a167ce0d1b8`,
`app/src/split/bluetooth/service.c` (MIT header retained).
LED tests execute its central-to-peripheral receive callback: the transport
sets source 0, then the event HANDLE macro increments it to 1. Do not derive
raw source from the expected application source in the test harness.
