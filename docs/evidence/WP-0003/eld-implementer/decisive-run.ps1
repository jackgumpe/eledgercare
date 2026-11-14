#Requires -Version 7.0
# Decisive WP-0003 author checks against the frozen candidate. Scratch tool (ignored .scratch/); outputs in .scratch/decisive.
$ErrorActionPreference = 'Continue'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $root
$out = Join-Path $root '.scratch/decisive'
Remove-Item -Recurse -Force $out -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $out | Out-Null
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'; $env:DOTNET_NOLOGO = '1'; $env:TESTINGPLATFORM_TELEMETRY_OPTOUT = '1'
$env:npm_config_cache = Join-Path $root '.local/npm-cache'; $env:NG_CLI_ANALYTICS = 'false'
$summary = [ordered]@{ startedUtc = (Get-Date).ToUniversalTime().ToString('o') }

function Step([string] $name, [scriptblock] $body) {
    $file = Join-Path $out "$name.txt"
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $body *> $file
    $code = $LASTEXITCODE
    $summary[$name] = [ordered]@{ exit = $code; seconds = [math]::Round($sw.Elapsed.TotalSeconds, 1); log = "$name.txt" }
    "$name exit=$code ($([math]::Round($sw.Elapsed.TotalSeconds,1)) s)" | Tee-Object -Append (Join-Path $out 'steps.txt')
}

$summary.head = (git rev-parse HEAD)
$summary.branch = (git branch --show-current)
$summary.statusPorcelain = @(git status --porcelain=v1)
$summary.dotnetVersion = (dotnet --version)
$summary.runtimes = @(dotnet --list-runtimes)
$summary.node = (node --version); $summary.npm = (npm --version)

# Clean build outputs so nothing stale is tested.
Get-ChildItem -Path src, tests -Directory -Recurse -Include bin, obj | Remove-Item -Recurse -Force
Remove-Item -Recurse -Force web/dist, web/.angular -ErrorAction SilentlyContinue

Step '01-tool-restore' { dotnet tool restore }
Step '02-restore-locked' { dotnet restore ELedgerCare.slnx --locked-mode }
Step '03-build' { dotnet build ELedgerCare.slnx -c Release --no-restore }
Step '04-npm-ci' { Push-Location web; npm ci --no-audit; $c = $LASTEXITCODE; Pop-Location; $global:LASTEXITCODE = $c }
Step '05-ng-build' { Push-Location web; npx ng build; $c = $LASTEXITCODE; Pop-Location; $global:LASTEXITCODE = $c }

$settings = Get-Content .local/secrets/pg-local.json -Raw | ConvertFrom-Json
$candidateDb = 'eledgercare_candidate_' + $summary.head.Substring(0, 7)
$env:PGPASSWORD = $settings.adminPassword
"DROP DATABASE IF EXISTS $candidateDb WITH (FORCE);" | & .local/tools/pgsql-18.7-1/bin/psql.exe -X -q -h $settings.host -p $settings.port -U $settings.adminUser -d postgres -f - *> $null
Remove-Item Env:PGPASSWORD
Step '06-migrate-fresh-db' { pwsh -NoProfile -File deploy/dev/database/prepare-database.ps1 -Database $candidateDb }

$logStart = (Get-Item .local/logs/postgres.log).Length
$env:ELEDGERCARE_EVIDENCE_FILE = Join-Path $out 'acceptance-evidence.jsonl'
Step '07-dotnet-test' { dotnet test --solution ELedgerCare.slnx -c Release --no-build }
Remove-Item Env:ELEDGERCARE_EVIDENCE_FILE

Remove-Item -Recurse -Force .scratch/playwright -ErrorAction SilentlyContinue
Step '08-browser' { pwsh -NoProfile -File evaluation/product-smoke/run-browser-checks.ps1 }
Copy-Item .scratch/playwright/browser-evidence.json, .scratch/playwright/results.json $out -ErrorAction SilentlyContinue

Step '09-demo-smoke' { pwsh -NoProfile -File evaluation/product-smoke/run-demo-smoke.ps1 -ReceiptPath (Join-Path $out 'demo-receipt.json') }

# Server log lines produced during the run that concern the idempotency key race (count only).
$fs = [IO.File]::Open((Resolve-Path .local/logs/postgres.log), 'Open', 'Read', 'ReadWrite')
$fs.Seek($logStart, 'Begin') | Out-Null
$runLog = [IO.StreamReader]::new($fs).ReadToEnd(); $fs.Dispose()
$summary.serverLogDuplicateKeyErrors = ([regex]::Matches($runLog, 'duplicate key value violates unique constraint "ux_documents_idempotency_key"')).Count
$summary.serverLogFatalOrPanic = ([regex]::Matches($runLog, '(FATAL|PANIC):')).Count
($runLog -split "`n" | Select-String -Pattern 'ERROR:|FATAL:|PANIC:|checkpoint|shut down|ready to accept' | Select-Object -Last 60) -join "`n" |
    Set-Content (Join-Path $out 'postgres-log-excerpt.txt')

Step '10-publish' { dotnet publish src/ELedgerCare.Api/ELedgerCare.Api.csproj -c Release --no-restore -o (Join-Path $root '.scratch/decisive-publish') }
$summary.publishFiles = @(Get-ChildItem .scratch/decisive-publish -Recurse -File | ForEach-Object { $_.FullName.Substring((Resolve-Path .scratch/decisive-publish).Path.Length + 1) } | Sort-Object)
$summary.keyAssemblyVersions = [ordered]@{}
foreach ($dll in 'Microsoft.EntityFrameworkCore.dll', 'Microsoft.EntityFrameworkCore.Relational.dll', 'Npgsql.EntityFrameworkCore.PostgreSQL.dll', 'Npgsql.dll', 'UglyToad.PdfPig.dll') {
    $summary.keyAssemblyVersions[$dll] = (Get-Item (Join-Path '.scratch/decisive-publish' $dll)).VersionInfo.FileVersion
}
$summary.apiRuntimeConfig = Get-Content .scratch/decisive-publish/ELedgerCare.Api.runtimeconfig.json -Raw | ConvertFrom-Json

$postmasterPid = [int](Get-Content .local/postgres-data/postmaster.pid -TotalCount 1)
$summary.postmaster = [ordered]@{ pid = $postmasterPid; startUtc = (Get-Process -Id $postmasterPid).StartTime.ToUniversalTime().ToString('o') }
$summary.listenersAfter = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object LocalPort -in 5180, 4200, 55432 |
    ForEach-Object { "$($_.LocalAddress):$($_.LocalPort) pid=$($_.OwningProcess) $((Get-Process -Id $_.OwningProcess).ProcessName)" })
$summary.finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
$summary | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $out 'summary.json')
"done"
