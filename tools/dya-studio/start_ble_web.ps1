param(
    [string]$WebRoot = (Join-Path $PSScriptRoot 'web'),
    [int]$Port = 8766
)
$ErrorActionPreference = 'Stop'
$resolvedWeb = (Resolve-Path -LiteralPath $WebRoot).Path
if (-not (Test-Path -LiteralPath (Join-Path $resolvedWeb 'index.html'))) {
    throw "DYA web build not found: $resolvedWeb"
}
$listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($listener) {
    throw "Port $Port is already in use. Existing process left unchanged."
}
$pythonPath = (Get-Command python -ErrorAction Stop).Source
$logRoot = Split-Path -Parent $resolvedWeb
$process = Start-Process -WindowStyle Hidden -PassThru -FilePath $pythonPath `
    -ArgumentList @('-m', 'http.server', "$Port", '--bind', '127.0.0.1', '--directory', ('"' + $resolvedWeb + '"')) `
    -RedirectStandardOutput (Join-Path $logRoot 'server.stdout.log') `
    -RedirectStandardError (Join-Path $logRoot 'server.stderr.log')
$process.Id | Set-Content -LiteralPath (Join-Path $logRoot 'server.pid')
Write-Output "Local DYA: http://localhost:$Port/ (PID $($process.Id))"
