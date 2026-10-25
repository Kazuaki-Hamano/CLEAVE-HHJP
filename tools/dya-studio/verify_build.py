"""Verify the downloaded DYA trial artifacts and actual merged configurations.

Usage: python tools/dya-studio/verify_build.py output/firmware/<commit>
Run the existing battery/verify_firmware.py for UF2 integrity and HID checks too.
"""
import json
from pathlib import Path
import re
import sys
import zipfile

root = Path(sys.argv[1])
sleep_timeout_ms = next((int(arg.split("=", 1)[1]) for arg in sys.argv[2:] if arg.startswith("--sleep-timeout-ms=")), 60000)
common = (
    "CONFIG_ZMK_SPLIT_RELAY_EVENT=y",
    "CONFIG_ZMK_SPLIT_RELAY_EVENT_DATA_LEN=240",
    "CONFIG_ZMK_CUSTOM_SETTINGS=y",
    "CONFIG_ZMK_CUSTOM_SETTINGS_SPLIT_RPC_RELAY=y",
    "CONFIG_CLEAVE_INPUT_PINNACLE=y",
    "CONFIG_ZMK_POINTING=y",
)
central = (
    "CONFIG_ZMK_STUDIO=y",
    "CONFIG_ZMK_FAST_KEYMAP=y",
    "CONFIG_ZMK_FAST_KEYMAP_STUDIO_RPC=y",
    "CONFIG_ZMK_FAST_KEYMAP_DEFAULT_LAYER=y",
    "CONFIG_ZMK_RUNTIME_MACRO=y",
    "CONFIG_ZMK_RUNTIME_MACRO_STUDIO_RPC=y",
    "CONFIG_ZMK_RUNTIME_COMBO=y",
    "CONFIG_ZMK_RUNTIME_COMBO_STUDIO_RPC=y",
    "CONFIG_ZMK_INPUT_STREAM_FEATURE_STUDIO_RPC=y",
    "CONFIG_ZMK_PHYSICAL_LAYOUTS_FEATURE_STUDIO_RPC=y",
    "CONFIG_ZMK_CUSTOM_SETTINGS_STUDIO_RPC=y",
    "CONFIG_USB_HID_DEVICE_COUNT=2",
)
identities = {}
with zipfile.ZipFile(root / "build-logs.zip") as logs:
    for side in ("left", "right"):
        config_entry = next(n for n in logs.namelist() if side in n and "Kconfig file" in n)
        config = logs.read(config_entry).decode()
        # Kconfig dumps contain settings; CMake messages and compiled object names
        # are in the separate West Build step log.
        build_entry = next(n for n in logs.namelist()
                           if side in n and "/" in n and "West Build (" in n)
        config += "\n" + logs.read(build_entry).decode()
        for setting in common + (central if side == "left" else ()):
            assert re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
        assert not re.search(r"(?m) CONFIG_INPUT_PINNACLE=y$", config), "Upstream driver must not replace CLEAVE driver"
        assert bool(re.search(r"(?m) CONFIG_ZMK_SPLIT_ROLE_CENTRAL=y$", config)) == (side == "left"), (side, "wrong split role")
        if side == "right":
            assert re.search(r"(?m) CONFIG_BT_MAX_CONN=1$", config), "Right must remain a single-link peripheral"
        stack_setting = "CONFIG_ZMK_SPLIT_BLE_CENTRAL_SPLIT_RUN_STACK_SIZE" if side == "left" else "CONFIG_ZMK_SPLIT_BLE_PERIPHERAL_STACK_SIZE"
        stack = int(re.search(r"(?m) " + stack_setting + r"=(\d+)$", config)[1])
        if "--stack-trial" in sys.argv:
            assert stack == 2048, (side, stack_setting, stack)
        print(side, "split worker stack:", stack)
        if "--ble-transport-fix" in sys.argv:
            assert ("CLEAVE Studio GATT override:" in config) == (side == "left"), (side, "transport replacement")
            objects = re.findall(r"Building C object [^\n]*gatt_rpc_transport[.]c[.]obj", config)
            assert len(objects) == (1 if side == "left" else 0), (side, "duplicate or missing GATT object", objects)
            print(side, "single role-correct patched GATT transport: PASS")
        if "--awake-led" in sys.argv:
            assert "CLEAVE awake battery LED override:" in config, (side, "missing LED override")
            objects = re.findall(r"Building C object [^\n]*status_led/widget[.]c[.]obj", config)
            assert len(objects) == 1, (side, "missing/duplicate awake LED renderer", objects)
            assert not re.search(r"Building C object [^\n]*zmk-rgbled-widget/src/widget[.]c[.]obj", config)
            for setting in ("CONFIG_RGBLED_WIDGET=y", "CONFIG_RGBLED_WIDGET_BATTERY_LEVEL_HIGH=80",
                            "CONFIG_RGBLED_WIDGET_BATTERY_LEVEL_LOW=20",
                            "CONFIG_RGBLED_WIDGET_BATTERY_COLOR_HIGH=2",
                            "CONFIG_RGBLED_WIDGET_BATTERY_COLOR_MEDIUM=3",
                            "CONFIG_RGBLED_WIDGET_BATTERY_COLOR_LOW=1"):
                assert re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
            print(side, "single awake LED renderer and startup battery thresholds: PASS")
        if "--pwm-led" in sys.argv:
            for setting in ("CONFIG_PWM=y", "CONFIG_LED_PWM=y"):
                assert re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
            assert len(re.findall(r"Building C object [^\n]*status_led/brightness[.]c[.]obj", config)) == 1
            entry = next(n for n in logs.namelist() if side in n and "Devicetree file" in n)
            led_dts = "\n".join(line.split("Z ", 1)[-1] for line in logs.read(entry).decode().splitlines())
            for label, status in (("pwm0", "disabled"), ("pwm1", "okay")):
                node = re.search(label + r": pwm@[^\s]+\s*\{(.*?)\};", led_dts, re.S)
                assert node and f'status = "{status}";' in node[1], (side, label)
            assert not re.search(r"(?m) CONFIG_LED_GPIO=y$", config), (side, "GPIO LED driver conflicts with PWM")
            assert not re.search(r"Building C object [^\n]*led_gpio[.]c[.]obj", config), (side, "GPIO LED driver compiled")
            assert re.search(r'\n\s*pwmleds\s*\{[^}]*status = "disabled";', led_dts)
            for channel, color in enumerate(("red", "green", "blue")):
                node = re.search(r"status_" + color + r": " + color + r"\s*\{(.*?)\};", led_dts, re.S)
                assert node and re.search(r"pwms = < &pwm1 0x" + str(channel) + r" 0xf4240 0x1 >;", node[1]), (side, color)
            pins = re.search(r"status_pwm_default:.*?psels = (.*?);", led_dts, re.S)
            assert pins and [int(x, 16) & 0x1ff for x in re.findall(r"0x[0-9a-f]+", pins[1])] == [26, 30, 6]
            print(side, "PWM1 RGB channels, 1kHz, polarity and CHG/GPIO isolation: PASS")
        if "--ble-discovery" in sys.argv:
            for setting in ("CONFIG_ZMK_STUDIO_TRANSPORT_BLE=y", "CONFIG_ZMK_STUDIO_TRANSPORT_UART=y"):
                assert bool(re.search(r"(?m) " + re.escape(setting) + r"$", config)) == (side == "left"), (side, setting)
            assert not re.search(r"(?m) CONFIG_ZMK_STUDIO_LOCK_BLE_DIRECT_ADVERTISING_ON_UNLOCK=y$", config), (side, "unbounded unlock advertising")
            if side == "left":
                assert "studio_ble_discovery.c" in config and "gatt_rpc_transport.c" in config
                dts_entry = next(n for n in logs.namelist() if side in n and "Devicetree file" in n)
                dts = "\n".join(line.split("Z ", 1)[-1] for line in logs.read(dts_entry).decode().splitlines())
                node = re.search(r"fn_layer\s*\{.*?bindings\s*=\s*<(.*?)>;", dts, re.S)
                bindings = [" ".join(x.split()) for x in re.findall(r"&[^&]+", node[1])]
                assert len(bindings) == 70 and bindings[41] == "&studio_ble", bindings[41]
                assert 'display-name = "Studio BLE Discovery";' in dts
            print(side, "USB/BLE transport and manual discovery config: PASS")
        if "--host-layers" in sys.argv:
            host_features = ("CONFIG_ZMK_OS_DETECTION=y", "CONFIG_ZMK_OS_DETECTION_STUDIO_RPC=y", "CONFIG_ZMK_OS_DETECTION_USB=y", "CONFIG_ZMK_OS_DETECTION_BLE=y", "CONFIG_ZMK_DEFAULT_LAYER=y", "CONFIG_ZMK_DEFAULT_LAYER_STUDIO_RPC=y", "CONFIG_ZMK_DEFAULT_LAYER_OS_DETECTION=y")
            for setting in host_features:
                assert bool(re.search(r"(?m) " + re.escape(setting) + r"$", config)) == (side == "left"), (side, setting)
            for setting in ("CONFIG_ZMK_OS_DETECTION_LAYER_AUTO_SWITCH=y", "CONFIG_ZMK_OS_DETECTION_BLE_GATT_CLIENT_PROBE=y", "CONFIG_ZMK_OS_DETECTION_TEST_INJECT=y"):
                assert not re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
            if side == "left":
                assert re.search(r"(?m) CONFIG_ZMK_KEYMAP_LAYER_REORDERING=y$", config), "Studio layer slots require layer reordering"
                for unit in ("os_detection_usb.c", "os_detection_ble.c", "os_detection_settings.c", "default_layer.c", "default_layer_handler.c"):
                    assert unit in config, unit
            print(side, "host-layer config: PASS")
        if "--stability" in sys.argv:
            for setting in ("CONFIG_ZMK_WATCHDOG=y", "CONFIG_ZMK_WATCHDOG_FATAL_DETECT=y", "CONFIG_ZMK_WATCHDOG_FREEZE_DETECT=y", "CONFIG_ZMK_WATCHDOG_SPLIT_RELAY=y", "CONFIG_ZMK_WATCHDOG_MAX_INCIDENTS=16", "CONFIG_ZMK_WATCHDOG_FREEZE_TIMEOUT_MS=30000", "CONFIG_ZMK_WATCHDOG_FREEZE_STARTUP_DELAY_MS=30000", "CONFIG_ZMK_WATCHDOG_FREEZE_FEED_DIVISOR=2", "CONFIG_TASK_WDT=y"):
                assert re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
            for setting in ("CONFIG_TASK_WDT_HW_FALLBACK=y", "CONFIG_ZMK_WATCHDOG_TEST_INJECTION=y", "CONFIG_ZMK_WATCHDOG_TEST=y", "CONFIG_ZMK_WATCHDOG_SPLIT_RELAY_TEST=y", "CONFIG_ZMK_DEVTOOL_LAYER_STATE=y", "CONFIG_ZMK_DEVTOOL_KEY_INJECTION=y", "CONFIG_ZMK_DEVTOOL_EVENT_TAP=y", "CONFIG_ZMK_DEVTOOL_LOG_CAPTURE=y", "CONFIG_ZMK_DEVTOOL_STUDIO_RPC_TEST=y"):
                assert not re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
            for unit in ("watchdog_freeze.c", "watchdog_fatal.c", "watchdog_relay.c"):
                assert unit in config, (side, unit)
            if side == "left":
                for setting in ("CONFIG_ZMK_WATCHDOG_STUDIO_RPC=y", "CONFIG_ZMK_WATCHDOG_STUDIO_RPC_UNSECURED=y", "CONFIG_ZMK_DEVTOOL=y", "CONFIG_ZMK_DEVTOOL_STUDIO_RPC=y", "CONFIG_ZMK_DEVTOOL_STACK_USAGE=y", "CONFIG_THREAD_MONITOR=y", "CONFIG_THREAD_STACK_INFO=y", "CONFIG_THREAD_NAME=y", "CONFIG_INIT_STACKS=y"):
                    assert re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
                assert "devtool_stack.c" in config
            else:
                for setting in ("CONFIG_ZMK_WATCHDOG_STUDIO_RPC=y", "CONFIG_ZMK_DEVTOOL=y"):
                    assert not re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
            print(side, "watchdog detectors/relay and stack diagnostics config: PASS")
        if "--diagnostics" in sys.argv:
            for setting in ("CONFIG_ZMK_KSCAN_DIAGNOSTICS=y", "CONFIG_ZMK_KSCAN_DIAGNOSTICS_SPLIT=y", "CONFIG_ZMK_KSCAN_DIAGNOSTICS_MAX_POSITIONS=70", "CONFIG_ZMK_KSCAN_DIAGNOSTICS_RELAY_STACK_SIZE=4096"):
                assert re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
            for unit in ("kscan_diagnostics_relay.c", "topology.c", "stats.c"):
                assert unit in config, (side, unit)
            if "--stability" not in sys.argv:
                for feature in ("CONFIG_ZMK_WATCHDOG=y", "CONFIG_ZMK_DEVTOOL=y"):
                    assert not re.search(r"(?m) " + re.escape(feature) + r"$", config), (side, feature)
            if side == "left":
                for setting in ("CONFIG_ZMK_DEVICE_INFO=y", "CONFIG_ZMK_DEVICE_INFO_STUDIO_RPC=y", "CONFIG_HWINFO=y", "CONFIG_ZMK_KSCAN_DIAGNOSTICS_STUDIO_RPC=y", "CONFIG_ZMK_KSCAN_DIAGNOSTICS_STUDIO_RPC_UNSECURED=y"):
                    assert re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
                assert not re.search(r"(?m) CONFIG_ZMK_DEVICE_INFO_STUDIO_RPC_REQUIRE_UNLOCK=y$", config)
            else:
                for setting in ("CONFIG_ZMK_DEVICE_INFO_STUDIO_RPC=y", "CONFIG_ZMK_KSCAN_DIAGNOSTICS_STUDIO_RPC=y"):
                    assert not re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
            print(side, "device/key diagnostics configuration and relay stack: PASS")
        if "--settings-sync" in sys.argv:
            assert "modules/settings-rpc/src/activity_store.c" in config, (side, "activity store missing")
            if side == "left":
                assert "modules/settings-rpc/src/activity_sync.c" in config, "Durable outbox missing"
            print(side, "activity sync/store compiled: PASS")
        if "--split-status" in sys.argv and side == "left":
            assert "modules/ble-management/src/studio/ble_management_handler.c" in config, "Local status adapter was not compiled"
            print(side, "local BLE management status adapter compiled: PASS")
        if "--connection" in sys.argv:
            if side == "left":
                for setting in ("CONFIG_ZMK_BLE_MANAGEMENT=y", "CONFIG_ZMK_BLE_MANAGEMENT_STUDIO_RPC=y"):
                    assert re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
            else:
                assert not re.search(r"(?m) CONFIG_ZMK_BLE_MANAGEMENT=y$", config), "BLE management must remain central-only"
            assert re.search(r"(?m) CONFIG_ZMK_IDLE_TIMEOUT=30000$", config), (side, "idle default changed")
            for setting in (("CONFIG_ZMK_OS_DETECTION_LAYER_AUTO_SWITCH=y",) if "--host-layers" in sys.argv and side == "left" else ("CONFIG_ZMK_OS_DETECTION_LAYER_AUTO_SWITCH=y", "CONFIG_ZMK_DEFAULT_LAYER=y")):
                assert not re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, "unexpected behavior change", setting)
            if "--deep-sleep" not in sys.argv:
                assert not re.search(r"(?m) CONFIG_ZMK_SLEEP=y$", config), (side, "unexpected sleep enablement")
            print(side, "DYA connection config: PASS")
        if "--activity-settings" in sys.argv:
            for setting in ("CONFIG_ZMK_SETTINGS_RPC=y", "CONFIG_SETTINGS=y", "CONFIG_SETTINGS_NVS=y", "CONFIG_ZMK_SETTINGS_SAVE_DEBOUNCE=60000"):
                assert re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
            assert bool(re.search(r"(?m) CONFIG_ZMK_SETTINGS_RPC_STUDIO=y$", config)) == (side == "left"), (side, "wrong settings RPC transport role")
            print(side, "activity settings RPC and persistence: PASS")
        else:
            assert not re.search(r"(?m) CONFIG_ZMK_SETTINGS_RPC=y$", config), (side, "unexpected settings RPC")
        if "--deep-sleep" in sys.argv:
            for setting in ("CONFIG_ZMK_SLEEP=y", f"CONFIG_ZMK_IDLE_SLEEP_TIMEOUT={sleep_timeout_ms}", "CONFIG_PM_DEVICE=y", "CONFIG_POWEROFF=y"):
                assert re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
            dts_entry = next(n for n in logs.namelist() if side in n and "Devicetree file" in n)
            dts = logs.read(dts_entry).decode()
            assert re.search(r"kscan_0\s*\{[^}]*wakeup-source;", dts, re.S), (side, "key matrix wake source missing")
            print(side, "deep sleep timeout and matrix wake source: PASS", sleep_timeout_ms)
        uf2 = next(root.glob("*" + side + "*.uf2"))
        data = uf2.read_bytes()
        payload = b"".join(data[i + 32:i + 32 + int.from_bytes(data[i + 16:i + 20], "little")] for i in range(0, len(data), 512))
        if "--trackpad-settings" in sys.argv:
            assert "tp_sens" not in logs.read(next(n for n in logs.namelist() if side in n and "Devicetree file" in n)).decode(), (side, "legacy sensitivity behavior remains")
            names = (b"cleave_right_trackpad", b"cleave_left_scroll", b"speed_percent", b"acceleration_percent", b"max_gain_percent", b"native_scroll_percent", b"scroll_percent")
            if side == "left":
                for name in names:
                    assert name + b"\x00" in payload, (side, name)
                assert bytes.fromhex("85070908951fb102") not in payload, "Legacy trackpad HID report remains"
            else:
                assert b"cleave_right_trackpad\x00" not in payload, "Tuning must live on central only"
            print(side, "role-specific DYA trackpad settings and retired legacy transport: PASS")
        if "--settings-sync" in sys.argv:
            assert b"activity/s\0" in payload, (side, "Activity persistence key missing")
            assert (b"cleave_sync/activity\0" in payload) == (side == "left"), (side, "Outbox must be central-only")
            print(side, "activity persistence/outbox image keys: PASS")
        if "--diagnostics" in sys.argv:
            for namespace in (b"zmk__device_info\0", b"cormoran__kscan_diagnostics\0"):
                assert (namespace in payload) == (side == "left"), (side, namespace)
            if side == "left":
                note = bytes.fromhex("040000001400000003000000474e5500")
                assert payload.count(note) == 1, "Expected one GNU build-id note in left UF2"
                offset = payload.index(note) + len(note)
                print(side, "GNU build-id:", payload[offset:offset+20].hex())
        if "--stability" in sys.argv:
            for namespace in (b"cormoran__watchdog\0", b"cormoran__devtool\0"):
                assert (namespace in payload) == (side == "left"), (side, namespace)
        if "--host-layers" in sys.argv:
            for namespace in (b"cormoran__os_detection\0", b"cormoran__default_layer\0"):
                assert (namespace in payload) == (side == "left"), (side, namespace)
        if "--host-layers" in sys.argv:
            dts_entry = next(n for n in logs.namelist() if side in n and "Devicetree file" in n)
            dts = logs.read(dts_entry).decode()
            for slot in range(1, 5):
                node = re.search(r"host_slot_" + str(slot) + r"\s*\{(.*?)\};", dts, re.S)
                assert node and 'status = "disabled"' in node[1], (side, slot)
                bindings = re.search(r"bindings\s*=\s*<(.*?)>;", node[1], re.S)
                assert bindings and len(re.findall(r"&trans\b", bindings[1])) == 70, (side, slot)
        if "--runtime-macro" in sys.argv:
            dts_entry = next(n for n in logs.namelist() if side in n and "Devicetree file" in n)
            dts = logs.read(dts_entry).decode()
            assert 'compatible = "cormoran,zmk-behavior-runtime-macro"' in dts, (side, "missing macro behavior node")
            assert 'display-name = "Runtime Macro"' in dts, (side, "missing macro display name")
            if side == "left":
                assert "CONFIG_ZMK_BEHAVIOR_METADATA=y" in config
                assert b"Runtime Macro\0" in payload, "Macro behavior metadata missing from central image"
            print(side, "runtime macro assignment definition: PASS")
        if "--pwm-led" in sys.argv:
            assert (b"brightness_percent\0" in payload) == (side == "left"), (side, "LED setting metadata")
            assert (b"cleave_led/saved\0" in payload) == (side == "right"), (side, "LED peripheral storage")
        marker = re.search(rb"CLEAVE_HHJP_UPDATE1\|" + side.upper().encode() + rb"\|([0-9a-f]{8})", payload)
        assert marker, (side, "update identity missing")
        identities[side] = marker[1].decode()
        print(side, "DYA config and custom driver: PASS", identities[side])
assert identities["left"] == identities["right"], identities
assert len(list(root.glob("*settings_reset*.uf2"))) == 1, "Missing settings-reset artifact"
(root / "dya-verification.json").write_text(json.dumps({"builds": identities, "artifact_checks_passed": True, "hardware_verified": False}, indent=2) + "\n")
print("DYA artifact verification: PASS (hardware verification still required)")
