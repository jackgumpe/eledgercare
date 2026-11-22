param(
    [ValidateSet('owners','review','coordination')][string]$Role = 'owners',
    [ValidatePattern('^[A-Za-z0-9-]+$')][string]$RunName = 'replay-1'
)
$ErrorActionPreference = 'Stop'
$env:CUDA_VISIBLE_DEVICES = '-1'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_DATASETS_OFFLINE = '1'
$env:PIP_NO_INDEX = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$runDir = Join-Path "C:/Users/jackg/eLedgerCare-Speed/WP-0027/$Role" $RunName
if (Test-Path -LiteralPath $runDir) { throw "Use a fresh run directory: $runDir" }
[void](New-Item -ItemType Directory -Path $runDir -Force)
foreach ($cacheVariable in @('TEMP','TMP','TMPDIR','HF_HOME','TORCH_HOME','XDG_CACHE_HOME','MPLCONFIGDIR','TRITON_CACHE_DIR','TORCHINDUCTOR_CACHE_DIR','NUMBA_CACHE_DIR','PIP_CACHE_DIR','CUDA_CACHE_PATH')) {
    $path = Join-Path $runDir $cacheVariable
    [void](New-Item -ItemType Directory -Path $path)
    [Environment]::SetEnvironmentVariable($cacheVariable, $path, 'Process')
}
& 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe' -I -B (Join-Path $PSScriptRoot replay.py) $runDir
exit $LASTEXITCODE
