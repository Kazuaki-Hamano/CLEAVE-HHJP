@echo off
cd /d "%~dp0\..\.."
if exist "output\battery\dist\CLEAVE-Battery.exe" (
    start "" "output\battery\dist\CLEAVE-Battery.exe"
    exit /b
)
start "" pythonw "tools\battery\battery_monitor.py"
