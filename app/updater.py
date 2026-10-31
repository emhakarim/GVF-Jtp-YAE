"""
Modul Auto-Updater Galileo Vacuum Fall Experiment
Mengintegrasikan Git Version Control untuk sinkronisasi otomatis via GitHub.
Engineered by Yotta Aksara Energi
"""

import os
import sys
import shutil
import subprocess
from PySide6.QtCore import QObject, QThread, Signal, Slot, QProcess
from PySide6.QtWidgets import QMessageBox

class UpdateWorker(QThread):
    """Worker background untuk menjalankan operasi Git tanpa memblokir GUI."""
    check_finished = Signal(bool, str, str)  # (has_update, remote_hash, commit_msg)
    update_progress = Signal(str)           # status progress string
    update_finished = Signal(bool, str)      # (success, message)

    def __init__(self, mode="CHECK", project_dir=None):
        super().__init__()
        self.mode = mode  # "CHECK" atau "APPLY"
        self.project_dir = project_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def run(self):
        if not shutil.which("git"):
            if self.mode == "CHECK":
                self.check_finished.emit(False, "", "Git CLI tidak ditemukan pada sistem.")
            else:
                self.update_finished.emit(False, "Git CLI tidak ditemukan.")
            return

        try:
            if self.mode == "CHECK":
                self._check_remote_update()
            elif self.mode == "APPLY":
                self._apply_remote_update()
        except Exception as e:
            if self.mode == "CHECK":
                self.check_finished.emit(False, "", f"Error: {e}")
            else:
                self.update_finished.emit(False, f"Gagal update: {e}")

    def _run_git(self, args: list) -> str:
        res = subprocess.run(
            ["git"] + args,
            cwd=self.project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=25
        )
        if res.returncode != 0:
            raise RuntimeError(res.stderr.strip() or f"Git error code {res.returncode}")
        return res.stdout.strip()

    def _check_remote_update(self):
        self.update_progress.emit("Menghubungi GitHub (git fetch)...")
        self._run_git(["fetch", "origin", "main"])

        local_hash = self._run_git(["rev-parse", "HEAD"])
        remote_hash = self._run_git(["rev-parse", "origin/main"])

        if local_hash != remote_hash:
            msg = self._run_git(["log", "-1", "--pretty=%s (%cr)", "origin/main"])
            self.check_finished.emit(True, remote_hash[:7], msg)
        else:
            self.check_finished.emit(False, local_hash[:7], "Sistem sudah menggunakan versi terbaru.")

    def _apply_remote_update(self):
        self.update_progress.emit("Menyinkronkan repositori (git reset --hard origin/main)...")
        self._run_git(["reset", "--hard", "origin/main"])

        req_path = os.path.join(self.project_dir, "requirements.txt")
        if os.path.exists(req_path):
            self.update_progress.emit("Memeriksa dependensi Python...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", req_path, "--quiet"],
                    cwd=self.project_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
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
                QMessageBox.information(
                    self.parent,
                    "Versi Terkini",
                    f"Sistem sudah menggunakan versi terbaru dari GitHub.\n(Commit: {commit_hash})"
                )

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
