@echo off
title Galileo Vacuum Fall - Jatim Park Mega Science Center dan Budaya
cd /d "%~dp0"

echo ===================================================
echo   GALILEO VACUUM FALL EXPERIMENT CONTROLLER
echo   Jatim Park Mega Science Center dan Budaya
echo   High-Speed Vision (OV2710 @ 100 FPS) ^& ESP32
echo   Crafted by Yotta Aksara Energi
echo ===================================================
echo.
echo [INFO] Meluncurkan antarmuka desktop PySide6...

:: 1. Prioritaskan Python 3.13 spesifik
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" app\main.py
    goto :done
)

:: 2. Prioritaskan py -3 launcher
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    py -3 app\main.py
    goto :done
)

:: 3. Fallback Python 3.11 spesifik
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" app\main.py
    goto :done
)

:: 4. Fallback python di PATH
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python app\main.py
    goto :done
)

:error
echo.
echo [ERROR] Gagal membuka aplikasi desktop.
pause

:done
