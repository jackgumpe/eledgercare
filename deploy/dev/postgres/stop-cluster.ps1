#Requires -Version 7.0
<#
.SYNOPSIS
  Stops only the worktree-owned PostgreSQL cluster through pg_ctl on its own data directory
  (fast shutdown: active sessions are rolled back, a shutdown checkpoint is written).
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$pgBin = Join-Path $root '.local/tools/pgsql-18.7-1/bin'
$data = Join-Path $root '.local/postgres-data'

& (Join-Path $pgBin 'pg_ctl.exe') status -D $data *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Owned cluster is not running.'
    return
}

& (Join-Path $pgBin 'pg_ctl.exe') stop -D $data -m fast -w -t 60 | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'pg_ctl stop failed.' }
