param([string]$InputDocx='advanced/output/Biosensor_Advanced_Proceeding.docx')
$sourcePath=(Resolve-Path -LiteralPath $InputDocx -ErrorAction Stop).Path
$folder=Split-Path $sourcePath
$stem=[System.IO.Path]::GetFileNameWithoutExtension($sourcePath)
$checkedPath=Join-Path $folder ($stem+'_Layout_Checked.docx')
$pdfPath=Join-Path $folder ($stem+'.pdf')
$wordStudy=New-Object -ComObject Word.Application
$wordStudy.Visible=$false
$wordStudy.DisplayAlerts=0
$paper=$null
try {
    $paper=$wordStudy.Documents.Open($sourcePath,$false,$true)
    if ($paper.Sections.Count -ge 2) { $paper.Sections.Item(2).PageSetup.SectionStart=0 }
    for ($i=1;$i -le [Math]::Min(15,$paper.Paragraphs.Count);$i++) {
        $paper.Paragraphs.Item($i).Format.PageBreakBefore=0
    }
    $paper.Repaginate()
    $titlePage=$paper.Paragraphs.Item(1).Range.Information(3)
    $abstractPage=$null
    for ($i=1;$i -le [Math]::Min(20,$paper.Paragraphs.Count);$i++) {
        if ($paper.Paragraphs.Item($i).Range.Text.Trim().StartsWith('Abstract')) {
            $abstractPage=$paper.Paragraphs.Item($i).Range.Information(3)
            break
        }
    }
    if ($titlePage -ne 1 -or $abstractPage -ne 1) { throw 'Title and abstract must share page 1.' }
    $paper.SaveAs2($checkedPath,16)
    $paper.ExportAsFixedFormat($pdfPath,17,$false,0,0,1,1,0,$true)
    $pages=$paper.ComputeStatistics(2)
    Write-Output ('Title page: '+$titlePage+'; abstract page: '+$abstractPage+'; pages: '+$pages)
} finally {
    if ($null -ne $paper) {
        try { $paper.Close(0) } catch { Write-Warning 'Could not close the study document after export.' }
    }
    if ($wordStudy.Documents.Count -eq 0) { $wordStudy.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($wordStudy) | Out-Null
}
Copy-Item -LiteralPath $checkedPath -Destination $sourcePath -Force
if ($pages -lt 6 -or $pages -gt 8) { throw 'Page count is outside the required 6–8 range; revise and re-render.' }
