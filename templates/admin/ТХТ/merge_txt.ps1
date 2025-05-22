$outputFileName = "объединенный_файл.txt"

# Путь к папке
$folderPath = "F:\МебельПрайсПро\templates\admin\ТХТ"

# Перейти в папку
Set-Location $folderPath

# Удаляем файл, если он существует
if (Test-Path $outputFileName) {
    Remove-Item $outputFileName
}

# Получаем все текстовые файлы и объединяем их
Get-ChildItem -Path $folderPath -Filter *.txt | ForEach-Object {
    # Добавляем название файла
    Add-Content -Path $outputFileName -Value "`n--- Файл: $($_.Name) ---`n"
    # Добавляем содержимое файла
    Get-Content $_.FullName | Add-Content -Path $outputFileName
}

Write-Host "Файлы объединены в $outputFileName"