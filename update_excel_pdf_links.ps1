$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$source = Join-Path $root '2025 TEM - CERTIFICATE ISSUE.xlsx'
$output = Join-Path $root '2025 TEM - CERTIFICATE ISSUE_WITH_PDF_LINKS.xlsx'
Copy-Item -LiteralPath $source -Destination $output -Force
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
try {
  $book = $excel.Workbooks.Open($output)
  $sheet = $book.Worksheets.Item(1)
  $lastRow = $sheet.Cells($sheet.Rows.Count, 7).End(-4162).Row
  $sheet.Cells(1, 8).Value2 = 'BATCH'
  $sheet.Cells(1, 9).Value2 = 'PDF FILE / LINK'
  $sheet.Cells(1, 8).Font.Bold = $true
  $sheet.Cells(1, 9).Font.Bold = $true
  for ($r = 2; $r -le $lastRow; $r++) {
    $reg = ([string]$sheet.Cells($r, 7).Text).Trim()
    if ([string]::IsNullOrWhiteSpace($reg)) { continue }
    $batch = [math]::Ceiling(($r - 1) / 50)
    $batchName = ('batch_{0:D3}' -f [int]$batch)
    $fileName = "$reg.pdf"
    $relative = "pdf_batches/$batchName/$fileName"
    $sheet.Cells($r, 8).Value2 = "Batch $batch"
    $sheet.Hyperlinks.Add($sheet.Cells($r, 9), $relative, $null, $null, $fileName) | Out-Null
  }
  $sheet.Columns.Item(8).ColumnWidth = 12
  $sheet.Columns.Item(9).ColumnWidth = 40
  $book.Save()
  $book.Close($true)
  Write-Output "Updated rows=$($lastRow-1) output=$output"
} finally {
  $excel.Quit()
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
}
