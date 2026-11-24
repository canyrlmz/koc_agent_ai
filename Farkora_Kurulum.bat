@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
title Farkora Kurulum
cd /d "%~dp0"
set "REPO=https://github.com/canyrlmz/koc_agent_ai.git"

echo ================================================================
echo   FARKORA KURULUMU
echo   Gereken her şey otomatik kurulacak. İnternet bağlı olmalı.
echo   Süre: 10-20 dakika. Bu pencereyi kapatmayın.
echo   Windows izin isterse "Evet" deyin.
echo ================================================================

set "WG=1"
where winget >nul 2>nul || set "WG="

rem ---------------------------------------------------------------
echo.
echo [1/6] Python kontrol ediliyor...
call :findpython
if defined PY goto :python_ok
if not defined WG goto :no_python
echo     Python bulunamadı, kuruluyor...
winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
call :findpython
if not defined PY goto :no_python
:python_ok
echo     Tamam.

rem ---------------------------------------------------------------
echo.
echo [2/6] Git kontrol ediliyor (otomatik güncelleme için)...
call :findgit
if defined GIT goto :git_ok
if not defined WG goto :git_skip
echo     Git bulunamadı, kuruluyor...
winget install -e --id Git.Git --silent --accept-package-agreements --accept-source-agreements
call :findgit
if defined GIT goto :git_ok
:git_skip
echo     Git kurulamadı. Uygulama çalışır ama kendini güncelleyemez.
goto :step3
:git_ok
echo     Tamam.

rem ---------------------------------------------------------------
:step3
echo.
echo [3/6] FFmpeg kontrol ediliyor (ses, video ve fotoğraf için)...
where ffmpeg >nul 2>nul && goto :ffmpeg_ok
if not defined WG goto :ffmpeg_skip
echo     FFmpeg bulunamadı, kuruluyor...
winget install -e --id Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto :ffmpeg_skip
:ffmpeg_ok
echo     Tamam.
goto :step4
:ffmpeg_skip
echo     FFmpeg kurulamadı. Ses, video ve fotoğraf seansları dışında her şey çalışır.

rem ---------------------------------------------------------------
:step4
echo.
echo [4/6] Uygulama paketleri kuruluyor. Bu adım 5-15 dakika sürebilir...
if not exist ".venv\Scripts\python.exe" "!PY!" -m venv .venv
if not exist ".venv\Scripts\python.exe" goto :pip_fail
".venv\Scripts\python.exe" -m pip install -q --upgrade pip --disable-pip-version-check
".venv\Scripts\python.exe" -m pip install -r requirements.txt --disable-pip-version-check
if errorlevel 1 goto :pip_fail
echo     Tamam.

rem ---------------------------------------------------------------
echo.
echo [5/6] Ayar dosyası hazırlanıyor...
if exist ".env" goto :env_exists
copy ".env.example" ".env" >nul
echo     .env dosyası oluşturuldu.
goto :step6
:env_exists
echo     .env zaten var, dokunulmadı.

rem ---------------------------------------------------------------
:step6
echo.
echo [6/6] Otomatik güncelleme ve masaüstü kısayolu...
if not defined GIT goto :shortcut
if exist ".git" goto :shortcut
"!GIT!" init -q
"!GIT!" remote add origin %REPO%
"!GIT!" fetch -q origin main
if errorlevel 1 goto :git_fetch_fail
"!GIT!" reset -q origin/main
"!GIT!" branch -q -M main
"!GIT!" branch -q -u origin/main
echo     Otomatik güncelleme açık: Farkora her açılışta son sürümü alır.
goto :shortcut
:git_fetch_fail
echo     GitHub'a bağlanılamadı; otomatik güncelleme şimdilik kapalı.
rmdir /s /q ".git" >nul 2>nul
:shortcut
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Masaustu_Kisayolu.ps1"

rem ---------------------------------------------------------------
echo.
echo ================================================================
echo   KURULUM TAMAMLANDI
echo ================================================================
echo.
echo   SON ADIM: Yapay zekâ anahtarı (ücretsiz, isteğe bağlı)
echo   ----------------------------------------------------------
echo   1. Kendi Google hesabınızla şu adrese girin:
echo        https://aistudio.google.com/app/apikey
echo   2. "Create API key" düğmesiyle bir anahtar oluşturup kopyalayın.
echo   3. .env dosyasında şu iki satırı bulun ve düzenleyin:
echo        LLM_PROVIDER=gemini
echo        GEMINI_API_KEY=kopyaladığınız-anahtar
echo   4. Dosyayı kaydedin (Ctrl+S) ve kapatın.
echo.
echo   Anahtar girilmezse uygulama örnek cevaplarla (Demo modu) çalışır.
echo   .env dosyası yalnızca bu bilgisayarda kalır; kimseyle paylaşmayın.
echo   Ücretsiz anahtarla gerçek danışan bilgisi girmeyin (KVKK).
echo.
echo   UYGULAMAYI AÇMAK
echo   ----------------------------------------------------------
echo   Masaüstündeki "Farkora" simgesine çift tıklayın.
echo   İlk açılışta kendi yönetici hesabınızı ve şifrenizi oluşturun.
echo.
choice /c EH /m "Anahtar sayfası ve .env dosyası şimdi açılsın mı"
if errorlevel 2 goto :ask_start
start "" "https://aistudio.google.com/app/apikey"
notepad ".env"
:ask_start
echo.
choice /c EH /m "Farkora şimdi açılsın mı"
if errorlevel 2 goto :end
start "" "%~dp0Farkora_Baslat.bat"
goto :end

rem ===============================================================
:no_python
echo.
echo   HATA: Python kurulamadı.
echo   python.org adresinden Python 3.12 indirip kurun. Kurulumun ilk
echo   ekranında "Add python.exe to PATH" kutusunu işaretleyin.
echo   Sonra bu dosyayı tekrar çalıştırın.
goto :end

:pip_fail
echo.
echo   HATA: Paketler kurulamadı. İnternet bağlantısını kontrol edip
echo   bu dosyayı tekrar çalıştırın.
goto :end

:end
echo.
pause
exit /b

rem ===============================================================
:findpython
set "PY="
for %%C in (python py) do (
  if not defined PY (
    %%C -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul && set "PY=%%C"
  )
)
if defined PY exit /b
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
  if exist "%%D\python.exe" (
    "%%D\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul && set "PY=%%D\python.exe"
  )
)
exit /b

:findgit
set "GIT="
where git >nul 2>nul && set "GIT=git"
if defined GIT exit /b
if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
exit /b
