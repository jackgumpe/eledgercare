param(
    [ValidateSet('scoring','review','coordination')][string]$Role = 'scoring',
    [Parameter(Mandatory)][ValidatePattern('^[A-Za-z0-9-]+$')][string]$RunName,
    [Parameter(Mandatory)][ValidateSet('controls','released')][string]$Mode,
    [Parameter(Mandatory)][ValidatePattern('^[a-f0-9]{40}$')][string]$Candidate,
    [ValidatePattern('^[a-f0-9]{40}$')][string]$GateRevision,
    [ValidatePattern('^[a-f0-9]{64}$')][string]$GateSha256
)
$ErrorActionPreference = 'Stop'
if ($Mode -eq 'released' -and (!$GateRevision -or !$GateSha256)) { throw 'Independent gate reference required' }
if ($Mode -eq 'controls' -and ($GateRevision -or $GateSha256)) { throw 'Controls take no gate' }
if ($RunName -eq '.' -or $RunName -eq '..') { throw 'Invalid run name' }
$env:CUDA_VISIBLE_DEVICES = '-1'
foreach ($key in @('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_DATASETS_OFFLINE','PIP_NO_INDEX','OMP_NUM_THREADS','MKL_NUM_THREADS')) {
    [Environment]::SetEnvironmentVariable($key,'1','Process')
}
$runDir = Join-Path "C:/Users/jackg/eLedgerCare-Speed/WP-0029/$Role" $RunName
if (Test-Path -LiteralPath $runDir) { throw "Run directory must be fresh: $runDir" }
[void](New-Item -ItemType Directory -Path $runDir -Force)
foreach ($key in @('TEMP','TMP','TMPDIR','HF_HOME','TORCH_HOME','XDG_CACHE_HOME','MPLCONFIGDIR','TRITON_CACHE_DIR','TORCHINDUCTOR_CACHE_DIR','NUMBA_CACHE_DIR','PIP_CACHE_DIR','CUDA_CACHE_PATH')) {
    $cache = Join-Path $runDir $key
    [void](New-Item -ItemType Directory -Path $cache)
    [Environment]::SetEnvironmentVariable($key,$cache,'Process')
}
$arguments = @('-I','-B',(Join-Path $PSScriptRoot 'scoring.py'),$runDir,$Mode,$Candidate)
if ($Mode -eq 'released') { $arguments += @($GateRevision,$GateSha256) }
& 'C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe' @arguments
exit $LASTEXITCODE
