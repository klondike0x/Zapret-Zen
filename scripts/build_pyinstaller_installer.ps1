param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [string]$AppDir = "dist_pyinstaller",
    [string]$PayloadDir = "installer_payload",
    [string]$OutputDir = "dist_installer",
    [switch]$SkipPrepareRelease
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

& $Python scripts\sync_app_icon.py
if ($LASTEXITCODE -ne 0) { throw "sync_app_icon.py failed with exit code $LASTEXITCODE" }

if (-not $SkipPrepareRelease) {
    $sourceDir = Join-Path $root $AppDir
    if (-not (Test-Path (Join-Path $sourceDir "zapret_zen.exe"))) {
        throw "Main app exe not found in $sourceDir. Run build_pyinstaller.ps1 first."
    }

    $payloadDir = Join-Path $root $PayloadDir
    if (Test-Path $payloadDir) {
        Remove-Item $payloadDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $payloadDir -Force | Out-Null

    # Create win_x64.zip payload from the app directory
    $zipPath = Join-Path $payloadDir "win_x64.zip"
    $tempDir = Join-Path $env:TEMP "zapretzen_payload_x64"
    if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force }
    $payloadRoot = Join-Path $tempDir "zapret_zen"
    New-Item -ItemType Directory -Path $payloadRoot -Force | Out-Null
    Get-ChildItem $sourceDir -File | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $payloadRoot -Force
    }
    Compress-Archive -Path (Join-Path $tempDir "*") -DestinationPath $zipPath -CompressionLevel Optimal -Force
    Remove-Item $tempDir -Recurse -Force
}

& pyinstaller @("packaging/install_zapretzen.spec", "--distpath", $OutputDir, "--workpath", "build_installer", "--noconfirm") 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { throw "PyInstaller installer build failed with exit code $LASTEXITCODE" }

$builtExe = Join-Path $OutputDir "install_zapretzen.exe"
$finalExe = Join-Path $OutputDir "install_zapretzen_2.1b_universal.exe"
if (Test-Path $builtExe) {
    Copy-Item -LiteralPath $builtExe -Destination $finalExe -Force
    Remove-Item -LiteralPath $builtExe -Force
}

if (Test-Path "build_installer") {
    Remove-Item "build_installer" -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "PyInstaller installer build complete: $finalExe"
