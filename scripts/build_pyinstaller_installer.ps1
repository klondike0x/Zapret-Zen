param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [string]$AppDir = "dist_pyinstaller",
    [string]$PayloadDir = "installer_payload",
    [string]$OutputDir = "dist_installer",
    [switch]$SkipPrepareRelease,
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $Version) {
    $Version = & $Python -c "import sys; sys.path.insert(0,'src'); from zapret_zen import __version__; print(__version__)"
} else {
    $initPy = Join-Path $root "src" "zapret_zen" "__init__.py"
    $content = Get-Content $initPy -Raw -Encoding UTF8
    $content = $content -replace '(?<=__version__\s*=\s*")[^"]*', $Version
    Set-Content $initPy -NoNewLine -Encoding UTF8 -Value $content
    Write-Host "Injected version $Version into $initPy"
}

$installerPy = Join-Path $root "installer" "install_zapretzen.py"
$content = Get-Content $installerPy -Raw -Encoding UTF8
$content = $content -replace '(?<=INSTALLER_VERSION\s*=\s*")[^"]*', $Version
Set-Content $installerPy -NoNewLine -Encoding UTF8 -Value $content
Write-Host "Injected INSTALLER_VERSION=$Version into installer source"

& $Python scripts\sync_app_icon.py
if ($LASTEXITCODE -ne 0) { throw "sync_app_icon.py failed with exit code $LASTEXITCODE" }

$versionLine = $Version

if (-not $SkipPrepareRelease) {
    $appRoot = Join-Path $root $AppDir "zapret_zen"
    if (-not (Test-Path (Join-Path $appRoot "zapret_zen.exe"))) {
        throw "Main app exe not found in $appRoot. Run build_pyinstaller.ps1 first."
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
    Copy-Item -LiteralPath $appRoot -Destination $payloadRoot -Recurse -Force
    Compress-Archive -Path (Join-Path $tempDir "*") -DestinationPath $zipPath -CompressionLevel Optimal -Force
    Remove-Item $tempDir -Recurse -Force
}

& pyinstaller @("packaging/install_zapretzen.spec", "--distpath", $OutputDir, "--workpath", "build_installer", "--noconfirm") 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { throw "PyInstaller installer build failed with exit code $LASTEXITCODE" }

$builtExe = Join-Path $OutputDir "install_zapretzen.exe"
$finalExe = Join-Path $OutputDir "install_zapretzen_${versionLine}_universal.exe"
if (Test-Path $builtExe) {
    Copy-Item -LiteralPath $builtExe -Destination $finalExe -Force
    Remove-Item -LiteralPath $builtExe -Force
}

if (Test-Path "build_installer") {
    Remove-Item "build_installer" -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "PyInstaller installer build complete: $finalExe"
