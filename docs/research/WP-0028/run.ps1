param(
    [ValidateSet('probe','review','coordination')][string]$Role = 'probe',
    [ValidatePattern('^[A-Za-z0-9-]+$')][string]$RunName = 'replay',
    [ValidateSet('historical','controlled')][string]$Mode = 'historical',
    [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{40}$')][string]$Candidate,
    [ValidatePattern('^$|^[a-f0-9]{40}$')][string]$FixtureRevision = ''
)
$ErrorActionPreference = 'Stop'
$env:CUDA_VISIBLE_DEVICES = '-1'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:PIP_NO_INDEX = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$runDir = Join-Path "C:/Users/jackg/eLedgerCare-Speed/WP-0028/$Role" $RunName
if (Test-Path -LiteralPath $runDir) { throw "Use a fresh run directory: $runDir" }
[void](New-Item -ItemType Directory -Path $runDir -Force)
foreach ($cacheName in @('TEMP','TMP','TMPDIR','HF_HOME','TORCH_HOME','XDG_CACHE_HOME','MPLCONFIGDIR','TRITON_CACHE_DIR','TORCHINDUCTOR_CACHE_DIR','NUMBA_CACHE_DIR','PIP_CACHE_DIR','CUDA_CACHE_PATH')) {
    $cacheDir = Join-Path $runDir $cacheName
    [void](New-Item -ItemType Directory -Path $cacheDir)
    [Environment]::SetEnvironmentVariable($cacheName, $cacheDir, 'Process')
}
$arguments = @('-I','-B',(Join-Path $PSScriptRoot replay.py),$runDir,$Mode,$Candidate)
if ($FixtureRevision) { $arguments += $FixtureRevision }
& 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe' @arguments
exit $LASTEXITCODE
