param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [string]$PayloadDir = "installer_payload",
    [string]$OutputDir = "dist_installer",
    [string]$ReleaseDir = "",
    [string]$X64Source = "",
    [string]$Arm64Source = "",
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
$nuitkaVersion = & $Python -c "import re; m=re.search(r'^(\d+(?:\.\d+)*)','$Version'.strip()); parts=tuple(int(x) for x in (m.group(1) if m else '0').split('.')[:4]); print('.'.join(str(p) for p in parts))"

if (-not $ReleaseDir) {
    $ReleaseDir = "release_$Version"
}

$installerPy = Join-Path $root "installer" "install_zapretzen.py"
$content = Get-Content $installerPy -Raw -Encoding UTF8
$content = $content -replace '(?<=INSTALLER_VERSION\s*=\s*")[^"]*', $Version
Set-Content $installerPy -NoNewLine -Encoding UTF8 -Value $content
Write-Host "Injected INSTALLER_VERSION=$Version into installer source"

& $Python scripts\sync_app_icon.py
if ($LASTEXITCODE -ne 0) { throw "sync_app_icon.py failed with exit code $LASTEXITCODE" }
if (-not $SkipPrepareRelease) {
    $prepareArgs = @(
        "scripts\prepare_nuitka_release.py",
        "--payload-dir",
        $PayloadDir,
        "--release-dir",
        $ReleaseDir
    )
    if ($X64Source) {
        $prepareArgs += @("--x64-source", $X64Source)
    }
    if ($Arm64Source) {
        $prepareArgs += @("--arm64-source", $Arm64Source)
    }
    & $Python @prepareArgs
    if ($LASTEXITCODE -ne 0) { throw "prepare_nuitka_release.py failed with exit code $LASTEXITCODE" }
}

& $Python -m nuitka `
  --onefile `
  --assume-yes-for-downloads `
  --no-deployment-flag=self-execution `
  --msvc=latest `
  --enable-plugin=pyside6 `
  --windows-console-mode=disable `
  --windows-uac-admin `
  --windows-icon-from-ico=ui_assets\icons\app_shell.ico `
  --company-name="peshk0v" `
  --product-name="Zapret-Zen Installer" `
  --file-version="$nuitkaVersion" `
  --product-version="$nuitkaVersion" `
  --file-description="Zapret-Zen Installer" `
  --copyright="peshk0v" `
  --output-dir=$OutputDir `
  --output-filename="install_zapretzen_${Version}_universal.exe" `
  --include-data-dir=$PayloadDir=installer_payload `
  --include-data-dir=ui_assets=ui_assets `
  --nofollow-import-to=tkinter `
  --remove-output `
  installer\install_zapretzen.py
if ($LASTEXITCODE -ne 0) { throw "Nuitka installer build failed with exit code $LASTEXITCODE" }
