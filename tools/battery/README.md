# CLEAVE USB battery display

Trackpad tuning is available from the tray's **タッチパッド設定** menu after updating both halves. See [the settings guide](trackpad-settings.md) for speed, acceleration, maximum multiplier, sensitivity, and saving. If the current EXE is running, the new build is provided separately at `output/battery/trackpad/dist/CLEAVE-Battery.exe`; exit the old instance before launching it.

## Windows EXE / notification area

Run `output/battery/dist/CLEAVE-Battery.exe`. Python is bundled and is not
required on the destination PC. The app starts in the notification area beside
the clock. Hover over the two-battery icon to see left/right percentages.
The icon may initially be in Windows' hidden-icons overflow.
Right-click for **残量ウィンドウを開く**, **ファームウェア更新**, or **終了**. Closing the window keeps
the app running. Only one instance can run. Readings refresh every five seconds.
The detail window shows the age of the last peripheral notification. An
unchanged battery level may not generate a new notification.
Windows login autostart is not installed automatically.

To rebuild, run `powershell -ExecutionPolicy Bypass -File tools/battery/build-exe.ps1`.
This creates an isolated build environment under `output/battery/build-env`.
The EXE can also run with `--once --output <JSON path>` for USB diagnostics.

## Firmware / source usage

The left/central half reports its own charge and the right/peripheral charge
over a separate vendor USB HID interface. Status reports are read-only; the
updater uses a separate explicit SET_FEATURE command on that interface.
Keyboard, mouse and Studio remain
on their existing interfaces. No PC Bluetooth connection is required.

Install the PC dependency from the repository root:

```powershell
python -m pip install --target output/battery/python-packages -r tools/battery/requirements.txt
```

For battery-only firmware support, flash the new **left** UF2 and reconnect USB.
For charging status and automatic updates, install matching new UF2s on **both**
halves. Open `tools/battery/Launch-Battery.cmd` (EXE if present, otherwise Python).
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

Initial installation: choose a right update-enabled UF2 (the local prepared
copy is `output/battery/CLEAVE-right-appupdate.uf2`), explicitly select
**キー操作で更新モードへ入れる** checked, click Start, then connect the right
half to USB and hold Fn+N for two seconds. The app detects and copies to the
new UF2 drive. After it disappears, reconnect the parent to USB for verification.
Then repeat for the left update-enabled UF2 (local copy:
`output/battery/CLEAVE-left-appupdate.uf2`) with Fn+B.
These prepared filenames are local copies, not files distributed by Git;
Actions artifact filenames differ. The embedded marker determines the side.
Before clicking Start, both halves must be in normal mode (no UF2 drive).
When the old parent cannot query the newly installed right firmware, the first
right update remains verification-pending. Keep the same app session running:
after a verified left update, it automatically checks the pending right build
for another 30 seconds. Pending state is not persisted across app restarts.
With one cable, move it from right to left after the right UF2 drive disappears;
keep both halves powered and paired for key operations and verification.
The key shortcuts must already be installed; otherwise double-press the target's
physical reset button after clicking Start instead of using Fn+B/N.

After installation, uncheck key-operation mode to use automatic mode. It sends
an explicit USB feature command to
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
The drive itself does not identify left/right; connect only the intended half
for manual boot entry. Drive detection waits up to 90 seconds, and post-reboot
verification up to 60 seconds. Hardware flashing through this app remains
unverified; key-based UF2 entry has been confirmed on both halves.

Feature 3 returns parent info, Feature 5 returns cached child info (32 bytes):
ID, version (1), side (0 left / 1 right), flags (bit 0 update support, bit 1 USB
power), ASCII build ID (8 bytes), `CHHP`, chip ID (8 bytes, parent only), reserved.
Feature 4 accepts ID=4, version=1, target side, `BOOT`, zero padding. The USB
collection maximum feature length is 32; Windows padding is accepted only when
zero. The parent delays the boot action 250 ms to finish the control transfer.
The child info GATT characteristic returns 16 bytes to fit the default ATT MTU.
Child update info is polled every five seconds and expires after 20 seconds or
disconnect. The eight-character build ID is a content hash, not a Git short SHA.

## Source checks and firmware tools

After running `build-exe.ps1`, run from the repository root using its isolated
Python environment (a plain system Python may not have `hidapi` installed):

```powershell
& output/battery/build-env/Scripts/python.exe -m unittest discover -s tools/battery -p "test_*.py"
```

The EXE also accepts `--window` to open the detail window or `--update` to open
the updater at startup. See [firmware tools](firmware-tools.md) for Actions
downloads and UF2/configuration checks. The app does not build firmware or
download updates automatically.

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

## Sudden battery-percentage changes: diagnostics

`battery_diagnostics.py` records the raw USB reports, percentages, power state,
and (with diagnostic firmware) the left battery sensor's cached voltage in mV.
It does not force ADC sampling, smooth readings, or change the charging circuit.
The normal battery worker continues to own sampling. The tray app can stay running.

```powershell
& output/battery/build-env/Scripts/python.exe tools/battery/battery_diagnostics.py --duration 600
```

This records for ten minutes at one-second intervals to a dated JSONL file
under `output/battery/`. Use Ctrl+C to finish early. Recording on old firmware
still captures reports 1/2, but voltage is unavailable. The recorder logs USB
disconnections and resumes reading after reconnection.

To bundle it without replacing the tray EXE:

```powershell
powershell -ExecutionPolicy Bypass -File tools/battery/build-diagnostics-exe.ps1
```

Run `output/battery/dist/CLEAVE-Battery-Diagnostics.exe` from the repository
root, or set `--output <new JSONL path>`. The standalone EXE needs no Python.
The output path must not already exist, to preserve earlier recordings.

Read-only Feature 6 has 16 meaningful bytes (request 32 on Windows): ID=6,
version=1, firmware percentage, power state, voltage mV (uint16 LE), sensor
percentage, flags (bit0 voltage valid, bit1 sensor percentage valid), uptime
seconds (uint32 LE), age of the last percentage-change event (uint32 LE,
`0xffffffff` before the first event). That age is not the last ADC sampling age.
Voltage and percentage are read sequentially and may briefly straddle an update;
use repeated records to evaluate discrepancies. Feature 6 is optional to the
tray app and existing updater; their reports and buffer size remain compatible.

For a drop, compare firmware percentage, sensor percentage, cached voltage,
power state and uptime. Uptime decreasing indicates a reboot. A simultaneous
cached-voltage change points toward sampling or the electrical measurement path,
but does not by itself prove the actual battery voltage changed.
