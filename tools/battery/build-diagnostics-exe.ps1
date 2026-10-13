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
& $taskPython -m PyInstaller --noconfirm --onefile --console --name CLEAVE-Battery-Diagnostics --distpath output\battery\dist --workpath output\battery\build-diagnostics --specpath output\battery tools\battery\battery_diagnostics.py
if ($LASTEXITCODE -ne 0) { throw 'Diagnostic EXE build failed' }
