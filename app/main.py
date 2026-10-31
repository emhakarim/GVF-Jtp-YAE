"""
Entry Point Aplikasi Desktop Galileo Vacuum Fall Experiment
Mengintegrasikan UI Dashboard, Camera Worker (100 FPS), Scene Detector,
Hardware Comm Manager (ESP32), dan Physics Engine.
"""

import sys
import time
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Slot, QTimer

from ui_dashboard import DashboardWindow
from camera_worker import CameraWorker
from scene_detector import SceneDetector
from comm_manager import CommManager
from physics_engine import PhysicsEngine
from updater import AppUpdater

class GalileoControllerApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = DashboardWindow()
        
        # Inisialisasi Modul Inti
        self.physics = PhysicsEngine(height_meters=2.0, delta_h_meters=0.002)
        self.detector = SceneDetector(buffer_size=120)
        self.comm = CommManager()
        self.camera = CameraWorker(camera_index=0, target_fps=100, width=640, height=480, detector=self.detector)
        
        self.current_t_trigger = 0.0
        self.current_mode = "BOTH"
        self.replay_frames_cache = []
        self.is_inspecting_replay = False

        # Stopwatch Penghitung Waktu Real-time
        self.stopwatch_timer = QTimer(self.window)
        self.stopwatch_timer.timeout.connect(self._update_live_stopwatch)

        # Pengelola Pembaruan Sistem (Git Auto-Updater)
        self.updater = AppUpdater(parent_window=self.window, on_clean_teardown=self._clean_teardown)

        self._connect_signals()
        self._populate_cameras()
        self._populate_serial_ports()

        # Silent check update 4 detik setelah boot tanpa mengganggu user
        QTimer.singleShot(4000, lambda: self.updater.check_for_updates(is_silent=True))

    def _connect_signals(self):
        # 1. Camera Signals
        self.camera.display_frame_ready.connect(self._on_display_frame)
        self.camera.fps_updated.connect(self._on_fps_updated)
        self.camera.camera_status.connect(self._on_camera_status)

        # 2. Scene Detector Signals
        self.detector.arrival_detected.connect(self._on_arrival_detected)
        self.detector.motion_level_updated.connect(self._on_motion_level)
        self.detector.slowmo_replay_ready.connect(self._on_replay_ready)

        # 3. Comm Manager Signals
        self.comm.connection_status.connect(self._on_comm_status)
        self.comm.release_confirmed.connect(self._on_release_confirmed)
        self.comm.log_message.connect(self.window.append_log)

        # 4. Camera Switch Actions
        self.window.btn_refresh_cameras.clicked.connect(self._populate_cameras)
        self.window.combo_cameras.currentIndexChanged.connect(self._apply_camera_selection)

        # 5. UI Button Actions
        self.window.btn_fullscreen.clicked.connect(self.window.toggle_fullscreen)
        self.window.btn_update.clicked.connect(lambda: self.updater.check_for_updates(is_silent=False))
        self.window.btn_connect_serial.clicked.connect(self._toggle_esp_connection)

        self.window.btn_drop_feather.clicked.connect(self._stage_feather)
        self.window.btn_drop_ball.clicked.connect(self._stage_ball)
        self.window.btn_drop_both.clicked.connect(self._execute_bucket_drop)
        self.window.btn_reset.clicked.connect(self._execute_reset)

        # 6. UI Slider & Slow-Mo Step Buttons
        self.window.slider_thresh.valueChanged.connect(self._on_thresh_slider_changed)
        self.window.replay_slider.valueChanged.connect(self._on_replay_scrubber_changed)
        self.window.btn_step_prev.clicked.connect(self._step_prev_replay)
        self.window.btn_step_next.clicked.connect(self._step_next_replay)
        self.window.btn_live_feed.clicked.connect(self._resume_live_feed)

    def _clean_teardown(self):
        """Melepas resource hardware camera & serial com sebelum restart sistem."""
        try:
            self.camera.stop()
        except Exception:
            pass
        try:
            self.comm.disconnect()
        except Exception:
            pass


    def _populate_cameras(self):
        cams = CameraWorker.list_available_cameras()
        self.window.combo_cameras.clear()
        for cam_idx, label in cams:
            self.window.combo_cameras.addItem(label, userData=cam_idx)
        self.window.append_log(f"[CAMERA] Ditemukan {len(cams)} opsi input video.")

    def _apply_camera_selection(self):
        selected_idx = self.window.combo_cameras.currentData()
        if selected_idx is not None:
            self.camera.switch_camera(selected_idx)
            self.window.append_log(f"[CAMERA] Mengganti kamera ke index: {selected_idx}")


    def _populate_serial_ports(self):
        ports = self.comm.list_serial_ports()
        self.window.combo_ports.clear()
        if ports:
            self.window.combo_ports.addItems(ports)
            self.window.append_log(f"[PORT] Ditemukan {len(ports)} port serial USB.")
        else:
            self.window.combo_ports.addItem("None")
        # Opsi Wi-Fi AP terintegrasi
        self.window.combo_ports.addItem("Wi-Fi AP: 192.168.4.1")

    def _toggle_esp_connection(self):
        if self.comm.is_serial_connected or self.comm.is_wifi_connected:
            self.comm.disconnect_serial()
            self.comm.disconnect_wifi()
            self.window.btn_connect_serial.setText("Hubungkan")
            self.window.btn_connect_serial.setStyleSheet("")
            self.window.append_log("[ESP32] Koneksi terputus.")
        else:
            selected = self.window.combo_ports.currentText()
            if "Wi-Fi" in selected:
                self.window.append_log("[ESP32] Menghubungkan via Wi-Fi WebSocket (192.168.4.1)...")
                self.comm.connect_wifi("192.168.4.1")
            elif selected and selected != "None":
                port = selected.split()[0].strip()
                self.window.append_log(f"[ESP32] Menghubungkan via Serial USB ({port})...")
                self.comm.connect_serial(port, 115200)

    def _update_live_stopwatch(self):
        elapsed_ms = (time.perf_counter() - self.current_t_trigger) * 1000.0
        self.window.val_dt.setText(f"{elapsed_ms:.1f}")

    def _stage_feather(self):
        """Tahap 1A: Memuat bulu ke dalam bucket penampung (Kamera & Stopwatch TIDAK aktif)."""
        self.comm.trigger_drop_feather()
        self.window.lbl_status_feather.setText("Bulu: Siap di Bucket [OK]")
        self.window.lbl_status_feather.setStyleSheet("font-size: 10px; font-weight: 700; color: #16a34a;")
        self.window.append_log("[STAGING] Servo 1 melepas bulu ke dalam wadah penampung.")

    def _stage_ball(self):
        """Tahap 1B: Memuat bola besi ke dalam bucket penampung (Kamera & Stopwatch TIDAK aktif)."""
        self.comm.trigger_drop_ball()
        self.window.lbl_status_ball.setText("Bola: Siap di Bucket [OK]")
        self.window.lbl_status_ball.setStyleSheet("font-size: 10px; font-weight: 700; color: #16a34a;")
        self.window.append_log("[STAGING] Servo 2 melepas bola besi ke dalam wadah penampung.")

    def _execute_bucket_drop(self):
        """Tahap 2: Buka bucket penampung - Kedua objek jatuh bersamaan (Kamera & Stopwatch AKTIF)."""
        self.is_inspecting_replay = False
        self.current_mode = "BOTH"
        self.current_t_trigger = time.perf_counter()

        # Mulai stopwatch dinamis pada UI Desktop
        self.window.val_g.setText("MENGUKUR...")
        self.window.val_v.setText("MENGUKUR...")
        self.window.val_dev.setText("---")
        self.stopwatch_timer.start(10)  # Refresh tiap 10 ms

        # Aktifkan detektor scene kamera 100 FPS
        self.detector.arm_detection(target_mode="BOTH", t_trigger=self.current_t_trigger)

        # Buka pintu bucket penampung via ESP32 (Servo 3)
        self.comm.trigger_drop_both()

        if self.camera.is_mock:
            self.camera.trigger_mock_drop("BOTH")

        self.window.append_log("[EKSPERIMEN] Pintu bucket terbuka! Stopwatch & Detektor 100 FPS AKTIF.")

    def _execute_reset(self):
        """Tahap 3: Mereset ketiga servo ke posisi penahan (Standby)."""
        self.is_inspecting_replay = False
        self.stopwatch_timer.stop()
        self.detector.reset()
        self.comm.reset_servos()
        self.window.val_dt.setText("0.0")
        self.window.val_g.setText("0.000")
        self.window.val_g_err.setText("Toleransi Galat: ± 0.00 m/s²")
        self.window.val_v.setText("0.00 m/s")
        self.window.val_dev.setText("0.00 %")
        self.window.lbl_status_feather.setText("Bulu: Belum Dimuat")
        self.window.lbl_status_feather.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8;")
        self.window.lbl_status_ball.setText("Bola: Belum Dimuat")
        self.window.lbl_status_ball.setStyleSheet("font-size: 10px; font-weight: 700; color: #94a3b8;")
        self.window.replay_lbl.setText("Standby (0 Frame)")
        self.window.lbl_frame_time.setText("LIVE")
        self.window.append_log("[RESET] Semua servo kembali ke posisi penahan (Standby).")

    @Slot(np.ndarray)
    def _on_display_frame(self, annotated_frame: np.ndarray):
        # Tampilan GUI diperbarui dari frame live jika tidak sedang inspeksi slow-mo replay
        if not self.is_inspecting_replay:
            self.window.update_camera_view(annotated_frame)

    @Slot(float)
    def _on_fps_updated(self, fps: float):
        self.window.fps_badge.setText(f"● CAM: {fps:.1f} FPS")

    @Slot(bool, str)
    def _on_camera_status(self, is_hw: bool, msg: str):
        self.window.append_log(f"[CAMERA] {msg}")

    @Slot(str, bool, str)
    def _on_comm_status(self, proto: str, connected: bool, msg: str):
        status_txt = f"● ESP32: {'OK' if connected else 'STANDBY'}"
        self.window.badge_status.setText(status_txt)
        if connected:
            self.window.badge_status.setStyleSheet("background-color: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; font-weight: 800; font-size: 10px; padding: 4px 10px; border-radius: 14px; font-family: monospace;")
            self.window.btn_connect_serial.setText("Putus")
            self.window.btn_connect_serial.setStyleSheet("background-color: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; font-weight: 700;")
        else:
            self.window.badge_status.setStyleSheet("background-color: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; font-weight: 800; font-size: 10px; padding: 4px 10px; border-radius: 14px; font-family: monospace;")
            self.window.btn_connect_serial.setText("Hubungkan")
            self.window.btn_connect_serial.setStyleSheet("")

    @Slot(str, int, float)
    def _on_release_confirmed(self, target: str, t_esp_micros: int, pc_time: float):
        self.current_t_trigger = pc_time

    @Slot(float)
    def _on_motion_level(self, level: float):
        # Non-blocking push ke ring buffer (0% CPU load, bebas lag)
        self.window.plot_canvas.push_data_point(level)

    @Slot(dict)
    def _on_arrival_detected(self, event_data: dict):
        """Kalkulasi kinematika saintifik saat benda menyentuh garis finish kamera."""
        # Hentikan stopwatch dinamis
        self.stopwatch_timer.stop()

        t_arrival = event_data["timestamp"]
        t_start = event_data["t_armed"]
        dt = t_arrival - t_start

        # Perhitungan nilai g dan ketidakpastian fisis
        g_val, g_err = self.physics.calculate_gravity_from_time(dt, delta_t_err=0.010)
        v_final = self.physics.theoretical_impact_velocity(g_val)
        deviation = ((g_val - self.physics.G_STANDARD) / self.physics.G_STANDARD) * 100.0

        # Update Telemetri UI (Nilai Highlighted Dominan)
        self.window.val_g.setText(f"{g_val:.3f}")
        self.window.val_g_err.setText(f"Toleransi Galat: ± {g_err:.2f} m/s²")
        self.window.val_dt.setText(f"{dt * 1000.0:.1f}")
        self.window.val_v.setText(f"{v_final:.2f} m/s")
        self.window.val_dev.setText(f"{deviation:+.2f} %")

        self.window.append_log(
            f"[RESULT] Deteksi Sukses: dt={dt*1000.0:.1f} ms | g={g_val:.3f} m/s² (dev: {deviation:+.2f}%)"
        )

    @Slot(list)
    def _on_replay_ready(self, frames_list: list):
        self.replay_frames_cache = frames_list
        total = len(frames_list)
        if total > 0:
            self.window.replay_slider.setEnabled(True)
            self.window.replay_slider.setRange(0, total - 1)
            self.window.btn_step_prev.setEnabled(True)
            self.window.btn_step_next.setEnabled(True)
            self.window.replay_lbl.setText(f"{total} Frame Siap (Geser untuk Replay)")
            self.window.append_log(f"[SLOW-MO] Buffer instan terisi: {total} frame 100 FPS.")

    def _on_replay_scrubber_changed(self, idx: int):
        self.is_inspecting_replay = True
        if 0 <= idx < len(self.replay_frames_cache):
            frame_item = self.replay_frames_cache[idx]
            frame_img = frame_item[0]
            t_stamp = frame_item[1]
            self.window.update_camera_view(frame_img)
            dt_rel_ms = (t_stamp - self.current_t_trigger) * 1000.0 if self.current_t_trigger > 0 else 0.0
            self.window.lbl_frame_time.setText(f"Δt = {dt_rel_ms:+.1f} ms")
            self.window.replay_lbl.setText(f"Frame {idx + 1} / {len(self.replay_frames_cache)} [REPLAY]")

    def _step_prev_replay(self):
        val = self.window.replay_slider.value()
        if val > 0:
            self.window.replay_slider.setValue(val - 1)

    def _step_next_replay(self):
        val = self.window.replay_slider.value()
        if val < self.window.replay_slider.maximum():
            self.window.replay_slider.setValue(val + 1)

    def _resume_live_feed(self):
        self.is_inspecting_replay = False
        self.window.replay_lbl.setText("Live Feed Aktif")
        self.window.lbl_frame_time.setText("LIVE")
        self.window.append_log("[VIEW] Menampilkan kembali Live Camera Stream.")

    def _on_thresh_slider_changed(self, val: int):
        thresh_pct = float(val) / 10.0  # Range 1 s/d 30 menjadi 0.1% s/d 3.0%
        self.detector.set_threshold(thresh_pct)
        self.window.lbl_thresh_val.setText(f"{thresh_pct:.1f} %")

    def run(self):
        self.camera.start()
        self.window.showMaximized()
        self.window.raise_()
        self.window.activateWindow()
        return self.app.exec()

if __name__ == "__main__":
    app = GalileoControllerApp()
    sys.exit(app.run())
