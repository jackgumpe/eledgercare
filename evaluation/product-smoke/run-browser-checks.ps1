#Requires -Version 7.0
<#
.SYNOPSIS
  Runs the Playwright F1 browser checks against a freshly prepared owned database (eledgercare_e2e).
.DESCRIPTION
  Preconditions: owned cluster running (deploy/dev/postgres/setup-cluster.ps1), solution built in Release,
  web dependencies installed (npm ci in web/). Uses the installed Microsoft Edge through Playwright's
  msedge channel; PLAYWRIGHT_BROWSERS_PATH points inside .local so nothing is downloaded elsewhere.
  Ports 5180 (API) and 4200 (Angular dev server) must be free; nothing already listening is touched.
#>
[CmdletBinding()]
param(
    [string] $Database = 'eledgercare_e2e'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$settings = Get-Content (Join-Path $root '.local/secrets/pg-local.json') -Raw | ConvertFrom-Json
$psql = Join-Path $root '.local/tools/pgsql-18.7-1/bin/psql.exe'

foreach ($port in 5180, 4200) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    if ($listener) { throw "Port $port is already bound by PID $($listener[0].OwningProcess); not ours, not touching it." }
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
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $root '.local/ms-playwright'
$env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = '1'
$env:NG_CLI_ANALYTICS = 'false'
Push-Location (Join-Path $root 'web')
try {
    npx playwright test
    $exit = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $exit
