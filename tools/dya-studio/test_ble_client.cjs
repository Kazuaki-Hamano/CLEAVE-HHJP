// Usage: node test_ble_client.cjs <client checkout> <test dependency prefix>
// Dependencies: typescript and async-mutex. Tests run actual upstream/patched TS.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const [root, deps] = process.argv.slice(2).map(p => path.resolve(p));
const ts = require(path.join(deps, 'node_modules/typescript'));
const mutex = require(path.join(deps, 'node_modules/async-mutex'));
function source(file, patched) {
  return patched ? fs.readFileSync(path.join(root, file), 'utf8') :
    execFileSync('git', ['-C', root, 'show', '39083858775d320018716e3d8fd68d00f6d11118:' + file], { encoding: 'utf8' });
}
function load(code, navigator) {
  const module = { exports: {} };
  const js = ts.transpileModule(code, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
  }}).outputText;
  vm.runInNewContext(js, {
    module, exports: module.exports, navigator, console, Uint8Array, DOMException, setTimeout, clearTimeout,
    ReadableStream, WritableStream, TransformStream, AbortController,
    require: name => name === 'async-mutex' ? mutex : {},
  });
  return module.exports;
}
async function rpcChecks(patched) {
  const api = load(source('src/index.ts', patched));
  for (const failed of ['write', 'read']) {
    const error = new Error('original ' + failed + ' failure');
    const conn = {
      current_request: 0,
      request_writable: new WritableStream({ write() { if (failed === 'write') throw error; } }),
      request_response_readable: new ReadableStream({ start(c) { c.error(error); } }),
    };
    await assert.rejects(api.call_rpc(conn, {}), e => e === error);
    const leaked = failed === 'write' ? conn.request_writable.locked : conn.request_response_readable.locked;
    assert.equal(leaked, !patched);
    if (failed === 'write') {
      await assert.rejects(api.call_rpc(conn, {}), e => patched ? e === error : /locked/i.test(e.message));
    }
  }
  let responses;
  const ids = [];
  const conn = {
    current_request: 0,
    request_response_readable: new ReadableStream({ start(c) { responses = c; } }),
    request_writable: new WritableStream({ write(req) { ids.push(req.requestId); responses.enqueue({ requestId: req.requestId }); } }),
  };
  await Promise.all(Array.from({ length: 10 }, () => api.call_rpc(conn, {})));
  assert.deepEqual(ids, Array.from({ length: 10 }, (_, i) => i));
  assert.equal(conn.request_writable.locked, false);
  assert.equal(conn.request_response_readable.locked, false);
  console.log(patched ? 'PATCHED RPC: error locks released; original errors retained; concurrent calls serialized: PASS' :
    'UPSTREAM RPC: identical locked-stream error reproduced after failed write; read lock leak reproduced');
}
async function gattCheck(patched, bluefy) {
  const writes = [];
  const char = {
    properties: { writeWithoutResponse: true },
    async stopNotifications() {}, async startNotifications() {},
    addEventListener() {}, removeEventListener() {},
    async writeValueWithoutResponse(bytes) {
      if (bytes.length > 20) throw new Error('simulated 20-byte ATT payload limit');
      writes.push(...bytes);
    },
    async writeValue(bytes) {
      assert.ok(bytes.length <= 20); writes.push(...bytes);
    },
  };
  let disconnected;
  const dev = {
    name: 'test keyboard',
    addEventListener(name, cb) { if (name === 'gattserverdisconnected') disconnected = cb; },
    removeEventListener() {},
    gatt: { connected: true, async getPrimaryService() { return { async getCharacteristic() { return char; } }; },
      disconnect() { disconnected?.(); } },
  };
  const api = load(source('src/transport/gatt.ts', patched), {
    userAgent: bluefy ? 'Bluefy' : 'Chrome', bluetooth: { async requestDevice() { return dev; } },
  });
  const transport = await api.connect();
  const writer = transport.writable.getWriter();
  const bytes = Uint8Array.from({ length: 65 }, (_, i) => i);
  try {
    if (!patched && !bluefy) {
      await assert.rejects(writer.write(bytes), /ATT payload limit/);
      console.log('UPSTREAM BLE: non-Bluefy write-without-response exceeds simulated MTU: reproduced');
    } else {
      await writer.write(bytes);
      assert.deepEqual(writes, Array.from(bytes));
      console.log(`${patched ? 'PATCHED' : 'UPSTREAM'} BLE ${bluefy ? 'Bluefy' : 'Chrome'}: split payload / byte order: PASS`);
    }
  } finally { writer.releaseLock(); transport.abortController.abort(); }
}
async function lifecycleCheck() {
  const events = [];
  const char = {
    properties: {},
    async stopNotifications() { events.push('stop'); },
    async startNotifications() { events.push('start'); },
    addEventListener() {}, removeEventListener() {},
  };
  const dev = {
    name: 'test', addEventListener() {}, removeEventListener() {},
    gatt: { connected: true,
      async getPrimaryService() { return { async getCharacteristic() { return char; } }; },
      disconnect() { events.push('disconnect'); },
    },
  };
  const api = load(source('src/transport/gatt.ts', true), {
    userAgent: 'Chrome', bluetooth: { async requestDevice() { return dev; } },
  });
  const transport = await api.connect();
  await new Promise(resolve => setTimeout(resolve, 0));
  events.length = 0;
  transport.abortController.abort();
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.deepEqual(events, ['stop', 'disconnect']);
  dev.gatt.getPrimaryService = async () => { throw new Error('simulated failure'); };
  await assert.rejects(api.connect(), /BLE: Studio service discovery:.*simulated failure/);
  const code = source('src/index.ts', true);
  const body = code.match(/try \{\s*await byte_readable.cancel\(\);\s*\} finally \{\s*transport.abortController.abort\(reason\);\s*\}/)[0];
  let aborted = false;
  await assert.rejects(new Function('byte_readable', 'transport', 'reason',
    'return (async () => {' + body + '})()')(
    { cancel: async () => { throw new Error('cancel failure'); } },
    { abortController: { abort() { aborted = true; } } }, undefined), /cancel failure/);
  assert.equal(aborted, true);
  console.log('PATCHED lifecycle: unsubscribe before disconnect, stage errors, teardown despite cancellation failure: PASS');
}
(async () => {
  await lifecycleCheck();
  for (const patched of [false, true]) {
    await rpcChecks(patched);
    await gattCheck(patched, false);
    await gattCheck(patched, true);
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
