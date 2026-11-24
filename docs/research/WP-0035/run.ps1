param(
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')][string]$Candidate,
    [Parameter(Mandatory)][ValidatePattern('^attempt-[0-9]{2}$')][string]$RunName
)
$ErrorActionPreference = 'Stop'
$work = Join-Path 'C:/Users/jackg/eLedgerCare-Speed/WP-0035/author' $RunName
if (Test-Path -LiteralPath $work) { throw "Attempt exists $work" }
$null = New-Item -ItemType Directory -Path $work
$env:CUDA_VISIBLE_DEVICES = '-1'
foreach ($flag in @('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_DATASETS_OFFLINE','PIP_NO_INDEX','OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS')) {
    [Environment]::SetEnvironmentVariable($flag,'1','Process')
}
foreach ($flag in @('TEMP','TMP','TMPDIR','HF_HOME','TORCH_HOME','XDG_CACHE_HOME','TORCHINDUCTOR_CACHE_DIR','PIP_CACHE_DIR')) {
    $p = Join-Path $work $flag
    $null = New-Item -ItemType Directory -Path $p
    [Environment]::SetEnvironmentVariable($flag,$p,'Process')
}
$py = 'C:/Users/jackg/eLedgerCare-Speed/WP-0030/runtime/venv/Scripts/python.exe'
& $py -I -B (Join-Path $PSScriptRoot 'trial.py') $Candidate $work > (Join-Path $work 'stdout.txt') 2> (Join-Path $work 'stderr.txt')
$code = $LASTEXITCODE
[IO.File]::WriteAllText((Join-Path $work 'exit.txt'),[string]$code)
exit $code
