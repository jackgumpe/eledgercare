# Source snapshot integrity only; never imports upstream code or accesses network/GPU.
$ErrorActionPreference = 'Stop'
$records = @(Get-Content -LiteralPath research/astra/source-manifest.json -Raw | ConvertFrom-Json)
$tree = @(Get-Content -LiteralPath research/astra/sources/hf-tree.json -Raw | ConvertFrom-Json)
$paths = @{}
$gitChecks = 0
foreach ($record in $records) {
    if (-not $record.path.StartsWith('research/astra/sources/') -or $record.path.Contains('..')) { throw "Out-of-scope path: $($record.path)" }
    if ($paths.ContainsKey($record.path)) { throw "Duplicate manifest path: $($record.path)" }
    $paths[$record.path] = $true
    $item = Get-Item -LiteralPath $record.path
    if ($item.Length -ne $record.bytes) { throw "Size mismatch: $($record.path)" }
    $sha = (Get-FileHash -LiteralPath $record.path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($sha -ne $record.sha256) { throw "SHA-256 mismatch: $($record.path)" }
    $blob = $record.git_blob
    if ($record.origin -like 'https://huggingface.co/baidu/Unlimited-OCR-2/resolve/*') {
        $name = ($record.origin -split '/')[-1]
        $entry = @($tree | Where-Object { $_.path -eq $name })
        if ($entry.Count -ne 1 -or $entry[0].lfs) { throw "Expected one plain source object: $name" }
        $blob = $entry[0].oid
    }
    if ($blob) {
        $actual = git hash-object -- $record.path
        if ($LASTEXITCODE -ne 0 -or $actual -ne $blob) { throw "Git blob mismatch: $($record.path)" }
        $gitChecks++
    }
}
$actualFiles = @(Get-ChildItem -LiteralPath research/astra/sources -File)
if ($actualFiles.Count -ne $records.Count) { throw 'Unmanifested or missing snapshot file' }
$public = @(Get-Content -LiteralPath research/astra/sources/public-candidate-metadata.json -Raw | ConvertFrom-Json)
if ($public.Count -ne 2) { throw 'Public candidate metadata count changed' }
$weights = @($tree | Where-Object { $_.path -like '*.safetensors' })
$weightBytes = ($weights | Measure-Object -Property size -Sum).Sum
if ($weightBytes -ne 6688305576) { throw 'Advertised weight-byte arithmetic mismatch' }
Write-Output "PASS: $($records.Count) snapshot SHA-256/size checks; $gitChecks upstream Git blob matches; 2 public metadata records; advertised weight total $weightBytes bytes. No upstream code executed."
