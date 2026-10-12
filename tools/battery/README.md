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
