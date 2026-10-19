$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location -LiteralPath $taskRoot
$taskPython = Join-Path $taskRoot 'output\battery\build-env\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    python -m venv output\battery\build-env
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create build environment' }
}
& $taskPython -m pip install -r tools\battery\requirements.txt pyinstaller==6.16.0
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed' }
& $taskPython -m PyInstaller --noconfirm --onefile --windowed --name CLEAVE-Battery --hidden-import pystray._win32 --distpath output\battery\dist --workpath output\battery\build --specpath output\battery tools\battery\battery_monitor.py
if ($LASTEXITCODE -ne 0) { throw 'EXE build failed' }
