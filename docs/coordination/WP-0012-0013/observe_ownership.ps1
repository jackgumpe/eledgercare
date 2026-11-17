# Adapted from unchanged WP-0011 observer: output boundary and mapping_v2 process recognition only.
param([Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference='Stop'
$coverageRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$coverageBoundaries=@('WP-0012-0013','WP-0012','WP-0013') | ForEach-Object {[IO.Path]::GetFullPath((Join-Path $coverageRoot ('docs/coordination/'+$_)))+[IO.Path]::DirectorySeparatorChar}
$coverageTarget=[IO.Path]::GetFullPath((Join-Path $coverageRoot $Out))
if(-not @($coverageBoundaries | Where-Object {$coverageTarget.StartsWith($_,[StringComparison]::OrdinalIgnoreCase)}).Count -or (Test-Path -LiteralPath $coverageTarget)){
    throw 'Require a new file beneath the WP-0012/WP-0013 coordinator directories'
}
if(-not (Test-Path -LiteralPath ([IO.Path]::GetDirectoryName($coverageTarget)))){
    throw 'Observation parent directory must already exist'
}
$coverageProtocol=Get-Content -LiteralPath (Join-Path $coverageRoot 'qualification/coverage_v1/protocol.json') -Raw | ConvertFrom-Json
$coverageGpu=@(& nvidia-smi ('--id='+$coverageProtocol.gpu.uuid) '--query-gpu=timestamp,uuid,name,driver_version,compute_cap,memory.total,memory.used,memory.free,utilization.gpu,pstate' '--format=csv,noheader,nounits' 2>&1 | ForEach-Object {$_.ToString()})
$coverageGpuExit=$LASTEXITCODE
$coverageApps=@(& nvidia-smi ('--id='+$coverageProtocol.gpu.uuid) '--query-compute-apps=pid,process_name,used_memory' '--format=csv,noheader,nounits' 2>&1 | ForEach-Object {$_.ToString()})
$coverageAppsExit=$LASTEXITCODE
$coverageListedPids=@($coverageApps | ForEach-Object {if($_ -match '^\s*(\d+)\s*,'){[int]$Matches[1]}})
$coverageProcesses=@(Get-CimInstance Win32_Process | Where-Object {
    $_.ProcessId -in $coverageListedPids -or
    $_.Name -match '^(python(w)?|ollama|llama(-server|-cli)?|vllm|lm.?studio|koboldcpp)\.exe$' -or
    $_.CommandLine -match '(qualification[/\\](coverage_v1|mapping_v1|mapping_v2|baseline)|q0harness|eledgercare_worker)'
} | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CreationDate)
$coverageOllama=Get-Command ollama -ErrorAction SilentlyContinue
$coverageOllamaResult=$null
$coverageOllamaExit=$null
if($coverageOllama){
    $coverageOllamaResult=@(& $coverageOllama.Source ps 2>&1 | ForEach-Object {$_.ToString()})
    $coverageOllamaExit=$LASTEXITCODE
}
$coverageObservation=[ordered]@{
    schema='eld-wp12-wp13-ownership-observation/1'
    observed_utc=[DateTime]::UtcNow.ToString('o')
    gpu_exit=$coverageGpuExit
    gpu=$coverageGpu
    apps_exit=$coverageAppsExit
    apps=$coverageApps
    candidate_and_gpu_processes=$coverageProcesses
    ollama_ps_exit=$coverageOllamaExit
    ollama_ps=$coverageOllamaResult
    note='Read-only snapshot. No full command lines, environment, process termination or lease grant. Root must reconcile active leases and process ownership separately. Desktop sharing/WDDM unavailable memory do not establish hardware exclusivity.'
}
[IO.File]::WriteAllText($coverageTarget,($coverageObservation|ConvertTo-Json -Depth 8)+[Environment]::NewLine,[Text.UTF8Encoding]::new($false))
[pscustomobject]@{out=$Out;gpu_exit=$coverageGpuExit;apps_exit=$coverageAppsExit;candidate_count=$coverageProcesses.Count;ollama_ps_exit=$coverageOllamaExit}|ConvertTo-Json -Compress
if($coverageGpuExit -ne 0 -or $coverageAppsExit -ne 0){exit 1}
