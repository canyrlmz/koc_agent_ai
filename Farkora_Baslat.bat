@echo off
chcp 65001 >nul
title Farkora
cd /d "%~dp0"

rem Farkora: her acilista GitHub'daki son surumu indirir, sonra uygulamayi baslatir.
rem .env (anahtarlar) ve data (veriler) guncellemeden etkilenmez.

set "GIT=git"
where git >nul 2>nul || if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"

echo [1/3] Guncelleme kontrol ediliyor...
ver >nul
if exist ".git" "%GIT%" pull --ff-only
if errorlevel 1 echo     Guncelleme alinamadi (internet yok olabilir). Mevcut surumle devam ediliyor.

echo [2/3] Paketler kontrol ediliyor...
if not exist ".venv\Scripts\python.exe" python -m venv .venv
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt
if not exist ".env" copy ".env.example" ".env" >nul

echo [3/3] Farkora aciliyor: http://localhost:8765
echo     Bu pencere acik kaldigi surece uygulama calisir.
start "" cmd /c "timeout /t 6 >nul & start http://localhost:8765"
".venv\Scripts\python.exe" run.py
pause
