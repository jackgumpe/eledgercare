param(
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')][string]$Candidate,
    [Parameter(Mandatory)][ValidatePattern('^attempt-[0-9]{2}$')][string]$RunName
)
$ErrorActionPreference = 'Stop'
$runDir = Join-Path 'C:/Users/jackg/eLedgerCare-Speed/WP-0036/author' $RunName
if (Test-Path -LiteralPath $runDir) { throw "Existing attempt $runDir" }
$null = New-Item -ItemType Directory -Path $runDir
$env:CUDA_VISIBLE_DEVICES = '-1'
foreach ($name in @('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS','HF_HUB_OFFLINE','HF_DATASETS_OFFLINE','TRANSFORMERS_OFFLINE','PIP_NO_INDEX')) {
    [Environment]::SetEnvironmentVariable($name,'1','Process')
}
foreach ($name in @('TEMP','TMP','TMPDIR','HF_HOME','TORCH_HOME','XDG_CACHE_HOME','TORCHINDUCTOR_CACHE_DIR','PIP_CACHE_DIR')) {
    $dir = Join-Path $runDir $name
    $null = New-Item -ItemType Directory -Path $dir
    [Environment]::SetEnvironmentVariable($name,$dir,'Process')
}
$py = 'C:/Users/jackg/eLedgerCare-Speed/WP-0030/runtime/venv/Scripts/python.exe'
& $py -I -B (Join-Path $PSScriptRoot 'trial.py') $Candidate $runDir > (Join-Path $runDir 'stdout.txt') 2> (Join-Path $runDir 'stderr.txt')
$code = $LASTEXITCODE
[IO.File]::WriteAllText((Join-Path $runDir 'exit.txt'),[string]$code)
exit $code
