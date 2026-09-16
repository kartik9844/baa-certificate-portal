$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.Drawing

$root = (Get-Location).Path
$xlsx = Join-Path $root '2025 TEM - CERTIFICATE ISSUE_SORTED_ASSIGNED.xlsx'
$templatePath = Join-Path $root 'Add a subheading (1).png'
$outDir = Join-Path $root 'sorted_certificates'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

function Read-ZipText([System.IO.Compression.ZipArchive]$zip, [string]$name) {
  $entry = $zip.GetEntry($name)
  if ($null -eq $entry) { return $null }
  $reader = [System.IO.StreamReader]::new($entry.Open())
  try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
}

$zip = [System.IO.Compression.ZipFile]::OpenRead($xlsx)
try {
  $ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
  $ssXml = [xml](Read-ZipText $zip 'xl/sharedStrings.xml')
  $mgr = New-Object System.Xml.XmlNamespaceManager($ssXml.NameTable)
  $mgr.AddNamespace('m', $ns)
  $shared = @()
  foreach ($si in $ssXml.SelectNodes('/m:sst/m:si', $mgr)) {
    $shared += (($si.SelectNodes('.//m:t', $mgr) | ForEach-Object { $_.InnerText }) -join '')
  }
  $sheetXml = [xml](Read-ZipText $zip 'xl/worksheets/sheet1.xml')
  $sheetMgr = New-Object System.Xml.XmlNamespaceManager($sheetXml.NameTable)
  $sheetMgr.AddNamespace('m', $ns)
  $rows = @()
  foreach ($row in $sheetXml.SelectNodes('/m:worksheet/m:sheetData/m:row', $sheetMgr)) {
    $item = [ordered]@{}
    foreach ($cell in $row.SelectNodes('m:c', $sheetMgr)) {
      $ref = [string]$cell.r
      $valueNode = $cell.SelectSingleNode('m:v', $sheetMgr)
      $value = if ($null -eq $valueNode) { '' } else { [string]$valueNode.InnerText }
      if ([string]$cell.t -eq 's' -and $value -ne '') { $value = $shared[[int]$value] }
      $item[$ref.Substring(0,1)] = $value
    }
    $rows += [pscustomobject]$item
  }
} finally { $zip.Dispose() }

$template = [Drawing.Bitmap]::new($templatePath)
$fontFamily = New-Object Drawing.FontFamily('Arial')
$centerFormat = New-Object Drawing.StringFormat
$centerFormat.Alignment = [Drawing.StringAlignment]::Center
$centerFormat.LineAlignment = [Drawing.StringAlignment]::Near
$leftFormat = New-Object Drawing.StringFormat
$leftFormat.Alignment = [Drawing.StringAlignment]::Near
$leftFormat.LineAlignment = [Drawing.StringAlignment]::Near
$black = [Drawing.Brushes]::Black

$manifest = @()
$made = 0
$skipped = 0
foreach ($row in $rows | Select-Object -Skip 1) {
  $name = ([string]$row.D).Trim()
  $reg = ([string]$row.G).Trim()
  if ([string]::IsNullOrWhiteSpace($reg)) { $skipped++; continue }
  $safeReg = ($reg -replace '[<>:"/\\|?*]', '_')
  $jpgPath = Join-Path $outDir ($safeReg + '.jpg')
  if (Test-Path -LiteralPath $jpgPath) {
    $manifest += [pscustomobject]@{ SLNO = $row.A; Name = $name; RegisterNo = $reg; FileName = (Split-Path $jpgPath -Leaf); LocalPath = $jpgPath }
    $made++
    continue
  }
  $bmp = [Drawing.Bitmap]$template.Clone()
  try {
    $g = [Drawing.Graphics]::FromImage($bmp)
    try {
      $g.TextRenderingHint = [Drawing.Text.TextRenderingHint]::AntiAliasGridFit
      $nameSize = 54.0
      do {
        $nameFont = New-Object Drawing.Font($fontFamily, $nameSize, [Drawing.FontStyle]::Bold, [Drawing.GraphicsUnit]::Pixel)
        $measure = $g.MeasureString($name, $nameFont)
        if ($measure.Width -le 1220 -or $nameSize -le 32) { break }
        $nameFont.Dispose(); $nameSize -= 2
      } while ($true)
      $g.DrawString($name, $nameFont, $black, [Drawing.RectangleF]::new(390, 838, 1220, 70), $centerFormat)
      $nameFont.Dispose()
      $regFont = New-Object Drawing.Font($fontFamily, 26, [Drawing.FontStyle]::Bold, [Drawing.GraphicsUnit]::Pixel)
      $g.DrawString($reg, $regFont, $black, [Drawing.PointF]::new(385, 1255), $leftFormat)
      $regFont.Dispose()
    } finally { $g.Dispose() }
    $bmp.Save($jpgPath, [Drawing.Imaging.ImageFormat]::Jpeg)
  } finally { $bmp.Dispose() }
  $manifest += [pscustomobject]@{ SLNO = $row.A; Name = $name; RegisterNo = $reg; FileName = (Split-Path $jpgPath -Leaf); LocalPath = $jpgPath }
  $made++
}

$manifest | Export-Csv -NoTypeInformation -Encoding UTF8 -LiteralPath (Join-Path $root 'certificate_manifest.csv')
$template.Dispose(); $fontFamily.Dispose(); $centerFormat.Dispose(); $leftFormat.Dispose()
Write-Output "Generated=$made Skipped=$skipped Output=$outDir"
