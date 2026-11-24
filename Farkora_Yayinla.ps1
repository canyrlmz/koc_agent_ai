# Farkora'yı internete açar: uygulamayı başlatır, Cloudflare geçici tüneliyle herkese açık bir link verir.
# Bu pencere açık kaldığı sürece link çalışır. Kapatmak için Enter'a basın.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$Host.UI.RawUI.WindowTitle = "Farkora yayında"
$log = Join-Path $env:TEMP "farkora_tunel.log"
Remove-Item $log -ErrorAction SilentlyContinue

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    Write-Host "cloudflared bulunamadı. Kurmak için: winget install Cloudflare.cloudflared" -ForegroundColor Red
    Read-Host "Kapatmak için Enter"; exit 1
}

Write-Host "[1/3] Güvenli tünel açılıyor..." -ForegroundColor Cyan
$tunnel = Start-Process cloudflared -ArgumentList "tunnel --no-autoupdate --url http://127.0.0.1:8765" `
    -RedirectStandardError $log -WindowStyle Hidden -PassThru
$url = $null
for ($i = 0; $i -lt 60 -and -not $url; $i++) {
    Start-Sleep -Seconds 1
    if (Test-Path $log) {
        $m = Select-String -Path $log -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -First 1
        if ($m) { $url = $m.Matches[0].Value }
    }
}
if (-not $url) {
    Write-Host "Tünel açılamadı (internet bağlantısını kontrol edin). Ayrıntı: $log" -ForegroundColor Red
    Stop-Process -Id $tunnel.Id -ErrorAction SilentlyContinue
    Read-Host "Kapatmak için Enter"; exit 1
}

Write-Host "[2/3] Farkora başlatılıyor..." -ForegroundColor Cyan
$server = $null
$running = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "    Farkora zaten açık; mevcut uygulama kullanılıyor." -ForegroundColor Yellow
} else {
    $env:PUBLIC_BASE_URL = $url   # gözlemci bağlantıları da bu linkle gitsin
    $server = Start-Process ".venv\Scripts\python.exe" -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8765" `
        -WindowStyle Minimized -PassThru
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Seconds 1
        try { if ((Invoke-WebRequest "http://127.0.0.1:8765/" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200) { break } } catch {}
    }
}

Write-Host "[3/3] Link hazır" -ForegroundColor Cyan
Set-Clipboard -Value $url
$url | Out-File (Join-Path $root "yayin_linki.txt") -Encoding utf8
Write-Host ""
Write-Host "   $url" -ForegroundColor Green
Write-Host ""
Write-Host "   Link panoya kopyalandı; hocaya WhatsApp'tan yapıştırıp gönderebilirsiniz."
Write-Host "   Not: Bu link her açılışta değişir. Bu pencere ve bilgisayar açık kaldığı sürece çalışır."
Write-Host ""
Start-Process $url
Read-Host "Yayını kapatmak için Enter'a basın"

Stop-Process -Id $tunnel.Id -ErrorAction SilentlyContinue
if ($server) { Stop-Process -Id $server.Id -ErrorAction SilentlyContinue }
Write-Host "Yayın kapatıldı."
