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
        if "--connection" in sys.argv:
            if side == "left":
                for setting in ("CONFIG_ZMK_BLE_MANAGEMENT=y", "CONFIG_ZMK_BLE_MANAGEMENT_STUDIO_RPC=y"):
                    assert re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, setting)
            else:
                assert not re.search(r"(?m) CONFIG_ZMK_BLE_MANAGEMENT=y$", config), "BLE management must remain central-only"
            assert re.search(r"(?m) CONFIG_ZMK_IDLE_TIMEOUT=30000$", config), (side, "idle default changed")
            for setting in ("CONFIG_ZMK_SETTINGS_RPC=y", "CONFIG_ZMK_OS_DETECTION_LAYER_AUTO_SWITCH=y", "CONFIG_ZMK_DEFAULT_LAYER=y", "CONFIG_ZMK_SLEEP=y"):
                assert not re.search(r"(?m) " + re.escape(setting) + r"$", config), (side, "unexpected behavior change", setting)
            print(side, "DYA connection config: PASS")
        uf2 = next(root.glob("*" + side + "*.uf2"))
        data = uf2.read_bytes()
        payload = b"".join(data[i + 32:i + 32 + int.from_bytes(data[i + 16:i + 20], "little")] for i in range(0, len(data), 512))
        marker = re.search(rb"CLEAVE_HHJP_UPDATE1\|" + side.upper().encode() + rb"\|([0-9a-f]{8})", payload)
        assert marker, (side, "update identity missing")
        identities[side] = marker[1].decode()
        print(side, "DYA config and custom driver: PASS", identities[side])
assert identities["left"] == identities["right"], identities
assert len(list(root.glob("*settings_reset*.uf2"))) == 1, "Missing settings-reset artifact"
(root / "dya-verification.json").write_text(json.dumps({"builds": identities, "artifact_checks_passed": True, "hardware_verified": False}, indent=2) + "\n")
print("DYA artifact verification: PASS (hardware verification still required)")
