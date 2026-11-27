param([Parameter(Mandatory)][string]$Directory,[Parameter(Mandatory)][string]$Output)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime,System.Drawing
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime]
$null=[Windows.Data.Pdf.PdfPageRenderOptions,Windows.Data.Pdf,ContentType=WindowsRuntime]
$null=[Windows.Storage.Streams.InMemoryRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$methods=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object Name -eq AsTask
$generic=$methods | Where-Object {$_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'} | Select-Object -First 1
$action=$methods | Where-Object {!$_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'} | Select-Object -First 1
function AwaitValue($Operation,$Type) {
    $Task=$generic.MakeGenericMethod($Type).Invoke($null,@($Operation))
    $Task.Wait()
    $Task.Result
}
$dest=New-Item -Type Directory -Path $Output
foreach ($p in Get-ChildItem -LiteralPath $Directory -File -Filter '*.pdf') {
    $f=AwaitValue ([Windows.Storage.StorageFile]::GetFileFromPathAsync($p.FullName)) ([Windows.Storage.StorageFile])
    $doc=AwaitValue ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($f)) ([Windows.Data.Pdf.PdfDocument])
    for ($j=0;$j -lt $doc.PageCount;$j++) {
        $page=$doc.GetPage($j)
        $mem=New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
        $opt=New-Object Windows.Data.Pdf.PdfPageRenderOptions
        $opt.DestinationWidth=816
        $t=$action.Invoke($null,@($page.RenderToStreamAsync($mem,$opt)))
        $t.Wait()
        $mem.Seek(0)
        $s=[System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($mem)
        $bitmap=[System.Drawing.Bitmap]::new($s)
        $bitmap.Save((Join-Path $dest.FullName ("{0}-{1:d2}.png" -f $p.BaseName,$j)),
                      [System.Drawing.Imaging.ImageFormat]::Png)
        $bitmap.Dispose(); $s.Dispose(); $mem.Dispose(); $page.Dispose()
    }
    Write-Output ("{0} -> {1} pages" -f $p.Name,$doc.PageCount)
}
