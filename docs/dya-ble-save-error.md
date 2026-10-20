# Bluetooth save: locked WritableStream

The user reported `Cannot create writer when WritableStream is locked` while
saving trackpad settings over BLE on 2026-10-20. No firmware changes are made.

## Evidence and scope

DYA source/remote HEAD is `fa5f4ef55422f7f0806b28fc4d9da4ba41297400`.
Its lockfile pins the client to `39083858775d320018716e3d8fd68d00f6d11118`
and React hook to `ceda0a4117078af35aed498c9b3afcb85cc68f62`.

Confirmed in that client: `call_rpc` releases its writer only after successful
`writer.write`. A rejection leaves the writer locked. A second RPC then throws
the same locked-stream error as the screenshot. The reader has the equivalent
leak after a read rejection. The process-wide RPC mutex does serialize ordinary
concurrent calls; concurrency alone is not the demonstrated cause.

Also confirmed: GATT's non-Bluefy write-without-response path sends an entire
chunk, while its fallback path splits into 20-byte payloads. A simulated 20-byte
ATT limit rejects a 65-byte write on the original fast path. This is a plausible
initial write failure, not a confirmed measurement of this user's negotiated MTU
or first exception. The screenshot shows the later lock error only.

The patch adds writer/reader release in `finally` and serial 20-byte chunks in
both BLE write paths. It preserves byte order and does not retry settings writes.
An errored stream still needs a reconnect; releasing the lock does not repair
an errored stream or prove an earlier save persisted.

Sources:
- https://github.com/cormoran/zmk-studio-ts-client/blob/39083858775d320018716e3d8fd68d00f6d11118/src/index.ts
- https://github.com/cormoran/zmk-studio-ts-client/blob/39083858775d320018716e3d8fd68d00f6d11118/src/transport/gatt.ts

## Regression proof

Install isolated test dependencies (`typescript@5.9.3`, `async-mutex@0.5.0`).
Apply `tools/dya-studio/patches/0001-ble-chunks-and-rpc-locks.patch` to a checkout
of the pinned client. Run:

```
node tools/dya-studio/test_ble_client.cjs <client checkout> <dependency prefix>
```

The test transpiles actual original and patched source and uses real Node Web
Streams with a deterministic GATT mock. Original write/read lock leaks and the
subsequent locked-stream error reproduce. Patched error paths release locks,
retain original errors, serialize ten concurrent calls, and preserve a 65-byte
payload through both Chrome-style and Bluefy-style 20-byte writes. All pass.
The tests do not establish physical BLE persistence or UI behavior.

Reviewed DYA specs: WRITE-002/005/006 and WRITE-I03/I05, SESSION-R01/R02.
The patch restores error cleanup and transport framing in an external dependency;
the intended DYA RAM-versus-flash/save UI contract is unchanged. DYA page source
and specifications were not modified. No upstream issue/PR or website update
was sent.

## Local trial

Canonical files: `V:/Projects/CLEAVE-HHJP/output/dya-studio-ble-fix/`.
The pinned DYA app was bundled with Vite after injecting transpiled patched
client runtime modules and the pinned React-hook runtime. Vite production build
passed; full app TypeScript typechecking was not performed. Provenance and the
patch are in that folder. The official site is unchanged.

`Start-DYA-Studio.cmd` starts a hidden Python static server bound only to
127.0.0.1:8766. The launcher records the PID and refuses to replace an existing
port owner. Open http://localhost:8766/ and use Fn+U / Bluetooth as before.
Entry HTML and its referenced production assets returned successfully; actual
browser rendering, BLE editing/save, and persistence remain user verification.

Use a fresh local session after any failed connection. Change one setting, wait
for the RAM write to finish, save its section and confirm the unsaved state
clears. Reconnect/read back; a later keyboard reboot/readback checks persistence.
The public site's prior error should not be treated as successful saving.
USB saving remains a workaround on the public site.

## Local startup correction

The user found a black screen after the first local delivery. The original
HTTP-200/asset checks did not establish browser startup. On this Windows system,
Python's generic server used the registry MIME mapping and returned the module
bundle as `text/plain`. Chrome displayed an empty root rather than running it.

`serve_ble_web.py` now explicitly serves `.js`/`.mjs` as `text/javascript`,
independently of registry mappings. Responses use `no-store`; conditional cache
headers are ignored so a prior cached wrong MIME response cannot produce a 304.
The launcher uses this server and still binds only to loopback. The old known
trial process was identified by PID/command line before replacing it.

The user-owned Chrome tab was reloaded and the Japanese DYA splash visibly
showed USB, BLE and Demo controls. No errors were captured by the browser log
API. Actual module Content-Type and a conditional request returning fresh HTTP
200 were checked. Screenshot: `output/dya-studio-ble-fix/startup-confirmed.png`.
Temporary startup error diagnostics were removed. BLE hardware saving remains
pending; this corrects the local delivery, not the public DYA website.


## Reconnect lifecycle trial (2026-10-20)

User confirmed: power cycle -> signal icon -> first connection/keymap succeeds;
DYA disconnect -> connected-Bluetooth icon -> reconnect hangs. This isolates a
reconnect-specific condition but does not establish which Windows/GATT/RPC stage
stalls. Firmware `b0c9f322` is still hardware-pending and remains unmerged.

Local client now explicitly awaits notification unsubscribe before releasing
GATT. RPC pipeline teardown always aborts its transport in a finally block even
if stream cancellation rejects. GATT connect, service/characteristic discovery,
notification stop/start have individual 15-second limits with named errors.
The user picker itself has no timeout. A timed-out browser operation cannot be
cancelled through Web Bluetooth; reload the page before another attempt.

Actual-source mock tests pass for unsubscribe-before-disconnect ordering,
stage-labelled service errors, and transport abort despite cancellation failure,
plus previous lock/framing regression tests. They do not prove Windows disconnect
behavior or hardware recovery. Public DYA is unchanged. Trial uses localhost:8766
with existing firmware; verify first connection, explicit disconnect/reconnect,
then settings save/readback. Record the displayed BLE stage if it fails.


## Service-discovery timeout follow-up

Hardware feedback: reconnect fails with `Studio service discovery timed out (15s)`.
The failure precedes characteristic discovery, subscription and Studio RPC.
Notification cleanup alone did not resolve it. The browser/UI icon does not prove
the JavaScript GATT object's `connected` state or establish firmware culpability.

Next local trial: if the selected browser GATT session is connected, release it
before connecting; always call connect before service discovery. Retain the
15-second stage bounds and include selected GATT state in failure details.
Tests cover connected-session release-before-connect and initially-disconnected
connect paths. This is a recovery trial, not a confirmed Windows fix. Firmware
remains b0c9f322 and no pairing reset is requested. Physical HID link teardown is
not guaranteed by browser disconnect; Windows may retain other clients' access.
