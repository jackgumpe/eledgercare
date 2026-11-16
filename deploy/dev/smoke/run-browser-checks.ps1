#Requires -Version 7.0
<#
.SYNOPSIS
  Runs the Playwright F1 + F2 browser checks against a freshly prepared owned database.
.DESCRIPTION
  Product-owned F1 + F2 browser runner (F2-KR-01 / F2-BIC-01), self-contained within deploy/dev.
  Defaults to author loopback ports (API 5190, UI 4210) and honors -ApiPort / -UiPort so
  independent review (5290 / 4310) runs the exact frozen candidate without source edits.
#>
[CmdletBinding()]
param(
    [string] $Database = 'eledgercare_e2e',
    [int] $ApiPort = 5190,
    [int] $UiPort = 4210
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$settings = Get-Content (Join-Path $root '.local/secrets/pg-local.json') -Raw | ConvertFrom-Json
$psql = Join-Path $root '.local/tools/pgsql-18.7-1/bin/psql.exe'

foreach ($port in $ApiPort, $UiPort) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    if ($listener) {
        throw "Port $port is already bound by PID $($listener[0].OwningProcess); not ours, not touching it."
    }
}

$env:PGPASSWORD = $settings.adminPassword
try {
    "DROP DATABASE IF EXISTS $Database WITH (FORCE);" | & $psql -X -q -v ON_ERROR_STOP=1 -h $settings.host -p $settings.port -U $settings.adminUser -d postgres -f -
    if ($LASTEXITCODE -ne 0) { throw 'Could not reset the e2e database.' }
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

& (Join-Path $root 'deploy/dev/database/prepare-database.ps1') -Database $Database

$env:E2E_DATABASE = $Database
$env:ELEDGERCARE_API_PORT = [string]$ApiPort
$env:ELEDGERCARE_UI_PORT = [string]$UiPort
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $root '.local/ms-playwright'
$env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = '1'
$env:NG_CLI_ANALYTICS = 'false'

Push-Location (Join-Path $root 'web')
try {
    npx playwright test
    $exit = $LASTEXITCODE
} finally {
    Pop-Location
    Remove-Item Env:E2E_DATABASE, Env:ELEDGERCARE_API_PORT, Env:ELEDGERCARE_UI_PORT -ErrorAction SilentlyContinue
}
exit $exit
