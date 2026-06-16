$ErrorActionPreference = 'SilentlyContinue'
$pidToWait = {{PID}}
$src = '{{SRC}}'
$dst = '{{DST}}'
$launch = '{{LAUNCH}}'
$tempRoot = '{{TEMP_ROOT}}'
$logPath = '{{LOG_PATH}}'
$preserve = @('data', 'mods', 'configs', 'cache', 'logs', 'backups')
$backupRoot = Join-Path '{{SCRIPT_ROOT}}' ('preserve_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
Add-Content -LiteralPath $logPath -Value ('[' + (Get-Date -Format s) + '] updater started')

function Remove-PathRobust([string]$targetPath) {
  if (-not (Test-Path $targetPath)) { return $true }
  for ($i = 0; $i -lt 6; $i++) {
    try {
      attrib -r -s -h $targetPath /s /d *> $null
    } catch {}
    try {
      Remove-Item $targetPath -Recurse -Force -ErrorAction Stop
      return $true
    } catch {
      Start-Sleep -Milliseconds 300
    }
  }
  $quarantineRoot = Join-Path $env:TEMP 'zapret_zen_update_quarantine'
  New-Item -ItemType Directory -Path $quarantineRoot -Force | Out-Null
  $moved = Join-Path $quarantineRoot ((Split-Path $targetPath -Leaf) + '_' + [guid]::NewGuid().ToString('N'))
  try {
    Move-Item $targetPath $moved -Force -ErrorAction Stop
    return $true
  } catch {
    return $false
  }
}

function Add-UpdateLog([string]$message) {
  try {
    Add-Content -LiteralPath $logPath -Value ('[' + (Get-Date -Format s) + '] ' + $message)
  } catch {}
}

function Test-StandalonePayload([string]$sourceDir) {
  return (Test-Path (Join-Path $sourceDir 'python311.dll')) -and
         (Test-Path (Join-Path $sourceDir 'python3.dll')) -and
         (Test-Path (Join-Path $sourceDir 'zapret_zen.exe'))
}

function Test-InstalledStandalone([string]$targetDir) {
  return (Test-Path (Join-Path $targetDir 'python311.dll')) -and
         (Test-Path (Join-Path $targetDir 'python3.dll')) -and
         (Test-Path (Join-Path $targetDir 'zapret_zen.exe'))
}

function Overlay-Tree([string]$sourceDir, [string]$targetDir, [string[]]$preserveNames) {
  New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
  $sourceItems = Get-ChildItem -LiteralPath $sourceDir -Force -ErrorAction SilentlyContinue
  $sourceNames = @{}
  foreach ($item in $sourceItems) {
    $sourceNames[$item.Name] = $true
  }
  Get-ChildItem -LiteralPath $targetDir -Force -ErrorAction SilentlyContinue | ForEach-Object {
    if ($preserveNames -contains $_.Name) { return }
    if (-not $sourceNames.ContainsKey($_.Name)) {
      [void](Remove-PathRobust $_.FullName)
    }
  }
  foreach ($item in $sourceItems) {
    if ($preserveNames -contains $item.Name) { continue }
    $dest = Join-Path $targetDir $item.Name
    if ($item.PSIsContainer) {
      Overlay-Tree $item.FullName $dest $preserveNames
    } else {
      if (Test-Path $dest) {
        [void](Remove-PathRobust $dest)
      }
      New-Item -ItemType Directory -Path (Split-Path $dest -Parent) -Force | Out-Null
      try {
        Copy-Item $item.FullName $dest -Force -ErrorAction Stop
      } catch {
        Add-UpdateLog ('copy failed: ' + $item.FullName + ' -> ' + $dest + ' | ' + $_.Exception.Message)
      }
    }
  }
}

for ($i = 0; $i -lt 120; $i++) {
  if (-not (Get-Process -Id $pidToWait -ErrorAction SilentlyContinue)) { break }
  Start-Sleep -Milliseconds 250
}

if (Get-Process -Id $pidToWait -ErrorAction SilentlyContinue) {
  Add-Content -LiteralPath $logPath -Value ('[' + (Get-Date -Format s) + '] forcing old process stop')
  Stop-Process -Id $pidToWait -Force -ErrorAction SilentlyContinue
  for ($i = 0; $i -lt 40; $i++) {
    if (-not (Get-Process -Id $pidToWait -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Milliseconds 250
  }
}

try { sc stop zapret *> $null } catch {}
try { sc delete zapret *> $null } catch {}
foreach ($image in @('zapret_zen.exe', 'TgWsProxy_windows.exe', 'winws.exe')) {
  try { taskkill /F /T /IM $image *> $null } catch {}
}

New-Item -ItemType Directory -Path $dst -Force | Out-Null

foreach ($item in $preserve) {
  $dstItem = Join-Path $dst $item
  try {
    if (Test-Path $dstItem) {
      Move-Item $dstItem (Join-Path $backupRoot $item) -Force
    }
  } catch {}
}
Add-Content -LiteralPath $logPath -Value ('[' + (Get-Date -Format s) + '] preserved user dirs')

$sourceIsStandalone = Test-StandalonePayload $src
if ($sourceIsStandalone) {
  Add-UpdateLog 'standalone payload detected'
  $oldInternal = Join-Path $dst '_internal'
  if (Test-Path $oldInternal) {
    [void](Remove-PathRobust $oldInternal)
    Add-UpdateLog 'old _internal removed for standalone update'
  }
}

Overlay-Tree $src $dst $preserve
Add-Content -LiteralPath $logPath -Value ('[' + (Get-Date -Format s) + '] payload copied')

if ($sourceIsStandalone -and -not (Test-InstalledStandalone $dst)) {
  Add-UpdateLog 'standalone validation failed after overlay, retrying top-level runtime files'
  foreach ($fileName in @('zapret_zen.exe', 'python311.dll', 'python3.dll')) {
    $sourceFile = Join-Path $src $fileName
    $targetFile = Join-Path $dst $fileName
    if (Test-Path $sourceFile) {
      [void](Remove-PathRobust $targetFile)
      try {
        Copy-Item $sourceFile $targetFile -Force -ErrorAction Stop
        Add-UpdateLog ('runtime file copied: ' + $fileName)
      } catch {
        Add-UpdateLog ('runtime file copy failed: ' + $fileName + ' | ' + $_.Exception.Message)
      }
    }
  }
}

foreach ($item in $preserve) {
  $backupItem = Join-Path $backupRoot $item
  $target = Join-Path $dst $item
  if (Test-Path $backupItem) {
    try {
      if (Test-Path $target) {
        [void](Remove-PathRobust $target)
      }
    } catch {}
    Move-Item $backupItem $target -Force
  }
}
Add-Content -LiteralPath $logPath -Value ('[' + (Get-Date -Format s) + '] user data restored')

if ($sourceIsStandalone -and -not (Test-InstalledStandalone $dst)) {
  Add-UpdateLog 'standalone validation failed, aborting relaunch to avoid broken install'
  exit 2
}

Start-Sleep -Milliseconds 400
$launch = Join-Path $dst 'zapret_zen.exe'
Start-Process -FilePath $launch -WorkingDirectory $dst
Add-Content -LiteralPath $logPath -Value ('[' + (Get-Date -Format s) + '] relaunched app')
Remove-Item $backupRoot -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
Remove-Item '{{SELF_DELETE}}' -Force -ErrorAction SilentlyContinue
