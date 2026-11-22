# Render the published per-write series with the Windows .NET Framework chart library.
param(
    [Parameter(Mandatory)][string]$Evidence,
    [Parameter(Mandatory)][string]$Output
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms.DataVisualization
Add-Type -AssemblyName System.Drawing
$chart = New-Object System.Windows.Forms.DataVisualization.Charting.Chart
$chart.Width = 1440
$chart.Height = 720
$chart.BackColor = [Drawing.Color]::White
$fontFamily = 'Segoe UI'
$ink = [Drawing.ColorTranslator]::FromHtml('#20354A')
$grid = [Drawing.ColorTranslator]::FromHtml('#D9E3E9')
$colors = @{ M1 = '#156480'; M3 = '#AD501C' }
function New-Font([float]$size,[Drawing.FontStyle]$style) {
    [Drawing.Font]::new($fontFamily,$size,$style,[Drawing.GraphicsUnit]::Point)
}
function Add-Title([string]$label,[float]$size,[float]$x,[float]$y,[float]$w,[float]$h,[Drawing.FontStyle]$style) {
    $title = [Windows.Forms.DataVisualization.Charting.Title]::new($label)
    $title.Position = [Windows.Forms.DataVisualization.Charting.ElementPosition]::new($x,$y,$w,$h)
    $title.Alignment = [Drawing.ContentAlignment]::MiddleLeft
    $title.Font = New-Font $size $style
    $title.ForeColor = $ink
    [void]$chart.Titles.Add($title)
}
Add-Title 'Owner response across span writes' 22 3.3 1 90 7 Bold
Add-Title 'A positive value means the name edit moved scores toward the printed owner.' 12 3.3 8.5 90 4.5 Regular
Add-Title '12-page binder' 16 6.5 15 41 6 Bold
Add-Title '30-page binder' 16 55.5 15 41 6 Bold
$pairedReads = 0
$pairedWins = 0
foreach ($horizon in @(12,30)) {
    $area = [Windows.Forms.DataVisualization.Charting.ChartArea]::new("h$horizon")
    $left = if ($horizon -eq 12) { 2.5 } else { 51.5 }
    $area.Position = [Windows.Forms.DataVisualization.Charting.ElementPosition]::new($left,22,46.5,61)
    $area.BackColor = [Drawing.Color]::White
    foreach ($axis in @($area.AxisX,$area.AxisY)) {
        $axis.LabelStyle.Font = New-Font 10 Regular
        $axis.LabelStyle.ForeColor = $ink
        $axis.LineColor = $ink
        $axis.MajorTickMark.LineColor = $ink
        $axis.MajorGrid.LineColor = $grid
        $axis.TitleFont = New-Font 11 Regular
        $axis.TitleForeColor = $ink
        $axis.IsLabelAutoFit = $false
    }
    $area.AxisX.Title = 'Completed span writes'
    $area.AxisX.Minimum = 0
    $area.AxisX.Maximum = if ($horizon -eq 12) { 36 } else { 72 }
    $area.AxisX.Interval = if ($horizon -eq 12) { 4 } else { 8 }
    $area.AxisX.MajorGrid.Enabled = $false
    $area.AxisY.Title = 'Signed response'
    $area.AxisY.Minimum = -0.025
    $area.AxisY.Maximum = 0.025
    $area.AxisY.Interval = 0.01
    $area.AxisY.IntervalOffset = 0.005
    $area.AxisY.LabelStyle.Format = '0.000'
    foreach ($step in @(8,16)) {
        $mark = [Windows.Forms.DataVisualization.Charting.StripLine]::new()
        $mark.IntervalOffset = $step
        $mark.BorderColor = [Drawing.ColorTranslator]::FromHtml('#758491')
        $mark.BorderDashStyle = 'Dash'
        $mark.BorderWidth = 1
        [void]$area.AxisX.StripLines.Add($mark)
    }
    $zero = [Windows.Forms.DataVisualization.Charting.StripLine]::new()
    $zero.IntervalOffset = 0
    $zero.BorderColor = $ink
    $zero.BorderWidth = 2
    [void]$area.AxisY.StripLines.Add($zero)
    [void]$chart.ChartAreas.Add($area)
    foreach ($arm in @('M1','M3')) {
        $inputFile = Join-Path $Evidence "$arm-$horizon.json"
        $rows = Get-Content -Raw -Encoding UTF8 -LiteralPath $inputFile | ConvertFrom-Json
        $pairedReads += $rows.Count
        $pairedWins += @($rows | Where-Object { $_.paired_win }).Count
        $series = [Windows.Forms.DataVisualization.Charting.Series]::new("$arm-$horizon")
        $series.ChartArea = $area.Name
        $series.ChartType = 'Line'
        $series.BorderWidth = 3
        $series.Color = [Drawing.ColorTranslator]::FromHtml($colors[$arm])
        $series.MarkerStyle = if ($arm -eq 'M1') { 'Circle' } else { 'Square' }
        $series.MarkerSize = 5
        $series.IsVisibleInLegend = $false
        foreach ($row in $rows) {
            if ($row.phase -ne 'native_pre_target') {
                [void]$series.Points.AddXY([int]$row.step_index,[double]$row.delta)
            }
        }
        [void]$chart.Series.Add($series)
        $posting = @($rows | Where-Object phase -eq 'native_pre_target')
        if ($posting.Count -ne 1) { throw "Expected one native posting in $inputFile" }
        $dot = [Windows.Forms.DataVisualization.Charting.Series]::new("posting-$arm-$horizon")
        $dot.ChartArea = $area.Name
        $dot.ChartType = 'Point'
        $dot.IsVisibleInLegend = $false
        $dot.MarkerStyle = 'Diamond'
        $dot.MarkerSize = 12
        $dot.MarkerBorderColor = $ink
        $dot.MarkerColor = [Drawing.ColorTranslator]::FromHtml($colors[$arm])
        [void]$dot.Points.AddXY([int]$posting[0].step_index,[double]$posting[0].delta)
        [void]$chart.Series.Add($dot)
    }
}
Add-Title (([char]0x25CF).ToString() + '  M1') 12 4 86 11 5 Bold
$chart.Titles[$chart.Titles.Count-1].ForeColor = [Drawing.ColorTranslator]::FromHtml($colors.M1)
Add-Title (([char]0x25A0).ToString() + '  M3') 12 12 86 12 5 Bold
$chart.Titles[$chart.Titles.Count-1].ForeColor = [Drawing.ColorTranslator]::FromHtml($colors.M3)
Add-Title "Both owners ranked first on their own inputs at $pairedWins of $pairedReads paired reads." 11 23 86 72 5 Regular
Add-Title 'Dashed lines mark the owner write (8) and end of the opening (16). Diamonds mark the native pre-write posting.' 11 4 93 92 4.5 Regular
if (Test-Path -LiteralPath $Output) { throw "Choose a fresh output path" }
try {
    $chart.SaveImage($Output,[Windows.Forms.DataVisualization.Charting.ChartImageFormat]::Png)
} finally { $chart.Dispose() }
