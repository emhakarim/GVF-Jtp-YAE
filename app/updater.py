"""
Modul Standalone Auto-Updater Galileo Vacuum Fall Experiment
Bekerja mandiri via GitHub REST API & HTTP ZIP Stream (Zero-Git Dependency).
Engineered by Yotta Aksara Energi
"""

import os
import sys
import json
import shutil
import zipfile
import urllib.request
import subprocess
from PySide6.QtCore import QObject, QThread, Signal, Slot, QProcess
from PySide6.QtWidgets import QMessageBox

GITHUB_REPO = "emhakarim/GVF-Jtp-YAE"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/commits/main"
ZIP_URL = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip"

class UpdateWorker(QThread):
    check_finished = Signal(bool, str, str)  # (has_update, remote_hash, commit_msg)
    update_progress = Signal(str)           # status progress
    update_finished = Signal(bool, str)      # (success, message)

    def __init__(self, mode="CHECK", project_dir=None):
        super().__init__()
        self.mode = mode
        self.project_dir = project_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.version_file = os.path.join(self.project_dir, "version.json")

    def run(self):
        try:
            if self.mode == "CHECK":
                self._check_update()
            elif self.mode == "APPLY":
                self._apply_update()
        except Exception as e:
            if self.mode == "CHECK":
                self.check_finished.emit(False, "", f"Error: {e}")
            else:
                self.update_finished.emit(False, f"Gagal update: {e}")

    def _get_local_commit(self) -> str:
        # 1. Coba baca version.json
        if os.path.exists(self.version_file):
            try:
                with open(self.version_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("commit", "")[:7]
            except Exception:
                pass

        # 2. Fallback baca git rev-parse jika ada git
        if shutil.which("git") and os.path.exists(os.path.join(self.project_dir, ".git")):
            try:
                res = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.project_dir,
                    stdout=subprocess.PIPE,
                    text=True,
                    timeout=5
                )
                if res.returncode == 0:
                    return res.stdout.strip()[:7]
            except Exception:
                pass
        return "UNKNOWN"

    def _check_update(self):
        self.update_progress.emit("Menghubungi GitHub API...")
        req = urllib.request.Request(API_URL, headers={"User-Agent": "GVF-Controller"})
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))

        remote_sha = data.get("sha", "")[:7]
        commit_msg = data.get("commit", {}).get("message", "").splitlines()[0]
        local_sha = self._get_local_commit()

        if local_sha != remote_sha or local_sha == "UNKNOWN":
            self.check_finished.emit(True, remote_sha, commit_msg)
        else:
            self.check_finished.emit(False, local_sha, "Sistem sudah menggunakan versi terbaru.")

    def _apply_update(self):
        self.update_progress.emit("Mengunduh arsip kode dari GitHub...")
        temp_zip = os.path.join(self.project_dir, "_update_pkg.zip")
        
        req = urllib.request.Request(ZIP_URL, headers={"User-Agent": "GVF-Controller"})
        with urllib.request.urlopen(req, timeout=40) as response, open(temp_zip, "wb") as out_file:
            shutil.copyfileobj(response, out_file)

        self.update_progress.emit("Mengekstrak pembaruan sistem...")
        extract_dir = os.path.join(self.project_dir, "_update_extracted")
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)

        with zipfile.ZipFile(temp_zip, "r") as z:
            z.extractall(extract_dir)

        # Cari root folder dalam ZIP (biasanya GVF-Jtp-YAE-main)
        subdirs = [os.path.join(extract_dir, d) for d in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, d))]
        source_root = subdirs[0] if subdirs else extract_dir

        # Salin file baru menimpa yang lama
        for item in os.listdir(source_root):
            if item in [".git", "_update_pkg.zip", "_update_extracted"]:
                continue
            src = os.path.join(source_root, item)
            dst = os.path.join(self.project_dir, item)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        # Update version.json dengan commit terbaru
        try:
            req = urllib.request.Request(API_URL, headers={"User-Agent": "GVF-Controller"})
            with urllib.request.urlopen(req, timeout=5) as response:
                api_data = json.loads(response.read().decode("utf-8"))
                new_sha = api_data.get("sha", "")[:7]
            with open(self.version_file, "w", encoding="utf-8") as vf:
                json.dump({"commit": new_sha, "branch": "main"}, vf, indent=2)
        except Exception:
            pass

        # Bersihkan temporary files
        if os.path.exists(temp_zip):
            try:
                os.remove(temp_zip)
            except Exception:
                pass
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)

        # Periksa requirements.txt
        req_path = os.path.join(self.project_dir, "requirements.txt")
        if os.path.exists(req_path):
            self.update_progress.emit("Memverifikasi dependensi...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", req_path, "--quiet"],
                    cwd=self.project_dir,
                    timeout=60
                )
            except Exception:
                pass

        self.update_finished.emit(True, "Pembaruan berhasil diterapkan. Memulai ulang aplikasi...")


