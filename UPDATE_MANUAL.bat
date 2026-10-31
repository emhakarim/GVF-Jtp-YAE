@echo off
title Update Sistem Galileo Vacuum Fall - JTP Mega Science Center
cd /d "%~dp0"

echo ===================================================
echo   PEMBARUAN SISTEM GALILEO VACUUM FALL
echo   Mengunduh versi terbaru langsung dari GitHub...
echo ===================================================
echo.

:: 1. Unduh arsip terbaru dari GitHub
echo [1/3] Mengunduh pembaruan dari GitHub...
curl.exe -L -o _update.zip https://github.com/emhakarim/GVF-Jtp-YAE/archive/refs/heads/main.zip
if not exist _update.zip (
    echo [ERROR] Gagal mengunduh file dari GitHub. Periksa koneksi internet Anda.
    pause
    exit /b 1
)

:: 2. Ekstrak arsip
echo [2/3] Mengekstrak file pembaruan...
powershell -Command "Expand-Archive -Path '_update.zip' -DestinationPath '_temp_extracted' -Force"

:: 3. Salin file menimpa proyek lokal
echo [3/3] Menerapkan pembaruan sistem...
xcopy /s /e /y "_temp_extracted\GVF-Jtp-YAE-main\*" "." >nul

:: Bersihkan file sementara
del /f /q _update.zip >nul 2>&1
rd /s /q _temp_extracted >nul 2>&1

echo.
echo ===================================================
echo   SUKSES: Sistem telah diperbarui ke versi terbaru!
echo   Membuka kembali aplikasi...
echo ===================================================
timeout /t 2 >nul

call run_app.bat
