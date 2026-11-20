$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)

if (-not [Environment]::Is64BitProcess) {
    throw '64-bit PowerShell process is required for System32 Windows.Media.Ocr.'
}

Add-Type -AssemblyName System.Runtime.WindowsRuntime
[System.Reflection.Assembly]::LoadWithPartialName('System.Runtime.InteropServices.WindowsRuntime') | Out-Null
$null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrResult,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapPixelFormat,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapAlphaMode,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Storage.FileAccessMode,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.IBuffer,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language,Windows.Globalization,ContentType=WindowsRuntime]

Add-Type -Language CSharp -TypeDefinition @"
using System;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;

public sealed class BmpHeaderInfo {
    public long FileLength;
    public uint BfSize;
    public uint BfOffBits;
    public uint DibSize;
    public int Width;
    public int Height;
    public bool TopDown;
    public ushort BitsPerPixel;
    public uint Compression;
    public long RowStride;
}

public static class WinRtWorkerNative {
    public static BmpHeaderInfo ValidateBmpFile(string path, int maxDimension) {
        if (string.IsNullOrWhiteSpace(path)) {
            throw new ArgumentException("BMP path is empty.");
        }
        if (!File.Exists(path)) {
            throw new FileNotFoundException("BMP file not found.", path);
        }
        using (var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read)) {
            long fileLen = fs.Length;
            if (fileLen < 54L) {
                throw new InvalidDataException("File is shorter than a minimal 54-byte BMP header.");
            }
            int readCount = (int)Math.Min(138L, fileLen);
            byte[] hdr = new byte[readCount];
            int got = 0;
            while (got < readCount) {
                int n = fs.Read(hdr, got, readCount - got);
                if (n <= 0) break;
                got += n;
            }
            if (got < 54 || hdr[0] != (byte)'B' || hdr[1] != (byte)'M') {
                throw new InvalidDataException("Input does not start with BMP 'BM' signature.");
            }
            uint bfSize = BitConverter.ToUInt32(hdr, 2);
            uint bfOffBits = BitConverter.ToUInt32(hdr, 10);
            uint dibSize = BitConverter.ToUInt32(hdr, 14);
            if (dibSize < 40U) {
                throw new InvalidDataException("Unsupported BMP DIB header size: " + dibSize);
            }
            if ((long)bfSize != fileLen) {
                throw new InvalidDataException(string.Format(
                    CultureInfo.InvariantCulture,
                    "BMP bfSize ({0}) disagrees with actual file length ({1}).", bfSize, fileLen));
            }
            if (14L + (long)dibSize > (long)bfOffBits || (long)bfOffBits > fileLen) {
                throw new InvalidDataException("BMP pixel data offset bfOffBits is out of bounds.");
            }
            int biWidth = BitConverter.ToInt32(hdr, 18);
            int biHeight = BitConverter.ToInt32(hdr, 22);
            ushort biPlanes = BitConverter.ToUInt16(hdr, 26);
            ushort biBitCount = BitConverter.ToUInt16(hdr, 28);
            uint biCompression = BitConverter.ToUInt32(hdr, 30);

            if (biWidth <= 0 || biHeight == 0 || biHeight == int.MinValue) {
                throw new InvalidDataException("Invalid BMP pixel dimensions in DIB header.");
            }
            int absHeight = Math.Abs(biHeight);
            if (biWidth > maxDimension || absHeight > maxDimension) {
                throw new InvalidDataException(string.Format(
                    CultureInfo.InvariantCulture,
                    "BMP dimensions {0}x{1} exceed OcrEngine.MaxImageDimension ({2}).",
                    biWidth, absHeight, maxDimension));
            }
            if (biPlanes != 1) {
                throw new InvalidDataException("BMP biPlanes must equal 1.");
            }
            if (biBitCount != 8 && biBitCount != 24 && biBitCount != 32) {
                throw new InvalidDataException("Unsupported BMP bits-per-pixel: " + biBitCount);
            }
            bool validCompression = (biCompression == 0U) || (biCompression == 3U && biBitCount == 32 && dibSize >= 56U);
            if (!validCompression) {
                throw new InvalidDataException("Unsupported or compressed BMP biCompression: " + biCompression);
            }
            long rowStride = (((long)biWidth * (long)biBitCount + 31L) / 32L) * 4L;
            long requiredBytes = checked(rowStride * (long)absHeight);
            if ((long)bfOffBits + requiredBytes > fileLen) {
                throw new InvalidDataException("Truncated BMP pixel payload.");
            }
            return new BmpHeaderInfo {
                FileLength = fileLen,
                BfSize = bfSize,
                BfOffBits = bfOffBits,
                DibSize = dibSize,
                Width = biWidth,
                Height = absHeight,
                TopDown = (biHeight < 0),
                BitsPerPixel = biBitCount,
                Compression = biCompression,
                RowStride = rowStride
            };
        }
    }

    public static string Sha256Hex(byte[] data) {
        if (data == null) throw new ArgumentNullException("data");
        using (var sha = SHA256.Create()) {
            byte[] hash = sha.ComputeHash(data);
            var sb = new StringBuilder(64);
            for (int i = 0; i < hash.Length; i++) {
                sb.Append(hash[i].ToString("x2", CultureInfo.InvariantCulture));
            }
            return sb.ToString();
        }
    }

    public static string Sha256HexAndAlpha(byte[] bgra, out int alphaMin, out int alphaMax, out bool allOpaque255) {
        if (bgra == null || bgra.Length < 4 || (bgra.Length % 4) != 0) {
            throw new ArgumentException("BGRA8 byte array must be non-empty and divisible by 4.");
        }
        int lo = 255;
        int hi = 0;
        for (int i = 3; i < bgra.Length; i += 4) {
            int a = bgra[i];
            if (a < lo) lo = a;
            if (a > hi) hi = a;
        }
        alphaMin = lo;
        alphaMax = hi;
        allOpaque255 = (lo == 255 && hi == 255);
        return Sha256Hex(bgra);
    }

    public static byte[] SliceRectBgra8(byte[] full, int fullWidth, int fullHeight, int left, int top, int right, int bottom) {
        if (left < 0 || top < 0 || right <= left || bottom <= top || right > fullWidth || bottom > fullHeight) {
            throw new ArgumentOutOfRangeException("rect", "Half-open crop rectangle is out of bounds.");
        }
        int expectedFullLen = checked(fullWidth * fullHeight * 4);
        if (full == null || full.Length != expectedFullLen) {
            throw new ArgumentException("Retained full BGRA8 buffer length mismatch.");
        }
        int cw = right - left;
        int ch = bottom - top;
        int dstRowBytes = checked(cw * 4);
        int srcStride = checked(fullWidth * 4);
        byte[] dst = new byte[checked(dstRowBytes * ch)];
        for (int r = 0; r < ch; r++) {
            int srcOffset = checked((top + r) * srcStride + left * 4);
            int dstOffset = checked(r * dstRowBytes);
            Buffer.BlockCopy(full, srcOffset, dst, dstOffset, dstRowBytes);
        }
        return dst;
    }

    public static bool BytesEqual(byte[] a, byte[] b) {
        if (ReferenceEquals(a, b)) return true;
        if (a == null || b == null || a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; i++) {
            if (a[i] != b[i]) return false;
        }
        return true;
    }

    public static void AppendJsonString(StringBuilder sb, string value) {
        if (value == null) {
            sb.Append("null");
            return;
        }
        sb.Append('"');
        for (int i = 0; i < value.Length; i++) {
            char c = value[i];
            switch (c) {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\b': sb.Append("\\b"); break;
                case '\f': sb.Append("\\f"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (c < (char)0x20 || c > (char)0x7E) {
                        sb.Append("\\u");
                        sb.Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                    } else {
                        sb.Append(c);
                    }
                    break;
            }
        }
        sb.Append('"');
    }

    public static void AppendJsonDouble(StringBuilder sb, double v) {
        if (double.IsNaN(v) || double.IsInfinity(v)) {
            throw new InvalidOperationException("Non-finite floating-point value in OCR result.");
        }
        if (v == Math.Truncate(v) && v >= -9007199254740992.0 && v <= 9007199254740992.0) {
            sb.Append(((long)v).ToString(CultureInfo.InvariantCulture));
        } else {
            sb.Append(v.ToString("R", CultureInfo.InvariantCulture));
        }
    }
}
"@

