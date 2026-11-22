param(
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')][string]$Candidate,
    [Parameter(Mandatory)][ValidatePattern('^[A-Za-z0-9-]+$')][string]$RunName
)
$ErrorActionPreference = 'Stop'
$packet = 'C:/Users/jackg/eLedgerCare-Speed/WP-0030'
$python = Join-Path $packet 'runtime/venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw 'Bound CPU interpreter missing' }
$run = Join-Path (Join-Path $packet 'trace') $RunName
if (Test-Path -LiteralPath $run) { throw "Run directory already exists $run" }
$null = New-Item -ItemType Directory -Path $run
$env:CUDA_VISIBLE_DEVICES = '-1'
foreach ($name in @('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_DATASETS_OFFLINE','PIP_NO_INDEX','OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS')) {
    [Environment]::SetEnvironmentVariable($name, '1', 'Process')
}
foreach ($name in @('TEMP','TMP','TMPDIR','HF_HOME','TORCH_HOME','XDG_CACHE_HOME','TORCHINDUCTOR_CACHE_DIR','PIP_CACHE_DIR')) {
    $cache = Join-Path $run $name
    $null = New-Item -ItemType Directory -Path $cache
    [Environment]::SetEnvironmentVariable($name, $cache, 'Process')
}
& $python -I -B (Join-Path $PSScriptRoot 'trace.py') $Candidate $run
exit $LASTEXITCODE
