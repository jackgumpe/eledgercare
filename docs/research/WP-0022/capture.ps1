param(
    [Parameter(Mandatory=$true)][string]$Raster,
    [Parameter(Mandatory=$true)][string]$RasterSha256,
    [Parameter(Mandatory=$true)][string]$BgraSha256,
    [Parameter(Mandatory=$true)][string]$ReceiptDirectory,
    [switch]$Preflight
)

# Windows PowerShell 5.1 x64; the driver starts a fresh process for each page.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
if (-not [Environment]::Is64BitProcess) { throw 'A 64-bit process is required' }
$utf8 = [Text.UTF8Encoding]::new($false)
$process = [Diagnostics.Process]::GetCurrentProcess()
$totalClock = [Diagnostics.Stopwatch]::StartNew()
$totalCpu = $process.TotalProcessorTime.TotalMilliseconds
$started = [DateTime]::UtcNow.ToString('o')

function Save-NewJson([string]$Name, $Value) {
    # CreateNew is the cross-process lock. A truncated start record still blocks a retry.
    $bytes = $utf8.GetBytes((ConvertTo-Json $Value -Depth 30 -Compress) + [char]10)
    $path = Join-Path $ReceiptDirectory $Name
    $file = [IO.File]::Open($path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    try {
        $file.Write($bytes, 0, $bytes.Length)
        $file.Flush($true)
    } finally { $file.Dispose() }
}

Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrResult,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapBufferAccessMode,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime]
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq ('IAsyncOperation' + [char]96 + '1')
} | Select-Object -First 1

function Await-Result($Operation, [Type]$ResultType) {
    $task = $asTask.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $task.Wait()
    $task.Result
}

