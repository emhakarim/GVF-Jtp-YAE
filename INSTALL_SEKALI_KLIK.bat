@echo off
setlocal enabledelayedexpansion
title Setup Otomatis - Galileo Vacuum Fall Experiment
cd /d "%~dp0"

echo =======================================================================
echo   GALILEO VACUUM FALL EXPERIMENT - AUTO INSTALLER PC BARU
echo   Jatim Park Mega Science Center dan Budaya
echo   Crafted by Yotta Aksara Energi
echo =======================================================================
echo.
echo [1/4] Memeriksa instalasi Python di sistem...

set "PY_CMD="

:: Cek py launcher
py -3 -V >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=py -3"
    goto :python_found
)

:: Cek python di PATH
python -V >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=python"
    goto :python_found
)

:: Cek path default AppData Python 3.12 / 3.13 / 3.11
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    goto :python_found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    goto :python_found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :python_found
)

echo.
echo [PERINGATAN] Python belum terpasang.
echo [INFO] Mengunduh Python 3.12 resmi dari python.org...
set "PY_INSTALLER=%TEMP%\python_setup_312.exe"

powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe', '%PY_INSTALLER%')"
if not exist "%PY_INSTALLER%" (
    echo [ERROR] Gagal mengunduh Python. Pastikan komputer terhubung ke internet.
    goto :error
)

echo [INFO] Memasang Python secara otomatis (Silent Install)...
"%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0
del /f /q "%PY_INSTALLER%" >nul 2>&1

:: Refresh path untuk sesi saat ini
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

:python_found
echo [OK] Python terdeteksi aktif.
echo.

echo [2/4] Memeriksa Microsoft Visual C++ Redistributable (x64)...
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64" /v Installed >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [OK] Visual C++ Runtime sudah terpasang.
) else (
    echo [INFO] Mengunduh Microsoft Visual C++ Redistributable x64...
    set "VC_INSTALLER=%TEMP%\vc_redist.x64.exe"
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://aka.ms/vs/17/release/vc_redist.x64.exe', '%VC_INSTALLER%')"
    if exist "%VC_INSTALLER%" (
        echo [INFO] Memasang Visual C++ Runtime...
        "%VC_INSTALLER%" /install /passive /norestart
        del /f /q "%VC_INSTALLER%" >nul 2>&1
        echo [OK] Visual C++ Runtime berhasil dipasang.
    ) else (
        echo [LEWATI] Pemasangan VC++ dilewati, melanjutkan dependensi...
    )
)
echo.

echo [3/4] Memasang seluruh pustaka Python (PySide6, OpenCV, NumPy, Serial, dll)...
%PY_CMD% -m pip install --upgrade pip >nul 2>&1
%PY_CMD% -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Gagal menginstal dependensi pustaka Python.
    goto :error
)
echo [OK] Seluruh pustaka dependensi terpasang lengkap.
echo.

echo [4/4] Memverifikasi integritas sistem...
%PY_CMD% -c "import PySide6, cv2, numpy, serial, matplotlib, fastapi, uvicorn; print('VERIFIKASI_BERHASIL')" > "%TEMP%\verify.txt" 2>&1
findstr /i "VERIFIKASI_BERHASIL" "%TEMP%\verify.txt" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Verifikasi pustaka gagal. Detail error:
    type "%TEMP%\verify.txt"
    del /f /q "%TEMP%\verify.txt" >nul 2>&1
    goto :error
)
del /f /q "%TEMP%\verify.txt" >nul 2>&1

echo.
echo =======================================================================
echo   SELURUH PERANGKAT LUNAK DAN KELENGKAPAN SELESAI DIPASANG!
echo   Sistem Galileo Vacuum Fall siap digunakan di PC ini.
echo =======================================================================
echo.
echo Tekan tombol apa saja untuk langsung membuka aplikasi desktop...
pause >nul

start "" "%~dp0run_app.bat"
exit /b 0

:error
echo.
echo =======================================================================
echo   PROSES INSTALASI MENGALAMI KENDALA.
echo   Pastikan koneksi internet aktif dan coba jalankan kembali file ini.
echo =======================================================================
echo.
pause
exit /b 1

