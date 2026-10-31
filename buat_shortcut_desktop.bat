@echo off
set SCRIPT_DIR=%~dp0
set TARGET_BAT=%SCRIPT_DIR%run_app.bat
set SHORTCUT_PATH=%USERPROFILE%\Desktop\Galileo Vacuum Fall.lnk

echo Membuat shortcut di Desktop: "%SHORTCUT_PATH%"...

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%TARGET_BAT%'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Description = 'Galileo Vacuum Fall Experiment Controller'; $s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo [SUKSES] Shortcut berhasil dibuat di Desktop Anda!
) else (
    echo [GAGAL] Gagal membuat shortcut.
)
pause
