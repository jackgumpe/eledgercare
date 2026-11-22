param(
    [Parameter(Mandatory)][string]$Run,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')][string]$Candidate
)
$ErrorActionPreference = 'Stop'
$runPath = [IO.Path]::GetFullPath($Run)
$packetPath = 'C:\Users\jackg\eLedgerCare-Speed\WP-0027'
$ownerPaths = @((Join-Path $packetPath 'reader'), (Join-Path $packetPath 'review'))
if ([IO.Path]::GetDirectoryName($runPath) -notin $ownerPaths -or (Test-Path -LiteralPath $runPath)) {
    throw 'Use a fresh run directory directly under the assigned reader or review scratch.'
}
$cache = Join-Path $runPath cache
New-Item -ItemType Directory -Path $cache | Out-Null
$env:CUDA_VISIBLE_DEVICES = '-1'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
$env:TOKENIZERS_PARALLELISM = 'false'
$cacheKeys = 'TEMP','TMP','TMPDIR','HF_HOME','HF_HUB_CACHE','HF_ASSETS_CACHE','TRANSFORMERS_CACHE',
             'TORCH_HOME','XDG_CACHE_HOME','MPLCONFIGDIR','NUMBA_CACHE_DIR','LOCALAPPDATA','APPDATA',
             'PYTHONPYCACHEPREFIX','TORCH_EXTENSIONS_DIR','TRITON_HOME','HF_MODULES_CACHE'
foreach ($key in $cacheKeys) {
    [Environment]::SetEnvironmentVariable($key,$cache,'Process')
}
$python = 'C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe'
& $python -I -B (Join-Path $PSScriptRoot 'replay.py') $runPath $Candidate
exit $LASTEXITCODE
