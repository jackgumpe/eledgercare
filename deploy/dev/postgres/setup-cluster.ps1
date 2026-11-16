#Requires -Version 7.0
<#
.SYNOPSIS
  Creates (once) and starts the worktree-owned local PostgreSQL 18.7 cluster for eLedgerCare F1.

.DESCRIPTION
  Everything lives under <worktree>/.local (ignored by Git):
    .local/tools/pgsql-18.7-1     server subset of the official EDB Windows x64 binaries archive
    .local/postgres-data          cluster data directory
    .local/logs/postgres.log      server log
    .local/secrets/pg-local.json  generated local credentials and port (never committed)
  No Windows service, installer, PATH change or machine-wide configuration is made.
  The server listens on 127.0.0.1 only, with scram-sha-256 authentication, and durability settings
  fsync, full_page_writes and synchronous_commit explicitly on.

  Roles: eledgercare_admin (cluster superuser, setup/harness only), eledgercare_migrator (schema owner,
  migrations), eledgercare_app (runtime: CONNECT, schema USAGE, SELECT/INSERT on the three F1 tables).
#>
[CmdletBinding()]
param(
    [int] $Port = 55434
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$local = Join-Path $root '.local'
$pgHome = Join-Path $local 'tools/pgsql-18.7-1'
$pgBin = Join-Path $pgHome 'bin'
$data = Join-Path $local 'postgres-data'
$logs = Join-Path $local 'logs'
$secrets = Join-Path $local 'secrets'
$settingsPath = Join-Path $secrets 'pg-local.json'
New-Item -ItemType Directory -Force $logs, $secrets | Out-Null

if (-not (Test-Path (Join-Path $pgBin 'postgres.exe'))) {
    Write-Host 'Fetching PostgreSQL 18.7 server subset (verified against the archive central directory)...'
    python (Join-Path $PSScriptRoot 'fetch_server_subset.py') $pgHome (Join-Path $local 'tools/pgsql-18.7-1.subset-manifest.json')
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL binary fetch failed.' }
}

$version = & (Join-Path $pgBin 'postgres.exe') --version
if ($version -notmatch '\(PostgreSQL\) 18\.7$') { throw "Unexpected server version: $version" }

function New-Secret {
    $bytes = [System.Security.Cryptography.RandomNumberGenerator]::GetBytes(24)
    return [Convert]::ToBase64String($bytes).Replace('+', 'A').Replace('/', 'B').TrimEnd('=')
}

if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
} else {
    $settings = [pscustomobject]@{
        host = '127.0.0.1'
        port = $Port
        adminUser = 'eledgercare_admin'
        adminPassword = New-Secret
        migratorUser = 'eledgercare_migrator'
        migratorPassword = New-Secret
        appUser = 'eledgercare_app'
        appPassword = New-Secret
        devDatabase = 'eledgercare_product_dev'
    }
    $settings | ConvertTo-Json | Set-Content -Encoding utf8NoBOM $settingsPath
}

if (-not (Test-Path (Join-Path $data 'PG_VERSION'))) {
    $pwFile = Join-Path $secrets 'initdb-admin.pw'
    Set-Content -NoNewline -Encoding ascii $pwFile $settings.adminPassword
    try {
        & (Join-Path $pgBin 'initdb.exe') -D $data -U $settings.adminUser --pwfile=$pwFile `
            --auth=scram-sha-256 --encoding=UTF8 --no-locale | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'initdb failed.' }
    } finally {
        Remove-Item $pwFile -Force
    }

    # Owned, explicit settings appended to the generated configuration.
    @"

# --- eLedgerCare WP-0003 owned local cluster settings ---
listen_addresses = '127.0.0.1'
port = $($settings.port)
unix_socket_directories = ''
password_encryption = 'scram-sha-256'
fsync = on
full_page_writes = on
synchronous_commit = on
wal_level = replica
"@ | Add-Content -Encoding utf8NoBOM (Join-Path $data 'postgresql.conf')

    # Loopback TCP with scram-sha-256 only; no trust, peer or remote entries.
    @'
# TYPE  DATABASE  USER  ADDRESS        METHOD
host    all       all   127.0.0.1/32   scram-sha-256
'@ | Set-Content -Encoding utf8NoBOM (Join-Path $data 'pg_hba.conf')
}

& (Join-Path $PSScriptRoot 'start-cluster.ps1')

$env:PGPASSWORD = $settings.adminPassword
try {
    $psql = Join-Path $pgBin 'psql.exe'
    $common = @('-X', '-v', 'ON_ERROR_STOP=1', '-h', $settings.host, '-p', $settings.port, '-U', $settings.adminUser, '-d', 'postgres')
    $roleSql = @"
DO `$`$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$($settings.migratorUser)') THEN
    CREATE ROLE $($settings.migratorUser) LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$($settings.appUser)') THEN
    CREATE ROLE $($settings.appUser) LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END
`$`$;
"@
    $roleSql | & $psql @common -q -f - | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Role creation failed.' }
    # Passwords are sent over the loopback session via stdin, never on a command line.
    "ALTER ROLE $($settings.migratorUser) PASSWORD '$($settings.migratorPassword)';`nALTER ROLE $($settings.appUser) PASSWORD '$($settings.appPassword)';" |
        & $psql @common -q -f - | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Role password update failed.' }

    & $psql @common -A -t -c "SELECT name || '=' || setting FROM pg_settings WHERE name IN ('server_version','listen_addresses','port','fsync','full_page_writes','synchronous_commit','password_encryption','wal_level') ORDER BY name" | Out-Host
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host "Cluster ready on 127.0.0.1:$($settings.port). Settings: $settingsPath"
