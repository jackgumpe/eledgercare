# eLedgerCare

An on-premises intranet document application. The first customer feature is to retain a submitted maintenance PDF, its original bytes, and its honest processing status across an application restart. Demonstration target: 26 November 2026.

This is a **provisional coordination seed**. Jack approved the direction; the contract and detailed design have not yet received independent technical acceptance. No application is implemented or released by this seed.

Start with [START_HERE.md](START_HERE.md). Current assignments are in [CURRENT.md](CURRENT.md); packet and report reservations are in [INDEX.md](INDEX.md).

Direction: ASP.NET Core 10, Angular 22, EF Core/Npgsql 10, PostgreSQL, and a later separately qualified local Python OCR worker. Product and research have separate dependency graphs and environments. There will be one production .NET solution.

Source is private unless Jack explicitly changes that decision. Public fixtures do not authorize public source publication. Do not place customer documents, secrets, database contents, uploads, model weights, or large corpora in Git.

## Local development setup (WP-0003 F1 candidate — ready for independent review, not accepted)

Local-only, Windows, PowerShell 7. Nothing is installed machine-wide; tools, data, logs and generated
credentials live in the ignored `.local/` directory of your worktree. Ports: API 5180, UI 4200,
PostgreSQL 55432 (bind 127.0.0.1; check they are free and use different ports in another worktree).

Prerequisites already on the machine: .NET SDK 10.0.403 (pinned by `global.json`, roll-forward disabled),
Node 24.18.0 / npm 11.16.0, Python 3.12 (standard library only, used by the PostgreSQL fetch script),
Microsoft Edge (browser checks only).

```powershell
# 1. .NET tool + packages (restored into .local/nuget/packages via NuGet.Config)
dotnet tool restore
dotnet restore ELedgerCare.slnx --locked-mode
dotnet build ELedgerCare.slnx -c Release --no-restore

# 2. Owned PostgreSQL 18.7 cluster (fetches the verified server subset of the official EDB archive,
#    initdb with scram-sha-256, 127.0.0.1:55432, fsync/full_page_writes/synchronous_commit on)
pwsh deploy/dev/postgres/setup-cluster.ps1          # add -Port 55433 for a second worktree
pwsh deploy/dev/database/prepare-database.ps1       # explicit dotnet-ef migration + runtime grants

# 3. Tests: unit, PdfPig admission, real PostgreSQL + real API process acceptance
$env:TESTINGPLATFORM_TELEMETRY_OPTOUT = '1'
dotnet test --solution ELedgerCare.slnx -c Release --no-build

# 4. Web UI (npm cache kept in .local)
$env:npm_config_cache = "$PWD\.local\npm-cache"
Push-Location web; npm ci; npx ng build; Pop-Location
pwsh evaluation/product-smoke/run-browser-checks.ps1   # Playwright on msedge, fresh eledgercare_e2e database
pwsh evaluation/product-smoke/run-demo-smoke.ps1       # restart receipt on eledgercare_product_dev

# Run the app manually: API (runtime role credentials from .local/secrets/pg-local.json) + UI
#   $env:ConnectionStrings__Runtime = "Host=127.0.0.1;Port=55432;Database=eledgercare_product_dev;Username=eledgercare_app;Password=<from pg-local.json>"
#   dotnet src/ELedgerCare.Api/bin/Release/net10.0/ELedgerCare.Api.dll
#   cd web; npm start      # http://127.0.0.1:4200, /api proxied to 127.0.0.1:5180
pwsh deploy/dev/postgres/stop-cluster.ps1
```

Implementation map: [docs/product/F1-durable-intake-implementation.md](docs/product/F1-durable-intake-implementation.md).
Synthetic fixture provenance: [tests/fixtures/README.md](tests/fixtures/README.md).
