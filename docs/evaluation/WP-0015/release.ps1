# Run only under the coordinator's source-bound reviewer release. No implicit key lookup.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('H','A','B')][string]$Family,
    [Parameter(Mandatory)][ValidateSet('input','scoring')][string]$Stage,
    [Parameter(Mandatory)][string]$SealedDirectory,
    [Parameter(Mandatory)][string]$KeyFile,
    [Parameter(Mandatory)][string]$Destination
)
$ErrorActionPreference = 'Stop'
$manifest = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'commitments.json') | ConvertFrom-Json -AsHashtable
$item = $manifest.packets[$Family]
$sealed = $item.sealed[$Stage]
$source = Join-Path $SealedDirectory $sealed.name
if ((Get-FileHash -LiteralPath $source).Hash.ToLowerInvariant() -ne $sealed.sha256) {throw 'Ciphertext digest mismatch'}
$target = [IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $target) {throw 'Use a new release directory'}
$packetKey = [Security.Cryptography.ProtectedData]::Unprotect([IO.File]::ReadAllBytes($KeyFile), $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
$body = [IO.File]::ReadAllBytes($source)
$cipher = [byte[]]::new($body.Length - 28)
[Array]::Copy($body,28,$cipher,0,$cipher.Length)
$plain = [byte[]]::new($cipher.Length)
$aes = [Security.Cryptography.AesGcm]::new($packetKey,16)
try {
    $aes.Decrypt([byte[]]$body[0..11],$cipher,[byte[]]$body[12..27],$plain)
} finally {
    $aes.Dispose()
    [Array]::Clear($packetKey,0,$packetKey.Length)
}
$archive = [IO.Compression.ZipArchive]::new([IO.MemoryStream]::new($plain),[IO.Compression.ZipArchiveMode]::Read)
try {
    $names = if ($Stage -eq 'input') {@('source.pdf')} else {@('truth.json','rasters.json')}
    if ($archive.Entries.Count -ne @($names).Count) {throw 'Incorrect package entry count'}
    $contents = @{}
    foreach ($name in $names) {
        $entry = $archive.GetEntry($name)
        if ($null -eq $entry) {throw "Missing $name"}
        $stream = $entry.Open()
        $memory = [IO.MemoryStream]::new()
        try {
            $stream.CopyTo($memory)
            $buffer = $memory.ToArray()
        } finally {
            $stream.Dispose()
            $memory.Dispose()
        }
        $digest = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($buffer)).ToLowerInvariant()
        if ($digest -ne $item.files[$name]) {throw "Invalid commitment for $name"}
        $contents[$name] = $buffer
    }
    [IO.Directory]::CreateDirectory($target) | Out-Null
    foreach ($name in $names) {
        $file = [IO.File]::Open((Join-Path $target $name),[IO.FileMode]::CreateNew)
        try {$file.Write($contents[$name])} finally {$file.Dispose()}
    }
    Get-ChildItem -LiteralPath $target -File | Get-FileHash | Select-Object Path,Hash
} finally {
    $archive.Dispose()
    [Array]::Clear($plain,0,$plain.Length)
}
