param([Parameter(Mandatory)][string]$Plan)
$ErrorActionPreference='Stop'
$path=(Resolve-Path -LiteralPath $Plan).Path
$root=(Resolve-Path -LiteralPath "$env:USERPROFILE/eLedgerCare-Speed/WP-0045").Path
if (-not $path.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetExtension($path) -ne '.json') {throw 'Plan path must be a new WP-0045 local JSON plan'}
$receipt=[IO.Path]::ChangeExtension($path,'.receipt.json')
if (Test-Path -LiteralPath $receipt){throw 'Fresh plan name required'}
$name='eLedgerCare-WP0045-'+[Guid]::NewGuid().ToString('N')
$user=[Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$runner="$root\coordination\limited_runner.py"
$exe="$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe"
$action=New-ScheduledTaskAction -Execute $exe -Argument ('-I -B "'+$runner+'" "'+$path+'"') -WorkingDirectory "$root\coordination"
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 345) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$registered=$false
try {
    Register-ScheduledTask -TaskName $name -Principal $principal -Action $action -Settings $settings | Out-Null
    $registered=$true
    Start-ScheduledTask -TaskName $name
    $timer=[Diagnostics.Stopwatch]::StartNew()
    while (-not (Test-Path -LiteralPath $receipt) -and $timer.Elapsed.TotalSeconds -lt 340) {
        Start-Sleep -Milliseconds 500
        if ($timer.Elapsed.TotalSeconds -gt 8) {
            $state=(Get-ScheduledTask -TaskName $name).State
            $info=Get-ScheduledTaskInfo -TaskName $name
            if ($state -ne 'Running' -and $info.LastRunTime.Year -gt 2025 -and $info.LastTaskResult -ne 0){throw "Limited task ended without receipt: $($info.LastTaskResult)"}
        }
    }
    if (-not (Test-Path -LiteralPath $receipt)){throw 'Limited task timed out'}
    Get-Content -Raw -LiteralPath $receipt
} finally {
    if ($registered){Unregister-ScheduledTask -TaskName $name -Confirm:$false}
}