$language = [Windows.Globalization.Language]::new('en-US')
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($language)
if ($null -eq $engine -or $engine.RecognizerLanguage.LanguageTag -cne 'en-US') { throw 'en-US engine unavailable' }
$version = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$assets = @(foreach ($rel in @('System32\Windows.Media.Ocr.dll','OCR\en-us\MsOcrRes.orp')) {
    $resource = Get-Item -LiteralPath (Join-Path $env:SystemRoot $rel)
    [ordered]@{path=$resource.FullName; bytes=$resource.Length; version=$resource.VersionInfo.FileVersion;
        sha256=(Get-FileHash -LiteralPath $resource.FullName -Algorithm SHA256).Hash.ToLowerInvariant()}
})
$loaded = $process.Modules | Where-Object ModuleName -eq 'Windows.Media.Ocr.dll' | Select-Object -First 1
$environment = [ordered]@{
    os_build=[string]$version.CurrentBuild; ubr=$version.UBR; display_version=$version.DisplayVersion
    engine='Windows.Media.Ocr.OcrEngine'; language=$engine.RecognizerLanguage.LanguageTag
    max_dimension=[Windows.Media.Ocr.OcrEngine]::MaxImageDimension; resources=$assets
    loaded_ocr_dll=$loaded.FileName; powershell=$PSVersionTable.PSVersion.ToString()
    pid=$PID; process_created_utc=$process.StartTime.ToUniversalTime().ToString('o')
}
if ((Get-FileHash -LiteralPath $Raster -Algorithm SHA256).Hash.ToLowerInvariant() -cne $RasterSha256) {
    throw 'PNG digest mismatch before decode'
}
$file = Await-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Raster)) ([Windows.Storage.StorageFile])
$stream = Await-Result ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
try {
    $decoder = Await-Result ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await-Result ($decoder.GetSoftwareBitmapAsync([Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,
        [Windows.Graphics.Imaging.BitmapAlphaMode]::Ignore)) ([Windows.Graphics.Imaging.SoftwareBitmap])
    try {
        $width = $bitmap.PixelWidth
        $height = $bitmap.PixelHeight
        if ($width -ne 2550 -or $height -ne 3300 -or $width -ne $decoder.OrientedPixelWidth -or
            $height -ne $decoder.OrientedPixelHeight -or $height -gt $environment.max_dimension) { throw 'Dimensions mismatch' }
        $buffer = $bitmap.LockBuffer([Windows.Graphics.Imaging.BitmapBufferAccessMode]::Read)
        try {
            $plane = $buffer.GetPlaneDescription(0)
            $geometry = [ordered]@{stride_bytes=$plane.Stride; start_index=$plane.StartIndex;
                width=$plane.Width; height=$plane.Height; plane_count=$buffer.GetPlaneCount()}
        } finally { $buffer.Dispose() }
        $canonical = [byte[]]::new($width * $height * 4)
        $ibuf = [System.Runtime.InteropServices.WindowsRuntime.WindowsRuntimeBufferExtensions]::AsBuffer($canonical)
        $bitmap.CopyToBuffer($ibuf)
        $hasher = [Security.Cryptography.SHA256]::Create()
        try { $hash = [BitConverter]::ToString($hasher.ComputeHash($canonical)).Replace('-','').ToLowerInvariant() }
        finally { $hasher.Dispose() }
        if ($hash -cne $BgraSha256) { throw 'Decoded WinRT BGRA8 pixels differ from the input pixels' }
        $metadata = [ordered]@{png_sha256=$RasterSha256; canonical_bgra_sha256=$hash; width=$width; height=$height
            decoder_format=$decoder.BitmapPixelFormat.ToString(); decoder_alpha_mode=$decoder.BitmapAlphaMode.ToString()
            bitmap_format=$bitmap.BitmapPixelFormat.ToString(); bitmap_alpha_mode=$bitmap.BitmapAlphaMode.ToString()
            dpi_x=$bitmap.DpiX; dpi_y=$bitmap.DpiY; plane=$geometry}
        $ready = [ordered]@{utc=[DateTime]::UtcNow.ToString('o'); initialization_started_utc=$started
            initialization_cpu_ms=$process.TotalProcessorTime.TotalMilliseconds-$totalCpu
            initialization_wall_ms=$totalClock.Elapsed.TotalMilliseconds; environment=$environment; image=$metadata}
        if ($Preflight) { Save-NewJson 'preflight.json' $ready; return }
        Save-NewJson 'ocr-started.json' $ready
        $clock = [Diagnostics.Stopwatch]::StartNew()
        $cpu = $process.TotalProcessorTime.TotalMilliseconds
        $callStarted = [DateTime]::UtcNow.ToString('o')
        $result = Await-Result ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        $callFinished = [DateTime]::UtcNow.ToString('o')
        $callCpu = $process.TotalProcessorTime.TotalMilliseconds - $cpu
        $callWall = $clock.Elapsed.TotalMilliseconds
        $lines = @(foreach ($line in $result.Lines) {
            $words = @(foreach ($word in $line.Words) {
                $b = $word.BoundingRect
                [ordered]@{text=[string]$word.Text; rect_px=@([double]$b.X,[double]$b.Y,[double]$b.Width,[double]$b.Height)}
            })
            [ordered]@{text=[string]$line.Text; words=$words}
        })
        $raw = [ordered]@{png_sha256=$RasterSha256; image=$metadata; language=$engine.RecognizerLanguage.LanguageTag
            text=[string]$result.Text; text_angle=$result.TextAngle; lines=$lines; recognize_started_utc=$callStarted
            recognize_finished_utc=$callFinished; recognize_wall_ms=$callWall; recognize_cpu_ms=$callCpu}
        Save-NewJson 'raw.json' $raw
        Save-NewJson 'ocr-finished.json' ([ordered]@{utc=[DateTime]::UtcNow.ToString('o'); png_sha256=$RasterSha256
            worker_cpu_ms=$process.TotalProcessorTime.TotalMilliseconds-$totalCpu
            worker_wall_ms=$totalClock.Elapsed.TotalMilliseconds
            raw_sha256=(Get-FileHash -LiteralPath (Join-Path $ReceiptDirectory 'raw.json')).Hash.ToLowerInvariant()})
    } finally { $bitmap.Dispose() }
} finally { $stream.Dispose() }
