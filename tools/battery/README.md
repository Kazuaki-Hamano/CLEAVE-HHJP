# CLEAVE USB battery display

## Windows EXE / notification area

Run `output/battery/dist/CLEAVE-Battery.exe`. Python is bundled and is not
required on the destination PC. The app starts in the notification area beside
the clock. Hover over the two-battery icon to see left/right percentages.
The icon may initially be in Windows' hidden-icons overflow.
Right-click for **残量ウィンドウを開く** or **終了**. Closing the window keeps
the app running. Only one instance can run. Readings refresh every five seconds.
The detail window shows the age of the last peripheral notification. An
unchanged battery level may not generate a new notification.
Windows login autostart is not installed automatically.

To rebuild, run `powershell -ExecutionPolicy Bypass -File tools/battery/build-exe.ps1`.
This creates an isolated build environment under `output/battery/build-env`.
The EXE can also run with `--once --output <JSON path>` for USB diagnostics.

## Firmware / source usage

The left/central half reports its own charge and the right/peripheral charge
over a separate read-only USB HID interface. Keyboard, mouse and Studio remain
on their existing interfaces. No PC Bluetooth connection is required.

Install the PC dependency from the repository root:

```powershell
python -m pip install --target output/battery/python-packages -r tools/battery/requirements.txt
```

Flash the new **left** UF2, reconnect USB, then open `Launch-Battery.cmd`.
For diagnostic JSON, run `python tools/battery/battery_monitor.py --once`.
The window refreshes every five seconds; battery measurements normally update
every sixty seconds. Right is shown as unknown before its first notification
and after disconnect. The last notification age is displayed so an old value
is identifiable. A zero percent reading is a real value, distinct from unknown.
Percentages are ZMK's voltage-based estimates, including while charging.

Hardware acceptance: verify both values, switch the right half off and confirm
unknown, switch it on and wait for a value; unplug/reconnect USB and confirm
recovery. Also verify typing, mouse layer, and Studio still work.

Protocol: vendor usage page `0xff60`, usage `1`, Feature report ID `1`.
Seven bytes: ID, protocol version (1), left %, right %, right-valid (0/1),
right notification age in seconds (uint16 little endian, saturates at 65535).
This implementation supports one central with one BLE peripheral.

## Firmware updater

Right-click the tray icon and select **ファームウェア更新**. Choose left/right
and the matching UF2, then click **更新開始**. The app validates UF2 structure,
nRF52840 family, application address range, complete block ordering and the
embedded CLEAVE left/right identity. Generic, settings-reset, bootloader, and
older unmarked images are rejected. The validated bytes are held in memory.

Initial installation: choose the new `CLEAVE-right-appupdate.uf2`, leave
**キー操作で更新モードへ入れる** checked, click Start, then connect the right
half to USB and hold Fn+N for two seconds. The app detects and copies to the
new UF2 drive. Then repeat for `CLEAVE-left-appupdate.uf2` with Fn+B.
Before clicking Start, both halves must be in normal mode (no UF2 drive).
When the old parent cannot query the newly installed right firmware, the first
right update remains verification-pending. Install/reconnect the parent and
confirm that both builds are readable.

After installation, automatic mode sends an explicit USB feature command to
the parent. Left boots locally; right boots using the existing encrypted split
behavior command. Keep the parent USB connected, and connect the right half
with another USB data cable when updating the right. Wait several seconds for
the right USB state to be reported. With one cable, use key-operation mode.

The app requires exactly one newly appeared XIAO UF2 drive and rechecks its
volume identity before copying. After the drive disappears, it compares the
running target's reported build with the chosen UF2 and checks the parent chip
identity when available. File copying alone is never reported as verified
success. The updater window and app cannot be closed normally during a write.
Connect/disconnect or recovery failures remain visible as errors or pending
verification. The physical reset button and Fn bootloader keys remain usable.

Feature 3 returns parent info, Feature 5 returns cached child info (32 bytes):
ID, version (1), side (0 left / 1 right), flags (bit 0 update support, bit 1 USB
power), ASCII build ID (8 bytes), `CHHP`, chip ID (8 bytes, parent only), reserved.
Feature 4 accepts ID=4, version=1, target side, `BOOT`, zero padding. The USB
collection maximum feature length is 32; Windows padding is accepted only when
zero. The parent delays the boot action 250 ms to finish the control transfer.
The child info GATT characteristic returns 16 bytes to fit the default ATT MTU.

## Charging status

Flash **both left and right** charging-enabled UF2 files. The app keeps reading
battery levels from old firmware but displays **充電不明** for unsupported sides.
Feature report 2 has six bytes: ID (2), version (1), left power state,
right power state, right-state age in seconds (uint16 little endian).
States: 0 unknown, 1 battery, 2 USB powered without an active charging signal,
3 charging. USB powered does not establish that the battery is full.
XIAO P0.17 is input-only, active-low CHG. nRF52840 VBUS detection also works
with a wall charger. A pull-up is enabled only while USB power is present.
The central polls an encrypted read-only custom GATT characteristic over the
existing split link every five seconds. Right charging state becomes unknown
on disconnect or when it has not been successfully read for over 20 seconds.

Acceptance: compare both charging indicators with the board charge LEDs;
connect/disconnect each USB cable, confirm the corresponding state changes,
then verify typing, mouse and Studio. Full-charge classification is not inferred
from percentages or a deasserted CHG signal. No charging-current settings change.
