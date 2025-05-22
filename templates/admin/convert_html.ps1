Get-ChildItem *.html | ForEach-Object {
    $htmlFileName = $_.BaseName
    $txtFileName = $htmlFileName + ".txt"
    Get-Content $_.FullName | Out-File $txtFileName -Encoding UTF8
}