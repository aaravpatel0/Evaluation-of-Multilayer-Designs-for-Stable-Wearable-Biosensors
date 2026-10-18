param([string]$InputDocx,[string]$OutputPdf)
$docPath = (Resolve-Path -LiteralPath $InputDocx -ErrorAction Stop).Path
$pdfPath = [System.IO.Path]::GetFullPath($OutputPdf)
$wordTask = New-Object -ComObject Word.Application
$wordTask.Visible = $false
$wordTask.DisplayAlerts = 0
try {
    $taskDocument = $wordTask.Documents.Open($docPath, $false, $true)
    $taskDocument.Repaginate()
    $taskDocument.ExportAsFixedFormat($pdfPath, 17)
    Write-Output ('Pages: ' + $taskDocument.ComputeStatistics(2))
    $taskDocument.Close(0)
} finally {
    if ($wordTask.Documents.Count -eq 0) { $wordTask.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($wordTask) | Out-Null
}