$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object {
        $_.Name -eq 'AsTask' -and
        $_.IsGenericMethod -and
        $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq ('IAsyncOperation' + [char]96 + '1')
    } |
    Select-Object -First 1

function AwaitResult($operation, [Type]$resultType) {
    $task = $asTask.MakeGenericMethod($resultType).Invoke($null, @($operation))
    $task.Wait()
    $task.Result
}

function ReadSoftwareBitmapBgra8([Windows.Graphics.Imaging.SoftwareBitmap]$sb) {
    if ($null -eq $sb) { throw 'SoftwareBitmap is null.' }
    if ($sb.BitmapPixelFormat -ne [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8) {
        throw ("Unexpected SoftwareBitmap pixel format: " + $sb.BitmapPixelFormat.ToString())
    }
    $len = [int]($sb.PixelWidth * $sb.PixelHeight * 4)
    $bytes = New-Object byte[] $len
    $ibuf = [System.Runtime.InteropServices.WindowsRuntime.WindowsRuntimeBufferExtensions]::AsBuffer([byte[]]$bytes)
    $sb.CopyToBuffer($ibuf)
    return ,$bytes
}

$lang = New-Object Windows.Globalization.Language('en-US')
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
if ($null -eq $engine) {
    throw 'en-US Windows.Media.Ocr.OcrEngine is unavailable on this host.'
}
if ($engine.RecognizerLanguage.LanguageTag -ne 'en-US') {
    throw ("Unexpected recognizer language tag: " + $engine.RecognizerLanguage.LanguageTag)
}
$maxDim = [int][Windows.Media.Ocr.OcrEngine]::MaxImageDimension

function Invoke-SharedRecognize([Windows.Graphics.Imaging.SoftwareBitmap]$bitmap) {
    if ($null -eq $bitmap) { throw 'Cannot recognize null SoftwareBitmap.' }
    if ($bitmap.BitmapPixelFormat -ne [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8) {
        throw ("Recognition requires Bgra8 SoftwareBitmap, got: " + $bitmap.BitmapPixelFormat.ToString())
    }
    if ($bitmap.PixelWidth -le 0 -or $bitmap.PixelHeight -le 0 -or $bitmap.PixelWidth -gt $maxDim -or $bitmap.PixelHeight -gt $maxDim) {
        throw ("SoftwareBitmap dimensions out of bounds: " + $bitmap.PixelWidth + "x" + $bitmap.PixelHeight)
    }
    $clock = [Diagnostics.Stopwatch]::StartNew()
    $ocrResult = AwaitResult ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $clock.Stop()
    $recMs = $clock.Elapsed.TotalMilliseconds

    $sbJson = New-Object System.Text.StringBuilder 4096
    $null = $sbJson.Append('[')
    $firstLine = $true
    foreach ($ln in $ocrResult.Lines) {
        if (-not $firstLine) { $null = $sbJson.Append(',') }
        $firstLine = $false
        $null = $sbJson.Append('{"text":')
        [WinRtWorkerNative]::AppendJsonString($sbJson, $ln.Text)
        $null = $sbJson.Append(',"words":[')
        $firstWord = $true
        foreach ($word in $ln.Words) {
            if (-not $firstWord) { $null = $sbJson.Append(',') }
            $firstWord = $false
            $box = $word.BoundingRect
            $x0 = [double]$box.X
            $y0 = [double]$box.Y
            $x1 = [double]($box.X + $box.Width)
            $y1 = [double]($box.Y + $box.Height)
            $null = $sbJson.Append('{"text":')
            [WinRtWorkerNative]::AppendJsonString($sbJson, $word.Text)
            $null = $sbJson.Append(',"bbox":[')
            [WinRtWorkerNative]::AppendJsonDouble($sbJson, $x0)
            $null = $sbJson.Append(',')
            [WinRtWorkerNative]::AppendJsonDouble($sbJson, $y0)
            $null = $sbJson.Append(',')
            [WinRtWorkerNative]::AppendJsonDouble($sbJson, $x1)
            $null = $sbJson.Append(',')
            [WinRtWorkerNative]::AppendJsonDouble($sbJson, $y1)
            $null = $sbJson.Append(']}')
        }
        $null = $sbJson.Append(']}')
    }
    $null = $sbJson.Append(']')

    return @{
        text = [string]$ocrResult.Text
        angle = $ocrResult.TextAngle
        recognize_ms = [double]$recMs
        lines_json = $sbJson.ToString()
    }
}

function Write-WorkerResponse(
    [string]$mode,
    [hashtable]$rec,
    [int]$width,
    [int]$height,
    [int]$fullWidth,
    [int]$fullHeight,
    [int[]]$rect,
    [string]$bgraSha,
    [string]$srcRectSha,
    [string]$fullBgraSha,
    [string]$pixelFormat,
    [string]$alphaMode,
    [int]$alphaMin,
    [int]$alphaMax,
    [bool]$allOpaque,
    [double]$dpiX,
    [double]$dpiY,
    [string]$bmpPath,
    [Nullable[int]]$bmpBpp,
    [Nullable[uint32]]$bmpComp,
    [string]$decFmt,
    [string]$decAlpha
) {
    $out = New-Object System.Text.StringBuilder 4096
    $null = $out.Append('{"mode":')
    [WinRtWorkerNative]::AppendJsonString($out, $mode)
    $null = $out.Append(',"text":')
    [WinRtWorkerNative]::AppendJsonString($out, $rec.text)
    $null = $out.Append(',"lines":')
    $null = $out.Append($rec.lines_json)
    $null = $out.Append(',"angle":')
    if ($null -eq $rec.angle) {
        $null = $out.Append('null')
    } else {
        [WinRtWorkerNative]::AppendJsonDouble($out, [double]$rec.angle)
    }
    $null = $out.Append(',"recognize_ms":')
    [WinRtWorkerNative]::AppendJsonDouble($out, [double]$rec.recognize_ms)
    $null = $out.AppendFormat([Globalization.CultureInfo]::InvariantCulture, ',"width":{0},"height":{1},"full_width":{2},"full_height":{3}', $width, $height, $fullWidth, $fullHeight)
    $null = $out.AppendFormat([Globalization.CultureInfo]::InvariantCulture, ',"rect":[{0},{1},{2},{3}]', $rect[0], $rect[1], $rect[2], $rect[3])
    $null = $out.Append(',"bgra_sha256":')
    [WinRtWorkerNative]::AppendJsonString($out, $bgraSha)
    $null = $out.Append(',"source_rectangle_sha256":')
    [WinRtWorkerNative]::AppendJsonString($out, $srcRectSha)
    $null = $out.Append(',"full_bgra_sha256":')
    [WinRtWorkerNative]::AppendJsonString($out, $fullBgraSha)
    $null = $out.Append(',"byte_equality_verified":true,"pixel_format":')
    [WinRtWorkerNative]::AppendJsonString($out, $pixelFormat)
    $null = $out.Append(',"requested_alpha_mode":"Ignore","alpha_mode":')
    [WinRtWorkerNative]::AppendJsonString($out, $alphaMode)
    $null = $out.AppendFormat([Globalization.CultureInfo]::InvariantCulture, ',"alpha_summary":{{"min":{0},"max":{1},"all_opaque_255":{2}}}', $alphaMin, $alphaMax, ($allOpaque.ToString().ToLowerInvariant()))
    $null = $out.Append(',"dpi_x":')
    [WinRtWorkerNative]::AppendJsonDouble($out, $dpiX)
    $null = $out.Append(',"dpi_y":')
    [WinRtWorkerNative]::AppendJsonDouble($out, $dpiY)
    $null = $out.AppendFormat([Globalization.CultureInfo]::InvariantCulture, ',"pid":{0},"language":', $PID)
    [WinRtWorkerNative]::AppendJsonString($out, $engine.RecognizerLanguage.LanguageTag)
    $null = $out.AppendFormat([Globalization.CultureInfo]::InvariantCulture, ',"max_dimension":{0}', $maxDim)
    if ($null -ne $bmpPath) {
        $null = $out.Append(',"bmp_path":')
        [WinRtWorkerNative]::AppendJsonString($out, $bmpPath)
    }
    if ($null -ne $bmpBpp) {
        $null = $out.AppendFormat([Globalization.CultureInfo]::InvariantCulture, ',"bmp_bits_per_pixel":{0}', $bmpBpp)
    }
    if ($null -ne $bmpComp) {
        $null = $out.AppendFormat([Globalization.CultureInfo]::InvariantCulture, ',"bmp_compression":{0}', $bmpComp)
    }
    if ($null -ne $decFmt) {
        $null = $out.Append(',"decoder_pixel_format":')
        [WinRtWorkerNative]::AppendJsonString($out, $decFmt)
    }
    if ($null -ne $decAlpha) {
        $null = $out.Append(',"decoder_alpha_mode":')
        [WinRtWorkerNative]::AppendJsonString($out, $decAlpha)
    }
    $null = $out.Append('}')
    [Console]::WriteLine($out.ToString())
}

function Write-ErrorResponse([string]$errText) {
    $out = New-Object System.Text.StringBuilder 512
    $null = $out.Append('{"error":')
    [WinRtWorkerNative]::AppendJsonString($out, $errText)
    $null = $out.AppendFormat([Globalization.CultureInfo]::InvariantCulture, ',"pid":{0}}}', $PID)
    [Console]::WriteLine($out.ToString())
}

$proc = [Diagnostics.Process]::GetCurrentProcess()
$createFt = $proc.StartTime.ToFileTimeUtc()
$cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
$assetVersions = @{}
foreach ($rel in @('System32\Windows.Media.Ocr.dll', 'OCR\en-us\MsOcrRes.orp')) {
    $fullAsset = Join-Path $env:SystemRoot $rel
    if (Test-Path $fullAsset) {
        $vi = (Get-Item $fullAsset).VersionInfo
        $assetVersions[$rel.Replace('\', '/')] = @{
            file_version = $vi.FileVersion
            product_version = $vi.ProductVersion
            file_description = $vi.FileDescription
        }
    }
}
$loadedMod = $null
try {
    $m = $proc.Modules | Where-Object { $_.ModuleName -ieq 'Windows.Media.Ocr.dll' } | Select-Object -First 1
    if ($null -ne $m) {
        $loadedMod = @{
            module_name = $m.ModuleName
            file_name = $m.FileName
            module_memory_size = $m.ModuleMemorySize
            file_version = $m.FileVersionInfo.FileVersion
            product_version = $m.FileVersionInfo.ProductVersion
        }
    }
} catch {
    $loadedMod = $null
}

$hello = @{
    pid = $PID
    process_create_filetime = $createFt
    is_64bit_process = [Environment]::Is64BitProcess
    powershell_version = $PSVersionTable.PSVersion.ToString()
    clr_version = $PSVersionTable.CLRVersion.ToString()
    language = $engine.RecognizerLanguage.LanguageTag
    language_display_name = $engine.RecognizerLanguage.DisplayName
    max_dimension = $maxDim
    os = @{
        product_name = [string]$cv.ProductName
        display_version = [string]$cv.DisplayVersion
        current_build = [string]$cv.CurrentBuild
        ubr = [int]$cv.UBR
        build_lab_ex = [string]$cv.BuildLabEx
    }
    asset_versions = $assetVersions
    loaded_ocr_module = $loadedMod
}
[Console]::WriteLine((ConvertTo-Json -Depth 6 -Compress $hello))

$heldBitmap = $null
$heldBytes = $null
$heldSha256 = $null
$heldWidth = 0
$heldHeight = 0
$heldPixelFormat = $null
$heldAlphaMode = $null
$heldDpiX = 0.0
$heldDpiY = 0.0
$heldBmpPath = $null

function Clear-HeldBitmap {
    if ($null -ne $script:heldBitmap) {
        try { $script:heldBitmap.Dispose() } catch {}
    }
    $script:heldBitmap = $null
    $script:heldBytes = $null
    $script:heldSha256 = $null
    $script:heldWidth = 0
    $script:heldHeight = 0
    $script:heldPixelFormat = $null
    $script:heldAlphaMode = $null
    $script:heldDpiX = 0.0
    $script:heldDpiY = 0.0
    $script:heldBmpPath = $null
}

try {
    while ($null -ne ($line = [Console]::ReadLine())) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $req = ConvertFrom-Json $line
            $op = [string]$req.op
            if ($op -eq 'full') {
                Clear-HeldBitmap
                $bmpPath = [string]$req.path
                $hdr = [WinRtWorkerNative]::ValidateBmpFile($bmpPath, $maxDim)
                $stream = $null
                $newBitmap = $null
                $kept = $false
                try {
                    $file = AwaitResult ([Windows.Storage.StorageFile]::GetFileFromPathAsync($bmpPath)) ([Windows.Storage.StorageFile])
                    $stream = AwaitResult ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
                    $decoder = AwaitResult ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
                    $decFmt = $decoder.BitmapPixelFormat.ToString()
                    $decAlpha = $decoder.BitmapAlphaMode.ToString()
                    if ([int]$decoder.PixelWidth -ne $hdr.Width -or [int]$decoder.PixelHeight -ne $hdr.Height) {
                        throw ("Decoder dimensions (" + $decoder.PixelWidth + "x" + $decoder.PixelHeight + ") disagree with BMP header (" + $hdr.Width + "x" + $hdr.Height + ").")
                    }
                    if ([int]$decoder.OrientedPixelWidth -ne $hdr.Width -or [int]$decoder.OrientedPixelHeight -ne $hdr.Height) {
                        throw ("Oriented dimensions (" + $decoder.OrientedPixelWidth + "x" + $decoder.OrientedPixelHeight + ") disagree with raw pixel dimensions.")
                    }
                    $newBitmap = AwaitResult ($decoder.GetSoftwareBitmapAsync([Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8, [Windows.Graphics.Imaging.BitmapAlphaMode]::Ignore)) ([Windows.Graphics.Imaging.SoftwareBitmap])
                    if ($newBitmap.BitmapPixelFormat -ne [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8) {
                        throw ("Decoded SoftwareBitmap pixel format is not Bgra8: " + $newBitmap.BitmapPixelFormat.ToString())
                    }
                    if ([int]$newBitmap.PixelWidth -ne $hdr.Width -or [int]$newBitmap.PixelHeight -ne $hdr.Height) {
                        throw ("SoftwareBitmap dimensions (" + $newBitmap.PixelWidth + "x" + $newBitmap.PixelHeight + ") disagree with BMP header.")
                    }

                    $fullBytes = ReadSoftwareBitmapBgra8 $newBitmap
                    if ($fullBytes.Length -ne ($hdr.Width * $hdr.Height * 4)) {
                        throw 'Decoded BGRA8 buffer byte count mismatch.'
                    }
                    $aMin = 0; $aMax = 0; $allOpaque = $false
                    $fullSha = [WinRtWorkerNative]::Sha256HexAndAlpha($fullBytes, [ref]$aMin, [ref]$aMax, [ref]$allOpaque)
                    if (($hdr.BitsPerPixel -eq 24 -or $hdr.BitsPerPixel -eq 8) -and (-not $allOpaque)) {
                        throw ("Expected default opaque alpha=255 for " + $hdr.BitsPerPixel + "-bit BMP, observed min=" + $aMin + " max=" + $aMax)
                    }

                    $rec = Invoke-SharedRecognize $newBitmap

                    $script:heldBitmap = $newBitmap
                    $script:heldBytes = $fullBytes
                    $script:heldSha256 = $fullSha
                    $script:heldWidth = [int]$newBitmap.PixelWidth
                    $script:heldHeight = [int]$newBitmap.PixelHeight
                    $script:heldPixelFormat = $newBitmap.BitmapPixelFormat.ToString()
                    $script:heldAlphaMode = $newBitmap.BitmapAlphaMode.ToString()
                    $script:heldDpiX = [double]$newBitmap.DpiX
                    $script:heldDpiY = [double]$newBitmap.DpiY
                    $script:heldBmpPath = $bmpPath
                    $kept = $true

                    Write-WorkerResponse `
                        -mode 'full' `
                        -rec $rec `
                        -width $script:heldWidth `
                        -height $script:heldHeight `
                        -fullWidth $script:heldWidth `
                        -fullHeight $script:heldHeight `
                        -rect @(0, 0, $script:heldWidth, $script:heldHeight) `
                        -bgraSha $fullSha `
                        -srcRectSha $fullSha `
                        -fullBgraSha $fullSha `
                        -pixelFormat $script:heldPixelFormat `
                        -alphaMode $script:heldAlphaMode `
                        -alphaMin $aMin `
                        -alphaMax $aMax `
                        -allOpaque $allOpaque `
                        -dpiX $script:heldDpiX `
                        -dpiY $script:heldDpiY `
                        -bmpPath $bmpPath `
                        -bmpBpp ([int]$hdr.BitsPerPixel) `
                        -bmpComp ([uint32]$hdr.Compression) `
                        -decFmt $decFmt `
                        -decAlpha $decAlpha
                } finally {
                    if (-not $kept -and $null -ne $newBitmap) {
                        try { $newBitmap.Dispose() } catch {}
                    }
                    if ($null -ne $stream) {
                        try { $stream.Dispose() } catch {}
                    }
                }
            } elseif ($op -eq 'crop') {
                if ($null -eq $script:heldBitmap -or $null -eq $script:heldBytes) {
                    throw 'No full-page SoftwareBitmap is retained; call full(bmp_path) first.'
                }
                $left = [int]$req.left
                $top = [int]$req.top
                $right = [int]$req.right
                $bottom = [int]$req.bottom
                if ($left -lt 0 -or $top -lt 0 -or $right -le $left -or $bottom -le $top -or $right -gt $script:heldWidth -or $bottom -gt $script:heldHeight) {
                    throw ("Half-open crop rectangle [" + $left + "," + $top + "," + $right + "," + $bottom + "] is out of bounds for retained page " + $script:heldWidth + "x" + $script:heldHeight + ".")
                }
                $cw = $right - $left
                $ch = $bottom - $top
                if ($cw -gt $maxDim -or $ch -gt $maxDim) {
                    throw ("Crop dimensions " + $cw + "x" + $ch + " exceed MaxImageDimension " + $maxDim + ".")
                }

                $srcSliceBytes = [WinRtWorkerNative]::SliceRectBgra8($script:heldBytes, $script:heldWidth, $script:heldHeight, $left, $top, $right, $bottom)
                $srcRectSha = [WinRtWorkerNative]::Sha256Hex($srcSliceBytes)

                $cropBitmap = $null
                try {
                    $cropBitmap = New-Object Windows.Graphics.Imaging.SoftwareBitmap(
                        $script:heldBitmap.BitmapPixelFormat,
                        $cw,
                        $ch,
                        $script:heldBitmap.BitmapAlphaMode
                    )
                    $srcIBuf = [System.Runtime.InteropServices.WindowsRuntime.WindowsRuntimeBufferExtensions]::AsBuffer([byte[]]$srcSliceBytes)
                    $cropBitmap.CopyFromBuffer($srcIBuf)
                    $cropBitmap.DpiX = $script:heldDpiX
                    $cropBitmap.DpiY = $script:heldDpiY

                    if ([int]$cropBitmap.PixelWidth -ne $cw -or [int]$cropBitmap.PixelHeight -ne $ch) {
                        throw 'Crop SoftwareBitmap dimensions disagree with requested rectangle.'
                    }
                    if ($cropBitmap.BitmapPixelFormat -ne [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8) {
                        throw 'Crop SoftwareBitmap pixel format is not Bgra8.'
                    }
                    if ($cropBitmap.BitmapAlphaMode -ne $script:heldBitmap.BitmapAlphaMode) {
                        throw 'Crop SoftwareBitmap alpha mode disagrees with retained full bitmap.'
                    }

                    # Prove exact byte identity on the live crop SoftwareBitmap BEFORE recognition.
                    $verifyBytes = ReadSoftwareBitmapBgra8 $cropBitmap
                    $aMin = 0; $aMax = 0; $allOpaque = $false
                    $cropSha = [WinRtWorkerNative]::Sha256HexAndAlpha($verifyBytes, [ref]$aMin, [ref]$aMax, [ref]$allOpaque)
                    if ($cropSha -ne $srcRectSha -or (-not [WinRtWorkerNative]::BytesEqual($verifyBytes, $srcSliceBytes))) {
                        throw 'Pre-recognition crop SoftwareBitmap byte identity verification failed.'
                    }

                    $rec = Invoke-SharedRecognize $cropBitmap

                    Write-WorkerResponse `
                        -mode 'crop' `
                        -rec $rec `
                        -width $cw `
                        -height $ch `
                        -fullWidth $script:heldWidth `
                        -fullHeight $script:heldHeight `
                        -rect @($left, $top, $right, $bottom) `
                        -bgraSha $cropSha `
                        -srcRectSha $srcRectSha `
                        -fullBgraSha $script:heldSha256 `
                        -pixelFormat $cropBitmap.BitmapPixelFormat.ToString() `
                        -alphaMode $cropBitmap.BitmapAlphaMode.ToString() `
                        -alphaMin $aMin `
                        -alphaMax $aMax `
                        -allOpaque $allOpaque `
                        -dpiX ([double]$cropBitmap.DpiX) `
                        -dpiY ([double]$cropBitmap.DpiY) `
                        -bmpPath $null `
                        -bmpBpp $null `
                        -bmpComp $null `
                        -decFmt $null `
                        -decAlpha $null
                } finally {
                    if ($null -ne $cropBitmap) {
                        try { $cropBitmap.Dispose() } catch {}
                    }
                }
            } else {
                throw ("Unsupported worker operation: " + $op)
            }
        } catch {
            Write-ErrorResponse ($_.Exception.ToString())
        }
    }
} finally {
    Clear-HeldBitmap
}
