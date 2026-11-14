#Requires -Version 7.0
<#
.SYNOPSIS
  Demo receipt for F1 on the persistent development database: submit the synthetic fixture through the
  real API on 127.0.0.1:5180, terminate and restart only that API process, then (additionally) perform a
  fast stop/start of the owned PostgreSQL cluster, re-verifying reference, status and original bytes.
.DESCRIPTION
  Writes a compact JSON receipt to -ReceiptPath (default .scratch/demo-receipt.json). Contains no
  credentials or document contents. An application or database-service restart is not a power-loss test.
#>
[CmdletBinding()]
param(
    [string] $ReceiptPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if (-not $ReceiptPath) { $ReceiptPath = Join-Path $root '.scratch/demo-receipt.json' }
$settings = Get-Content (Join-Path $root '.local/secrets/pg-local.json') -Raw | ConvertFrom-Json
$apiDir = Join-Path $root 'src/ELedgerCare.Api/bin/Release/net10.0'
$fixture = Join-Path $root 'tests/fixtures/F1-SWO-001.pdf'
$fixtureBytes = [IO.File]::ReadAllBytes($fixture)
$fixtureSha = [Convert]::ToHexStringLower([Security.Cryptography.SHA256]::HashData($fixtureBytes))
$base = 'http://127.0.0.1:5180'
$log = Join-Path $root '.scratch/demo-api.log'

function Start-OwnedApi {
    if (Get-NetTCPConnection -State Listen -LocalPort 5180 -ErrorAction SilentlyContinue) {
        throw 'Port 5180 is already bound; not starting (not ours).'
    }
    $env:ConnectionStrings__Runtime = "Host=$($settings.host);Port=$($settings.port);Database=$($settings.devDatabase);Username=$($settings.appUser);Password=$($settings.appPassword)"
    $env:ASPNETCORE_ENVIRONMENT = 'Production'
    try {
        $process = Start-Process -FilePath dotnet -ArgumentList "`"$apiDir/ELedgerCare.Api.dll`"" -WorkingDirectory $apiDir `
            -WindowStyle Hidden -PassThru -RedirectStandardOutput $log
    } finally {
        Remove-Item Env:ConnectionStrings__Runtime -ErrorAction SilentlyContinue
    }
    $deadline = (Get-Date).AddSeconds(60)
    while (-not (Get-NetTCPConnection -State Listen -LocalPort 5180 -ErrorAction SilentlyContinue | Where-Object OwningProcess -eq $process.Id)) {
        if ($process.HasExited -or (Get-Date) -gt $deadline) { throw 'API did not start listening on 5180.' }
        Start-Sleep -Milliseconds 200
    }
    return [pscustomobject]@{ Process = $process; Pid = $process.Id; StartUtc = $process.StartTime.ToUniversalTime().ToString('o') }
}

function Stop-OwnedApi($api) {
    $current = Get-Process -Id $api.Pid -ErrorAction SilentlyContinue
    if ($current -and $current.StartTime.ToUniversalTime().ToString('o') -eq $api.StartUtc) {
        Stop-Process -Id $api.Pid -Force   # abrupt termination of exactly the process this script started
        $api.Process.WaitForExit()
    } else {
        throw "PID $($api.Pid) no longer identifies the API started by this script; not stopping it."
    }
}

$client = [Net.Http.HttpClient]::new()
function Get-Receipt([string] $path) {
    $response = $client.GetAsync("$base$path").GetAwaiter().GetResult()
    if (-not $response.IsSuccessStatusCode) { throw "GET $path returned $([int]$response.StatusCode)" }
    return $response.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json
}
function Get-OriginalSha([string] $url) {
    $bytes = $client.GetByteArrayAsync("$base$url").GetAwaiter().GetResult()
    return [Convert]::ToHexStringLower([Security.Cryptography.SHA256]::HashData($bytes))
}

$key = [guid]::NewGuid().ToString('D')
$first = Start-OwnedApi
$content = [Net.Http.ByteArrayContent]::new($fixtureBytes)
$content.Headers.ContentType = [Net.Http.Headers.MediaTypeHeaderValue]::new('application/pdf')
$request = [Net.Http.HttpRequestMessage]::new([Net.Http.HttpMethod]::Post, "$base/api/documents")
$request.Headers.Add('Idempotency-Key', $key)
$request.Content = $content
$post = $client.SendAsync($request).GetAwaiter().GetResult()
$submitted = $post.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json
if ([int]$post.StatusCode -ne 201) { throw "Submission returned $([int]$post.StatusCode)" }
Stop-OwnedApi $first

$second = Start-OwnedApi
$afterApiRestart = Get-Receipt "/api/documents/$($submitted.documentId)"
$shaAfterApiRestart = Get-OriginalSha $afterApiRestart.originalUrl
Stop-OwnedApi $second

# Additional boundary (beyond DI-04): fast stop/start of the owned PostgreSQL cluster.
& (Join-Path $root 'deploy/dev/postgres/stop-cluster.ps1')
& (Join-Path $root 'deploy/dev/postgres/start-cluster.ps1')
$postmasterPid = [int](Get-Content (Join-Path $root '.local/postgres-data/postmaster.pid') -TotalCount 1)

$third = Start-OwnedApi
$afterDbRestart = Get-Receipt "/api/submissions/$key"
$shaAfterDbRestart = Get-OriginalSha $afterDbRestart.originalUrl
Stop-OwnedApi $third

$ok = ($afterApiRestart.documentId -eq $submitted.documentId) -and ($afterDbRestart.documentId -eq $submitted.documentId) -and
      ($shaAfterApiRestart -eq $fixtureSha) -and ($shaAfterDbRestart -eq $fixtureSha) -and
      ($afterApiRestart.status -eq 'awaiting_extraction') -and ($afterDbRestart.status -eq 'awaiting_extraction')

$receipt = [ordered]@{
    fixtureId = 'F1-SWO-001'
    fixtureSha256 = $fixtureSha
    fixtureBytes = $fixtureBytes.Length
    database = $settings.devDatabase
    submit = [ordered]@{ status = [int]$post.StatusCode; documentId = $submitted.documentId; jobId = $submitted.jobId; receiptStatus = $submitted.status; sha256 = $submitted.sha256 }
    apiProcesses = @(
        [ordered]@{ pid = $first.Pid; startUtc = $first.StartUtc; role = 'submit, then terminated' },
        [ordered]@{ pid = $second.Pid; startUtc = $second.StartUtc; role = 'after API restart' },
        [ordered]@{ pid = $third.Pid; startUtc = $third.StartUtc; role = 'after PostgreSQL fast restart' })
    afterApiRestart = [ordered]@{ documentId = $afterApiRestart.documentId; status = $afterApiRestart.status; originalSha256 = $shaAfterApiRestart }
    afterPostgresRestart = [ordered]@{ postmasterPid = $postmasterPid; documentId = $afterDbRestart.documentId; status = $afterDbRestart.status; originalSha256 = $shaAfterDbRestart }
    allMatch = $ok
    limits = 'Application and database-service restarts only; not a power-loss, OS-crash or backup test.'
}
New-Item -ItemType Directory -Force (Split-Path $ReceiptPath) | Out-Null
$receipt | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8NoBOM $ReceiptPath
$receipt | ConvertTo-Json -Depth 5
if (-not $ok) { exit 1 }
