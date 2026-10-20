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
