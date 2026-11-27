param([Parameter(Mandatory)][string]$InputsDir,[Parameter(Mandatory)][string]$Supplements,
      [Parameter(Mandatory)][string]$Assembly,[Parameter(Mandatory)][string]$Receipt)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
Add-Type -AssemblyName System.Drawing
$null = [Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime]
$null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Data.Pdf.PdfPageRenderOptions,Windows.Data.Pdf,ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.InMemoryRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapEncoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$overloads = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 }
$generic = $overloads | Where-Object { $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation' + [char]96 + '1' } | Select-Object -First 1
$plain = $overloads | Where-Object { $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction' } | Select-Object -First 1
function Resolve-Operation($Operation,$ResultType) {
    $task = $generic.MakeGenericMethod($ResultType).Invoke($null,@($Operation))
    $task.Wait()
    return $task.Result
}
function Read-PageHashes($Path) {
    $file = Resolve-Operation ([Windows.Storage.StorageFile]::GetFileFromPathAsync((Resolve-Path $Path).Path)) ([Windows.Storage.StorageFile])
    $doc = Resolve-Operation ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($file)) ([Windows.Data.Pdf.PdfDocument])
    for ($pageIndex=0; $pageIndex -lt $doc.PageCount; $pageIndex++) {
        $sheet = $doc.GetPage($pageIndex)
        $buffer = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
        $options = New-Object Windows.Data.Pdf.PdfPageRenderOptions
        $options.DestinationWidth = 560
        $options.BitmapEncoderId = [Windows.Graphics.Imaging.BitmapEncoder]::PngEncoderId
        $action = $sheet.RenderToStreamAsync($buffer,$options)
        $plain.Invoke($null,@($action)).Wait()
        $buffer.Seek(0)
        $stream = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($buffer)
        $sha = [System.Security.Cryptography.SHA256]::Create()
        $encoded = ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant()
        $stream.Position = 0
        $bitmap = New-Object System.Drawing.Bitmap($stream)
        $rect = New-Object System.Drawing.Rectangle(0,0,$bitmap.Width,$bitmap.Height)
        $bits = $bitmap.LockBits($rect,[System.Drawing.Imaging.ImageLockMode]::ReadOnly,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $length = $bits.Stride * $bitmap.Height
        if ($bits.Stride -ne 4 * $bitmap.Width) { throw 'Unexpected BGRA storage' }
        $pixels = New-Object byte[] $length
        [System.Runtime.InteropServices.Marshal]::Copy($bits.Scan0,$pixels,0,$length)
        $hash = ([BitConverter]::ToString($sha.ComputeHash($pixels))).Replace('-','').ToLowerInvariant()
        $bitmap.UnlockBits($bits)
        [pscustomobject]@{w=$bitmap.Width;h=$bitmap.Height;bgra=$hash;png=$encoded}
        $bitmap.Dispose()
        $sha.Dispose()
        $stream.Dispose()
        $sheet.Dispose()
    }
}
$results = [ordered]@{}
$mismatch = $false
foreach ($roman in @('I','II','III')) {
    $prior = Get-Item -Path (Join-Path $InputsDir "Targeted-Depth-$roman-*.pdf")
    $note = Join-Path $Supplements "Amendment-$roman-02.1.pdf"
    $combined = Join-Path $Assembly "Targeted-Depth-$roman-Complete-02.1.pdf"
    $expected = @(Read-PageHashes $note) + @(Read-PageHashes $prior.FullName)
    $observed = @(Read-PageHashes $combined)
    $equal = ($expected.Count -eq $observed.Count) -and (($expected.bgra -join ',') -ceq ($observed.bgra -join ',')) -and (($expected.w -join ',') -ceq ($observed.w -join ',')) -and (($expected.h -join ',') -ceq ($observed.h -join ','))
    $results[$roman] = [ordered]@{reference=$expected; assembled=$observed; equal=$equal}
    if (-not $equal) { $mismatch = $true }
}
$output = ($results | ConvertTo-Json -Depth 6).Replace([string][char]13,'') + [char]10
[System.IO.File]::WriteAllText($Receipt,$output,(New-Object System.Text.UTF8Encoding($false)))
if ($mismatch) { Write-Output 'Observed pixel variation; consult paired same-input repeats' }
