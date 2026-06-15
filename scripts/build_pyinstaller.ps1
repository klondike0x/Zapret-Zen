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

# Runtime is embedded in the exe via spec datas.
# On first launch, bootstrap.py will copy it from MEIPASS to alongside the exe.

if (Test-Path "build_pyinstaller") {
    Remove-Item "build_pyinstaller" -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "PyInstaller build complete: $OutputDir\zapret_zen\"
