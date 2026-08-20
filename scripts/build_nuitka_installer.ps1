param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [string]$OutputDir = "dist_installer",
    [string]$Version = "",
    [string]$Tag = ""
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

$installerPy = Join-Path $root "installer" "install_zapretzen.py"
$content = Get-Content $installerPy -Raw -Encoding UTF8
$content = $content -replace '(?<=INSTALLER_VERSION\s*=\s*")[^"]*', $Version
if ($Tag) {
    $content = $content -replace '(?<=DEFAULT_RELEASE_TAG\s*=\s*")[^"]*', $Tag
    Write-Host "Injected DEFAULT_RELEASE_TAG=$Tag into installer source"
} else {
    $content = $content -replace '(?<=DEFAULT_RELEASE_TAG\s*=\s*")[^"]*', "v$Version"
    Write-Host "Injected DEFAULT_RELEASE_TAG=v$Version into installer source"
}
Set-Content $installerPy -NoNewLine -Encoding UTF8 -Value $content
Write-Host "Injected INSTALLER_VERSION=$Version into installer source"

& $Python scripts\sync_app_icon.py
if ($LASTEXITCODE -ne 0) { throw "sync_app_icon.py failed with exit code $LASTEXITCODE" }

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
  --nofollow-import-to=tkinter `
  --remove-output `
  installer\install_zapretzen.py
if ($LASTEXITCODE -ne 0) { throw "Nuitka installer build failed with exit code $LASTEXITCODE" }
