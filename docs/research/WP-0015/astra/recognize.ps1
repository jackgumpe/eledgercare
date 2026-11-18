$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrResult,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime]
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation' + [char]96 + '1' } |
    Select-Object -First 1
function AwaitResult($operation,[Type]$resultType) {
    $task = $asTask.MakeGenericMethod($resultType).Invoke($null,@($operation))
    $task.Wait()
    $task.Result
}
$lang = New-Object Windows.Globalization.Language('en-US')
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
if ($null -eq $engine) { throw 'en-US OCR unavailable' }
[Console]::WriteLine((ConvertTo-Json -Compress @{language=$engine.RecognizerLanguage.LanguageTag;max_dimension=[Windows.Media.Ocr.OcrEngine]::MaxImageDimension;pid=$PID}))
while ($null -ne ($line = [Console]::ReadLine())) {
    $stream = $null
    $bitmap = $null
    try {
        $req = ConvertFrom-Json $line
        $file = AwaitResult ([Windows.Storage.StorageFile]::GetFileFromPathAsync($req.path)) ([Windows.Storage.StorageFile])
        $stream = AwaitResult ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $decoder = AwaitResult ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = AwaitResult ($decoder.GetSoftwareBitmapAsync([Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,[Windows.Graphics.Imaging.BitmapAlphaMode]::Ignore)) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $clock = [Diagnostics.Stopwatch]::StartNew()
        $result = AwaitResult ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        $clock.Stop()
        $lines = @(
            foreach ($ln in $result.Lines) {
                $words = @(foreach ($word in $ln.Words) {
                    $box = $word.BoundingRect
                    @{text=$word.Text;bbox=@($box.X,$box.Y,($box.X+$box.Width),($box.Y+$box.Height))}
                })
                @{text=$ln.Text;words=$words}
            }
        )
        [Console]::WriteLine((ConvertTo-Json -Depth 8 -Compress @{lines=$lines;text=$result.Text;angle=$result.TextAngle;recognize_ms=$clock.Elapsed.TotalMilliseconds;width=$bitmap.PixelWidth;height=$bitmap.PixelHeight}))
    } catch {
        [Console]::WriteLine((ConvertTo-Json -Compress @{error=$_.Exception.ToString()}))
    } finally {
        if ($null -ne $bitmap) { $bitmap.Dispose() }
        if ($null -ne $stream) { $stream.Dispose() }
    }
}
