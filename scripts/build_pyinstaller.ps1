param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [string]$OutputDir = "dist_pyinstaller"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

& $Python scripts\sync_app_icon.py
if ($LASTEXITCODE -ne 0) { throw "sync_app_icon.py failed with exit code $LASTEXITCODE" }

& pyinstaller @("packaging/zapret_zen.spec", "--distpath", $OutputDir, "--workpath", "build_pyinstaller", "--noconfirm") 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed with exit code $LASTEXITCODE" }

$appDir = Join-Path $OutputDir "zapret_zen"
if (-not (Test-Path (Join-Path $appDir "zapret_zen.exe"))) {
    throw "Expected build output not found: $appDir\zapret_zen.exe"
}

$versionLine = & $Python -c "import sys; sys.path.insert(0,'src'); from zapret_zen import __version__; print(__version__)"
$zipName = "ZapretZen_${versionLine}_portable.zip"
$zipPath = Join-Path (Get-Location) $zipName
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path $appDir -DestinationPath $zipPath -CompressionLevel Optimal -Force
Write-Host "Portable ZIP created: $zipName"

if (Test-Path "build_pyinstaller") {
    Remove-Item "build_pyinstaller" -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "PyInstaller build complete: $appDir"
