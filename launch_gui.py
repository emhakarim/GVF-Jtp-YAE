import os
import sys
import ctypes
from ctypes import wintypes

class STARTUPINFO(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('lpReserved', wintypes.LPWSTR),
        ('lpDesktop', wintypes.LPWSTR),
        ('lpTitle', wintypes.LPWSTR),
        ('dwX', wintypes.DWORD),
        ('dwY', wintypes.DWORD),
        ('dwXSize', wintypes.DWORD),
        ('dwYSize', wintypes.DWORD),
        ('dwXCountChars', wintypes.DWORD),
        ('dwYCountChars', wintypes.DWORD),
        ('dwFillAttribute', wintypes.DWORD),
        ('dwFlags', wintypes.DWORD),
        ('wShowWindow', wintypes.WORD),
        ('cbReserved2', wintypes.WORD),
        ('lpReserved2', ctypes.c_char_p),
        ('hStdInput', wintypes.HANDLE),
        ('hStdOutput', wintypes.HANDLE),
        ('hStdError', wintypes.HANDLE)
    ]

class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('hProcess', wintypes.HANDLE),
        ('hThread', wintypes.HANDLE),
        ('dwProcessId', wintypes.DWORD),
        ('dwThreadId', wintypes.DWORD)
    ]

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(base_dir, "app", "main.py")
    
    python_exe = sys.executable
    cmd_line = f'cmd.exe /k "{python_exe}" "{main_py}"'

    si = STARTUPINFO()
    si.cb = ctypes.sizeof(STARTUPINFO)
    si.lpDesktop = "WinSta0\\Default"
    si.dwFlags = 0x00000001  # STARTF_USESHOWWINDOW
    si.wShowWindow = 1       # SW_SHOWNORMAL

    pi = PROCESS_INFORMATION()

    CREATE_NEW_CONSOLE = 0x00000010
    success = ctypes.windll.kernel32.CreateProcessW(
        None,
        cmd_line,
        None,
        None,
        False,
        CREATE_NEW_CONSOLE,
        None,
        base_dir,
        ctypes.byref(si),
        ctypes.byref(pi)
    )

    if success:
        print(f"[LAUNCHER] Berhasil meluncurkan GUI ke WinSta0\\Default (PID: {pi.dwProcessId})")
        # Tutup handle proses & thread agar tidak leak di launcher
        ctypes.windll.kernel32.CloseHandle(pi.hProcess)
        ctypes.windll.kernel32.CloseHandle(pi.hThread)
        sys.exit(0)
    else:
        err = ctypes.GetLastError()
        print(f"[LAUNCHER] Gagal meluncurkan GUI: Error code {err}", file=sys.stderr)
        sys.exit(err)

if __name__ == "__main__":
    main()
