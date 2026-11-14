#Requires -Version 7.0
<#
.SYNOPSIS
  Starts the worktree-owned PostgreSQL cluster (if not already running) and records its postmaster PID.
  Refuses to start if the configured port is already bound by another process.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$pgBin = Join-Path $root '.local/tools/pgsql-18.7-1/bin'
$data = Join-Path $root '.local/postgres-data'
$log = Join-Path $root '.local/logs/postgres.log'
$settings = Get-Content (Join-Path $root '.local/secrets/pg-local.json') -Raw | ConvertFrom-Json
$pidFile = Join-Path $data 'postmaster.pid'

& (Join-Path $pgBin 'pg_ctl.exe') status -D $data *> $null
if ($LASTEXITCODE -eq 0) {
    $postmasterPid = [int](Get-Content $pidFile -TotalCount 1)
    Write-Host "Owned cluster already running (postmaster PID $postmasterPid)."
    return
}

$listener = Get-NetTCPConnection -State Listen -LocalPort $settings.port -ErrorAction SilentlyContinue
if ($listener) {
    throw "Port $($settings.port) is already bound by PID $($listener[0].OwningProcess); not starting (not ours)."
}

# Launch pg_ctl through ShellExecute (hidden window) so the postmaster does not inherit this
# session's stdout/stderr pipes; otherwise a calling pipeline blocks until the server exits.
$pgCtl = Start-Process -FilePath (Join-Path $pgBin 'pg_ctl.exe') -WindowStyle Hidden -PassThru `
    -ArgumentList @('start', '-D', "`"$data`"", '-l', "`"$log`"", '-w', '-t', '60')
$pgCtl.WaitForExit()
if ($pgCtl.ExitCode -ne 0) { throw "pg_ctl start failed (exit $($pgCtl.ExitCode)); see .local/logs/postgres.log" }

$postmasterPid = [int](Get-Content $pidFile -TotalCount 1)
$process = Get-Process -Id $postmasterPid
Write-Host ("Owned cluster started: postmaster PID {0}, started {1:o}, data {2}" -f $postmasterPid, $process.StartTime.ToUniversalTime(), $data)
