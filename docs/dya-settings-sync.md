# Durable DYA activity settings synchronization trial

Branch `feature/dya-settings-sync`, from accepted main `669cf37d`.

## Scope and contract

The existing DYA activity Set operation changes idle/sleep timeouts on both halves; `settings.source` identifies reports, not an independent-half write target. This correction preserves that behavior. It does not copy left settings to right merely on boot or connection. Only an explicit Set operation creates a pending transaction. Trackpad tuning remains central-only and outside this feature.

The central first persists the latest desired pair plus a monotonic transaction sequence under `cleave_sync/activity`, then applies and synchronously saves local `activity/s`. RPC success means durable local acceptance and queuing, not that an offline right has already saved. While pending, a low-priority worker checks actual split connectivity every five seconds and relays only to a connected right. Multiple changes coalesce to the latest pair. The pending transaction survives a central reboot. No pending transaction means no periodic work or automatic overwrite of independently loaded values.

The peripheral applies the pair and writes `activity/s` synchronously before reporting its transaction ID and effective values. The central clears pending only after matching source 1, sequence and both values, with a successful persistent outbox-clear write. Stale responses, ordinary read reports (transaction 0), save failures and disconnects cannot falsely complete delivery. The sequence is retained after completion/reset; it is never reused on reboot. Factory reset cancels pending through a registered Studio reset hook. Sequence overflow is rejected instead of wrapping.

The pinned ZMK activity/s ABI is two uint32 values, sleep then idle. The core's original delayed save may still run later and writes the same current data; this feature does not globally change the 60000ms debounce for unrelated settings. DYA activity Set and sync acknowledgement do not require a 70-second wait in this trial.

No input/activity-marking events or polling of the right are added. The worker does not wake an offline/sleeping right and does not reset the activity timer. It retries only while pending, including after reconnect, up to normal deep sleep/poweroff. If the left sleeps first, pending remains durable and retries resume after the left wakes. Disconnect supervision and the five-second retry can delay delivery after right power-on. Settings can disable/shorten sleep immediately, as before.

## Build integration

`modules/settings-rpc` snapshots the pinned module with license/provenance and replaces its west project. Root CMake/Kconfig includes it. Host RPC proto is unchanged. Private split changed/report events add a uint32 transaction ID: flash both halves together, without settings reset. Do not mix the old and new trial halves.

## Validation

`python tools/dya-studio/test_activity_sync.py` compiles production outbox, store and peripheral apply code with deterministic transport/NVS mocks. Tests cover disconnected queueing, latest-value coalescing, central reboot replay, failed local/outbox/right saves, stale/wrong-source/mismatched ACK rejection, persisted completion, no work after completion, reset and duplicate delivery. This is software evidence only, not hardware confirmation of flash timing or power consumption.

Build, artifact and hardware acceptance pending. Main is unchanged.

## Hardware acceptance

1. Flash both halves. Confirm normal typing, both pads and existing saved tuning. Use DYA Settings to note current idle/sleep timeouts.
2. Turn right OFF. Change a timeout to an easily recognizable, comfortably long value (for example sleep 20 minutes), and save/apply. The left should update without requiring right availability.
3. Turn right ON, wait roughly 5-10 seconds after split reconnection and refresh DYA Settings. Check that right reports the changed value and normal input still works.
4. Power cycle both without a 70-second wait after delivery, and verify values persist. Separately, queue another change while right is OFF, restart left before right, then power right ON and check delivery. Avoid many rapid trial writes.
5. Restore preferred timeouts and confirm one normal deep-sleep/own-side-key-wake cycle. Confirm later reconnects do not unexpectedly reset settings once the transaction is acknowledged.
