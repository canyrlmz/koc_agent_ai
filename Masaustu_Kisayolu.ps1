# Masaüstüne Farkora kısayolu ekler (bir kez çalıştırmak yeterli).
#   -Yayin  : "Farkora Yayınla" (bu bilgisayardan siteyi internete açar, link verir)
#   (yok)   : "Farkora" (uygulamayı bu bilgisayarda açar, her açılışta günceller)
param([switch]$Yayin)
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($Yayin) { $name = "Farkora Yayınla"; $target = Join-Path $root "Farkora_Yayinla.bat" }
else        { $name = "Farkora";          $target = Join-Path $root "Farkora_Baslat.bat" }
$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktop "$name.lnk"))
$lnk.TargetPath = $target
$lnk.WorkingDirectory = $root
$lnk.IconLocation = (Join-Path $root "static\farkora.ico")
$lnk.Description = "Farkora - yapay zekâ destekli koçluk"
$lnk.Save()
Write-Host "Masaüstüne eklendi: $name" -ForegroundColor Green
