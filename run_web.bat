@echo off
title Galileo Vacuum Fall - Jatim Park Mega Science Center dan Budaya
cd /d "%~dp0"

echo ===================================================
echo   GALILEO VACUUM FALL EXPERIMENT - HYBRID WEB SERVER
echo   Jatim Park Mega Science Center dan Budaya
echo   High-Speed Vision (OV2710 @ 100 FPS) ^& ESP32
echo   Crafted by Yotta Aksara Energi
echo ===================================================
echo.
echo [INFO] Menyiapkan server di http://localhost:8000 ...

:: Bersihkan port 8000 jika ada proses zombie sebelumnya
for /f "tokens=5" %%p in ('netstat -aon ^| findstr :8000') do taskkill /f /pid %%p >nul 2>&1

start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8000"

:: Jalankan via Python .venv atau py -3
if exist "%~dp0..\.venv\Scripts\python.exe" (
    "%~dp0..\.venv\Scripts\python.exe" -m uvicorn web_server:app --host 0.0.0.0 --port 8000
    if %ERRORLEVEL% equ 0 goto :done
)

:: Coba jalankan via py -3
py -3 -m uvicorn web_server:app --host 0.0.0.0 --port 8000
if %ERRORLEVEL% equ 0 goto :done

:: Fallback ke Python313 langsung di AppData
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" -m uvicorn web_server:app --host 0.0.0.0 --port 8000
    if %ERRORLEVEL% equ 0 goto :done
)

:: Fallback ke python di PATH
python -m uvicorn web_server:app --host 0.0.0.0 --port 8000
if %ERRORLEVEL% equ 0 goto :done

:error
echo.
echo [ERROR] Gagal menjalankan server web.
pause

:done
