<#
.SYNOPSIS
    Mirrors a working tree into OneDrive, skipping regenerable dependency folders.
.DESCRIPTION
    Driven by the "Claude Backup" scheduled task; safe to run by hand.
    Defaults mirror D:\Claude into <OneDrive>\Backups\Claude.
#>
[CmdletBinding()]
param(
    [string]   $Source       = 'D:\Claude',
    [string]   $Dest         = (Join-Path $env:OneDrive 'Backups\Claude'),
    [string]   $LogDir       = (Join-Path $env:LOCALAPPDATA 'ClaudeBackup'),
    [string[]] $ExcludeDirs  = @('node_modules', '.venv', '.next', '__pycache__', '.pytest_cache'),
    [string[]] $ExcludeFiles = @('*.pyc', 'Thumbs.db', 'desktop.ini')
)

$ErrorActionPreference = 'Stop'
$Log = Join-Path $LogDir 'backup.log'

# Guard: /MIR deletes anything in the destination that is missing from the
# source, so refuse to run if the source is gone or unexpectedly empty.
if (-not (Test-Path -LiteralPath $Source)) { throw "Source missing: $Source" }
if (@(Get-ChildItem -LiteralPath $Source -Force -Directory).Count -lt 1) {
    throw "Source has no subfolders; refusing to mirror: $Source"
}
if ([string]::IsNullOrWhiteSpace($Dest)) {
    throw 'Destination is empty -- is $env:OneDrive set for this account?'
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
New-Item -ItemType Directory -Force -Path $Dest   | Out-Null

if ((Test-Path -LiteralPath $Log) -and ((Get-Item -LiteralPath $Log).Length -gt 5MB)) {
    Move-Item -LiteralPath $Log -Destination "$Log.old" -Force
}

$roboArgs = @($Source, $Dest, '/MIR', '/FFT', '/R:2', '/W:2', '/NP', '/NDL',
              "/LOG+:$Log", '/XD') + $ExcludeDirs + @('/XF') + $ExcludeFiles

Add-Content -Path $Log -Value ("`r`n===== {0}  start =====" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
& robocopy.exe @roboArgs | Out-Null
$rc = $LASTEXITCODE

# robocopy: 0-7 are success codes, 8+ mean real failures
if ($rc -ge 8) {
    Add-Content -Path $Log -Value "FAILED rc=$rc"
    exit 1
}
Add-Content -Path $Log -Value "OK rc=$rc"
exit 0