class AppUpdater(QObject):
    """Pengelola Auto-Update dan Hot-Restart Aplikasi."""
    def __init__(self, parent_window=None, on_clean_teardown=None):
        super().__init__()
        self.parent = parent_window
        self.on_clean_teardown = on_clean_teardown
        self.worker = None

    def check_for_updates(self, is_silent=False):
        """Pemeriksaan update non-blocking."""
        if self.worker and self.worker.isRunning():
            return

        self.worker = UpdateWorker(mode="CHECK")
        if self.parent and hasattr(self.parent, "append_log"):
            self.worker.update_progress.connect(self.parent.append_log)
        self.worker.check_finished.connect(
            lambda has_up, r_hash, msg: self._on_check_done(has_up, r_hash, msg, is_silent)
        )
        self.worker.start()

    def apply_update_now(self):
        """Menerapkan update dan me-restart aplikasi."""
        if self.worker and self.worker.isRunning():
            return

        self.worker = UpdateWorker(mode="APPLY")
        if self.parent and hasattr(self.parent, "append_log"):
            self.worker.update_progress.connect(self.parent.append_log)
        self.worker.update_finished.connect(self._on_update_done)
        self.worker.start()

    def _on_check_done(self, has_update: bool, commit_hash: str, msg: str, is_silent: bool):
        if msg.startswith("Error:"):
            if not is_silent:
                if self.parent and hasattr(self.parent, "append_log"):
                    self.parent.append_log(f"[UPDATE ERROR] {msg}")
                QMessageBox.warning(self.parent, "Update Error", f"Gagal memeriksa pembaruan:\n{msg}")
            return

        if has_update:
            if self.parent and hasattr(self.parent, "btn_update"):
                self.parent.btn_update.setText("🔔 Update Siap!")
                self.parent.btn_update.setStyleSheet("""
                    background-color: #ea580c;
                    color: #ffffff;
                    font-weight: 800;
                    font-size: 11px;
                    border: 1px solid #c2410c;
                    border-radius: 5px;
                    padding: 5px 12px;
                """)
            
            if self.parent and hasattr(self.parent, "append_log"):
                self.parent.append_log(f"[UPDATE] Pembaruan baru tersedia di GitHub ({commit_hash}): {msg}")

            if not is_silent:
                reply = QMessageBox.question(
                    self.parent,
                    "Pembaruan Sistem Tersedia",
                    f"Pembaruan baru terdeteksi di GitHub!\n\n"
                    f"Commit: {commit_hash}\n"
                    f"Catatan: {msg}\n\n"
                    f"Terapkan pembaruan dan restart sekarang?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    self.apply_update_now()
        else:
            if not is_silent:
                if self.parent and hasattr(self.parent, "append_log"):
                    self.parent.append_log(f"[UPDATE] {msg} ({commit_hash})")
                
                reply = QMessageBox.question(
                    self.parent,
                    "Versi Terkini",
                    f"Sistem sudah menggunakan versi terbaru dari GitHub.\n(Commit: {commit_hash})\n\n"
                    f"Ingin me-restart aplikasi untuk me-reload antarmuka?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    if self.on_clean_teardown:
                        try:
                            self.on_clean_teardown()
                        except Exception:
                            pass
                    QProcess.startDetached(sys.executable, sys.argv)
                    sys.exit(0)

    def _on_update_done(self, success: bool, message: str):
        if success:
            if self.parent and hasattr(self.parent, "append_log"):
                self.parent.append_log(f"[UPDATE] {message}")
            
            # Lepas resource hardware (Camera & COM port)
            if self.on_clean_teardown:
                try:
                    self.on_clean_teardown()
                except Exception as e:
                    print(f"Teardown error: {e}")

            # Spawn proses Python baru dan terminate proses lama
            QProcess.startDetached(sys.executable, sys.argv)
            sys.exit(0)
        else:
            if self.parent and hasattr(self.parent, "append_log"):
                self.parent.append_log(f"[UPDATE ERROR] {message}")
            QMessageBox.warning(self.parent, "Gagal Update", message)
