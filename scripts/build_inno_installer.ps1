param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [string]$PayloadDir = "installer_payload",
    [string]$OutputDir = "dist_installer",
    [string]$ReleaseDir = "",
    [string]$X64Source = "",
    [string]$Arm64Source = "",
    [string]$Version = "",
    [string]$Iscc = ""
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not $Version) {
    $Version = & $Python -c "import sys; sys.path.insert(0,'src'); from zapret_zen import __version__; print(__version__)"
}
$nuitkaVersion = & $Python -c "import re; m=re.search(r'^(\d+(?:\.\d+)*)','$Version'.strip()); parts=tuple(int(x) for x in (m.group(1) if m else '0').split('.')[:4]); print('.'.join(str(p) for p in parts))"

if (-not $Iscc) {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
        'C:\Program Files\Inno Setup 6\ISCC.exe'
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            $Iscc = $candidate
            break
        }
    }
    if (-not $Iscc) {
        $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
        if ($cmd) {
            $Iscc = $cmd.Source
        }
    }
}
if (-not $Iscc -or -not (Test-Path -LiteralPath $Iscc)) {
    throw "ISCC.exe not found. Install Inno Setup (winget install JRSoftware.InnoSetup) or pass -Iscc <path>"
}
$isccAbs = (Resolve-Path -LiteralPath $Iscc).Path

$tempRoot = Join-Path $env:TEMP ("zapret_zen_inno_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

try {
    $x64Abs = ""
    $arm64Abs = ""

    if ($X64Source -and $Arm64Source) {
        $x64Abs = (Resolve-Path -LiteralPath $X64Source).Path
        $arm64Abs = (Resolve-Path -LiteralPath $Arm64Source).Path
    } elseif ($ReleaseDir) {
        $x64Abs = (Resolve-Path -LiteralPath "$ReleaseDir\zapret_zen_${Version}_portable_win_x64").Path
        $arm64Abs = (Resolve-Path -LiteralPath "$ReleaseDir\zapret_zen_${Version}_portable_win_arm64").Path
    } elseif ($PayloadDir -and (Test-Path -LiteralPath "$PayloadDir\win_x64.zip")) {
        $x64Out = Join-Path $tempRoot "payload_x64"
        $arm64Out = Join-Path $tempRoot "payload_arm64"
        Expand-Archive -LiteralPath "$PayloadDir\win_x64.zip" -DestinationPath $x64Out -Force
        Expand-Archive -LiteralPath "$PayloadDir\win_arm64.zip" -DestinationPath $arm64Out -Force
        $x64Abs = (Resolve-Path -LiteralPath $x64Out).Path
        $arm64Abs = (Resolve-Path -LiteralPath $arm64Out).Path
    }

    if (-not $x64Abs -or -not $arm64Abs -or -not (Test-Path -LiteralPath $x64Abs) -or -not (Test-Path -LiteralPath $arm64Abs)) {
        throw "Unable to resolve x64/arm64 payload sources. Provide -X64Source/-Arm64Source, -ReleaseDir, or -PayloadDir with win_x64.zip/win_arm64.zip"
    }

    $outAbs = Join-Path $root $OutputDir
    New-Item -ItemType Directory -Path $outAbs -Force | Out-Null

    $iconAbs = (Resolve-Path -LiteralPath (Join-Path $root "ui_assets\icons\app_shell.ico")).Path

    $issArgs = @(
        "/DAppVersion=$Version",
        "/DX64Src=$x64Abs",
        "/DArm64Src=$arm64Abs",
        "/DSetupIcon=$iconAbs",
        "/O$outAbs",
        (Join-Path $root "installer\zapret_zen.iss")
    )

    Write-Host "Compiling Inno Setup script: $issArgs"
    & $isccAbs @issArgs
    if ($LASTEXITCODE -ne 0) {
        throw "ISCC failed with exit code $LASTEXITCODE"
    }
    Write-Host "Built installer: $outAbs\install_zapretzen_${Version}_universal.exe"
} finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}