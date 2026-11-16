#Requires -Version 7.0
<#
.SYNOPSIS
  Creates (if needed) an owned eLedgerCare database on the worktree cluster, applies EF migrations
  explicitly with the migration role through the project-local dotnet-ef tool, then grants the
  runtime role its minimal privileges and prints the effective privilege matrix.
.PARAMETER Database
  Database name; defaults to the development database from .local/secrets/pg-local.json.
#>
[CmdletBinding()]
param(
    [string] $Database
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$settings = Get-Content (Join-Path $root '.local/secrets/pg-local.json') -Raw | ConvertFrom-Json
if (-not $Database) { $Database = $settings.devDatabase }
if ($Database -notmatch '^[a-z][a-z0-9_]{0,62}$') { throw "Unsafe database name: $Database" }
$psql = Join-Path $root '.local/tools/pgsql-18.7-1/bin/psql.exe'

function Invoke-Psql([string] $user, [string] $password, [string] $db, [string] $sql, [switch] $Tuples) {
    $env:PGPASSWORD = $password
    try {
        $arguments = @('-X', '-q', '-v', 'ON_ERROR_STOP=1', '-h', $settings.host, '-p', $settings.port, '-U', $user, '-d', $db)
        if ($Tuples) { $arguments += @('-A', '-t') }
        $output = $sql | & $psql @arguments -f -
        if ($LASTEXITCODE -ne 0) { throw "psql failed as $user on $db" }
        return $output
    } finally {
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    }
}

$exists = Invoke-Psql $settings.adminUser $settings.adminPassword 'postgres' "SELECT 1 FROM pg_database WHERE datname = '$Database'" -Tuples
if (-not $exists) {
    Invoke-Psql $settings.adminUser $settings.adminPassword 'postgres' "CREATE DATABASE $Database OWNER $($settings.migratorUser) ENCODING 'UTF8' TEMPLATE template0" | Out-Null
}
Invoke-Psql $settings.adminUser $settings.adminPassword 'postgres' @"
REVOKE ALL ON DATABASE $Database FROM PUBLIC;
GRANT CONNECT ON DATABASE $Database TO $($settings.appUser);
"@ | Out-Null
Invoke-Psql $settings.adminUser $settings.adminPassword $Database 'REVOKE ALL ON SCHEMA public FROM PUBLIC;' | Out-Null

$env:ELEDGERCARE_MIGRATION_CONNECTION = "Host=$($settings.host);Port=$($settings.port);Database=$Database;Username=$($settings.migratorUser);Password=$($settings.migratorPassword)"
try {
    Push-Location $root
    dotnet tool run dotnet-ef database update --project src/ELedgerCare.Infrastructure --startup-project src/ELedgerCare.Infrastructure --configuration Release
    if ($LASTEXITCODE -ne 0) { throw 'dotnet-ef database update failed.' }
} finally {
    Pop-Location
    Remove-Item Env:ELEDGERCARE_MIGRATION_CONNECTION -ErrorAction SilentlyContinue
}

Invoke-Psql $settings.migratorUser $settings.migratorPassword $Database (Get-Content (Join-Path $PSScriptRoot 'grant-runtime.sql') -Raw) | Out-Null

Write-Host "Runtime privilege matrix for $($settings.appUser) on $Database (table: select insert table_update col_update delete truncate):"
Invoke-Psql $settings.adminUser $settings.adminPassword $Database @"
SELECT c.relname || ': ' ||
       has_table_privilege('$($settings.appUser)', c.oid, 'SELECT') || ' ' ||
       has_table_privilege('$($settings.appUser)', c.oid, 'INSERT') || ' ' ||
       has_table_privilege('$($settings.appUser)', c.oid, 'UPDATE') || ' ' ||
       has_any_column_privilege('$($settings.appUser)', c.oid, 'UPDATE') || ' ' ||
       has_table_privilege('$($settings.appUser)', c.oid, 'DELETE') || ' ' ||
       has_table_privilege('$($settings.appUser)', c.oid, 'TRUNCATE')
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'eledgercare' AND c.relkind = 'r' ORDER BY c.relname;
SELECT 'fencing_seq usage/select: ' ||
       has_sequence_privilege('$($settings.appUser)', 'eledgercare.extraction_fencing_seq', 'USAGE') || ' ' ||
       has_sequence_privilege('$($settings.appUser)', 'eledgercare.extraction_fencing_seq', 'SELECT');
SELECT 'schema create for app: ' || has_schema_privilege('$($settings.appUser)', 'eledgercare', 'CREATE');
SELECT 'migrations: ' || string_agg("MigrationId", ', ') FROM eledgercare.__ef_migrations_history;
"@ -Tuples | Out-Host
