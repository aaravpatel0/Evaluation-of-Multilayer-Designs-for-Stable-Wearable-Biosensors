$inputPath = (Resolve-Path -LiteralPath 'detailed/output/Biosensor_Proceeding_3D.docx').Path
$checkedPath = Join-Path (Split-Path $inputPath) 'Biosensor_Proceeding_3D_Layout_Checked.docx'
$pdfPath = Join-Path (Split-Path $inputPath) 'Biosensor_Proceeding_3D.pdf'
$wordLayout = New-Object -ComObject Word.Application
$wordLayout.Visible = $false
$wordLayout.DisplayAlerts = 0
try {
    $layoutDoc = $wordLayout.Documents.Open($inputPath, $false, $true)
    # Retain the conference layout, with the body starting continuously below the title.
    $layoutDoc.Sections.Item(2).PageSetup.SectionStart = 0
    for ($i = 1; $i -le 7; $i++) {
        $layoutDoc.Paragraphs.Item($i).Format.PageBreakBefore = 0
    }
    $layoutDoc.Repaginate()
    $titlePage = $layoutDoc.Paragraphs.Item(1).Range.Information(3)
    $abstractPage = $layoutDoc.Paragraphs.Item(7).Range.Information(3)
    if ($titlePage -ne 1 -or $abstractPage -ne 1) { throw 'Title and abstract must share page 1.' }
    $layoutDoc.SaveAs2($checkedPath, 16)
    $layoutDoc.ExportAsFixedFormat($pdfPath, 17)
    Write-Output ('Title page: ' + $titlePage + '; abstract page: ' + $abstractPage + '; total pages: ' + $layoutDoc.ComputeStatistics(2))
    $layoutDoc.Close(0)
} finally {
    if ($wordLayout.Documents.Count -eq 0) { $wordLayout.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($wordLayout) | Out-Null
}
Copy-Item -LiteralPath $checkedPath -Destination $inputPath -Force
