param(
    [Parameter(Mandatory = $true)]
    [string]$InputPath
)

if (-not (Test-Path -LiteralPath $InputPath)) {
    Write-Error "File not found: $InputPath"
    exit 1
}

Write-Host "SignPath stub: $InputPath (signing skipped)"
