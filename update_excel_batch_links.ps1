$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$source = Join-Path $root '2025 TEM - CERTIFICATE ISSUE_SORTED_ASSIGNED.xlsx'
$output = Join-Path $root '2025 TEM - CERTIFICATE ISSUE_SORTED_WITH_BATCH_PDFS.xlsx'
Copy-Item -LiteralPath $source -Destination $output -Force
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
try {
  $book = $excel.Workbooks.Open($output)
  $sheet = $book.Worksheets.Item(1)
  $lastRow = $sheet.Cells($sheet.Rows.Count, 7).End(-4162).Row
  $sheet.Cells(1, 8).Value2 = 'BATCH PDF'
  $sheet.Cells(1, 8).Font.Bold = $true
  for ($r = 2; $r -le $lastRow; $r++) {
    $reg = ([string]$sheet.Cells($r, 7).Text).Trim()
    if ([string]::IsNullOrWhiteSpace($reg)) { continue }
    $batch = [int][math]::Ceiling(($r - 1) / 50)
    $fileName = ('Batch_{0:D3}.pdf' -f $batch)
    $relative = "sorted_batch_pdfs/$fileName"
    $sheet.Cells($r, 8).Formula = "=HYPERLINK(`"$relative`",`"$fileName`")"
  }
  $sheet.Columns.Item(8).ColumnWidth = 24
  $book.Save()
  $book.Close($true)
  Write-Output "Updated rows=$($lastRow-1) output=$output"
} finally {
  $excel.Quit()
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
}
