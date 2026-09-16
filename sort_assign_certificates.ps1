$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$source = Join-Path $root '2025 TEM - CERTIFICATE ISSUE.xlsx'
$output = Join-Path $root '2025 TEM - CERTIFICATE ISSUE_SORTED_ASSIGNED.xlsx'
Copy-Item -LiteralPath $source -Destination $output -Force
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
try {
  $book = $excel.Workbooks.Open($output)
  $sheet = $book.Worksheets.Item(1)
  $lastRow = $sheet.Cells($sheet.Rows.Count, 7).End(-4162).Row
  $data = $sheet.Range("A2:G$lastRow").Value2
  $records = @()
  for ($i = 1; $i -le ($lastRow - 1); $i++) {
    $vals = @($data[$i,1],$data[$i,2],$data[$i,3],$data[$i,4],$data[$i,5],$data[$i,6],$data[$i,7])
    $records += [pscustomobject]@{Name=([string]$vals[3]).Trim(); Values=$vals}
  }
  $records = $records | Sort-Object @{Expression={if([string]::IsNullOrWhiteSpace($_.Name)){1}else{0}}}, @{Expression={$_.Name}}
  $outData = New-Object 'object[,]' ($records.Count,7)
  for ($i = 0; $i -lt $records.Count; $i++) {
    $vals = $records[$i].Values
    $outData[$i,0] = $i + 1
    $outData[$i,1] = $vals[1]
    $outData[$i,2] = $vals[2]
    $outData[$i,3] = $vals[3]
    $outData[$i,4] = $vals[4]
    $outData[$i,5] = $vals[5]
    $outData[$i,6] = ('BAATEM25-{0:D5}' -f (26082 + $i + 1))
  }
  $sheet.Range("A2:G$lastRow").Value2 = $outData
  $sheet.Cells(1,8).ClearContents()
  $book.Save()
  $book.Close($true)
  Write-Output "Sorted and assigned records=$($records.Count) output=$output"
} finally {
  $excel.Quit()
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
}
