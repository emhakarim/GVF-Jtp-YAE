"""
Worker Thread Akuisisi Video Kamera OV9281 (100 FPS)
Arsitektur Zero-Bottleneck:
- Pemrosesan Scene Detector dieksekusi di background thread pada 100 FPS penuh (10 ms).
- Emisi tampilan GUI disub-sampling secara cerdas ke ~40 FPS untuk mencegah penumpukan event queue di GUI thread.
- Canvas sintetis di-preallocate di memori (zero heap thrashing).
"""

import time
import numpy as np
import cv2
from PySide6.QtCore import QThread, Signal

class CameraWorker(QThread):
    # Sinyal tampilan GUI (sub-sampled ke 40 FPS agar GUI responsif 100%)
    display_frame_ready = Signal(np.ndarray)
    fps_updated = Signal(float)
    camera_status = Signal(bool, str)

    @staticmethod
    def list_available_cameras():
        """Mendeteksi daftar perangkat video yang tersedia menggunakan QMediaDevices."""
        camera_list = []
        try:
            from PySide6.QtMultimedia import QMediaDevices
            devices = QMediaDevices.videoInputs()
            for idx, dev in enumerate(devices):
                desc = dev.description()
                camera_list.append((idx, f"Cam {idx}: {desc}"))
        except Exception:
            for i in range(3):
                test_cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if test_cap.isOpened():
                    camera_list.append((i, f"Kamera Port {i}"))
                    test_cap.release()

        # Opsi Simulasi Sintetis
        camera_list.append((-1, "Mode Simulasi Lab (Mock 120 FPS)"))
        return camera_list

    def __init__(self, camera_index: int = 0, target_fps: int = 120, width: int = 640, height: int = 480, detector=None):
        super().__init__()
        self.camera_index = camera_index
        self.target_fps = target_fps
        self.width = width
        self.height = height
        self.detector = detector  # Referensi scene detector untuk pemrosesan di background thread
        
        # Callbacks langsung untuk backend tanpa Qt event loop (FastAPI Web Server)
        self.display_callback = None
        self.fps_callback = None
        self.status_callback = None

        self.running = False
        self.is_mock = (camera_index < 0)
        self.frame_count = 0
        self.cap = None
        self._switch_requested = False
        self._new_camera_index = camera_index
        
        # Variabel simulasi jatuh sintetis (Mock Mode)
        self.sim_dropping = False
        self.sim_drop_start_time = 0.0
        self.sim_target_type = "BOTH"

        # Pre-allocate kanvas statis sintetis sekali saja di memori
        self._init_static_mock_canvas()

    def _init_static_mock_canvas(self):
        """Membuat template kanvas statis sekali saja untuk efisiensi RAM & CPU."""
        h, w = self.height, self.width
        base = np.full((h, w), 242, dtype=np.uint8)

        # Garis grid optik kalibrasi
        for y in range(0, h, 50):
            base[y:y+1, :] = 215
        for x in range(0, w, 80):
            base[:, x:x+1] = 215

        # Dinding silinder tabung vakum
        tube_left = w // 2 - 80
        tube_right = w // 2 + 80
        base[:, tube_left:tube_left+2] = 80
        base[:, tube_right:tube_right+2] = 80

        cv2.putText(base, "HIGH-SPEED SYNTHETIC STREAM [120 FPS]", (20, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, 50, 2)

        self.static_mock_canvas = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)

    def set_detector(self, detector):
        self.detector = detector

    def switch_camera(self, new_index: int):
        """Meminta pergantian kamera secara asinkron tanpa memblokir thread pemanggil."""
        self._new_camera_index = new_index
        self._switch_requested = True

    def _open_camera(self, index: int):
        if self.cap is not None:
            try:
                self.cap.release()
                time.sleep(0.15)  # Berikan waktu bagi driver DirectShow Windows unbind
            except Exception:
                pass
            self.cap = None

        if index < 0:
            self.is_mock = True
            self.camera_index = -1
            msg = "Mode Simulasi Lab Aktif (120 FPS Sintetis)"
            self.camera_status.emit(False, msg)
            if self.status_callback: self.status_callback(False, msg)
            return

        try:
            # Buka perangkat video
            self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if not self.cap or not self.cap.isOpened():
                self.cap = cv2.VideoCapture(index)

            if not self.cap or not self.cap.isOpened():
                raise RuntimeError(f"Port {index} tidak dapat dibuka.")

            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # High-Speed Adaptive Ladder (120 FPS Native OV2710 -> 100 FPS OV9281 -> 60 FPS -> 30 FPS)
            negotiated = False
            test_frame = None
            for fps_candidate in [120, 100, 60, 30]:
                self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, fps_candidate)

                for _ in range(3):
                    ret, test_frame = self.cap.read()
                    if ret and test_frame is not None:
                        negotiated = True
                        self.target_fps = fps_candidate
                        break
                if negotiated:
                    break

            if not negotiated:
                # Fallback untuk perangkat yang menolak parameter high-speed (misal webcam laptop default)
                self.cap.release()
                time.sleep(0.15)
                self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                if not self.cap or not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(index)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                ret, test_frame = self.cap.read()
                self.target_fps = 30

            if test_frame is not None:
                ch_h, ch_w = test_frame.shape[:2]
                self.is_mock = False
                self.camera_index = index
                msg = f"Kamera Port {index} Aktif ({ch_w}x{ch_h} @ {self.target_fps} FPS)"
                self.camera_status.emit(True, msg)
                if self.status_callback: self.status_callback(True, msg)
            else:
                raise RuntimeError("Kamera tidak menghasilkan frame video.")
        except Exception as e:
            self.is_mock = True
            self.camera_index = -1
            msg = f"Gagal buka port {index} ({e}). Menggunakan mode simulasi."
            self.camera_status.emit(False, msg)
            if self.status_callback: self.status_callback(False, msg)

    def run(self):
        self.running = True
        self._open_camera(self.camera_index)

        fps_timer = time.perf_counter()
        fps_frames = 0
        frame_interval = 1.0 / self.target_fps  # 10 ms
        last_display_emit_time = 0.0

        while self.running:
            # Handle pergantian kamera jika diminta
            if self._switch_requested:
                self._switch_requested = False
                self._open_camera(self._new_camera_index)

            loop_start = time.perf_counter()
            
            if not self.is_mock and self.cap and self.cap.isOpened():
                ret, raw_frame = self.cap.read()
                if not ret or raw_frame is None:
                    time.sleep(0.005)
                    continue
            else:
                raw_frame = self._render_synthetic_frame()

            t_now = time.perf_counter()
            self.frame_count += 1
            fps_frames += 1

            # 1. PROSES DETEKSI PADA SETIAP FRAME (Di Background Thread, 0% Beban GUI)
            annotated_frame = raw_frame
            if self.detector is not None:
                annotated_frame = self.detector.process_frame(raw_frame, t_now, self.frame_count)

            # 2. EMISI TAMPILAN KE GUI & WEB
            # Untuk frame rate <= 50 FPS langsung emit, untuk 100 FPS sub-sample ke ~40 FPS
            if self.is_mock or (t_now - last_display_emit_time) >= 0.020:
                self.display_frame_ready.emit(annotated_frame)
                if self.display_callback:
                    self.display_callback(annotated_frame)
                last_display_emit_time = t_now

            # 3. Hitung rolling FPS aktual
            if t_now - fps_timer >= 1.0:
                calc_fps = fps_frames / (t_now - fps_timer)
                self.fps_updated.emit(calc_fps)
                if self.fps_callback:
                    self.fps_callback(calc_fps)
                fps_frames = 0
                fps_timer = t_now


            # 4. Pengatur waktu interval 10 ms (High-Precision Sleep)
            if self.is_mock:
                elapsed = time.perf_counter() - loop_start
                sleep_sec = frame_interval - elapsed
                if sleep_sec > 0.001:
                    time.sleep(sleep_sec)

        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass

    def stop(self):
        self.running = False
        self.wait()

    def trigger_mock_drop(self, target_type: str = "BOTH"):
        """Memicu animasi jatuh sintetis pada mock mode."""
        self.sim_dropping = True
        self.sim_drop_start_time = time.perf_counter()
        self.sim_target_type = target_type

    def _render_synthetic_frame(self) -> np.ndarray:
        """Merender objek jatuh di atas kanvas template (sangat cepat, < 0.2 ms)."""
        frame = self.static_mock_canvas.copy()
        h, w = self.height, self.width

        if self.sim_dropping:
            dt = time.perf_counter() - self.sim_drop_start_time
            # Jarak jatuh: y = 50 + 0.5 * 1800 * t^2
            y_pos = int(50 + 0.5 * 1800 * (dt ** 2))
            
            if y_pos < h + 100:
                if self.sim_target_type in ["BALL", "BOTH"]:
                    cv2.circle(frame, (w // 2 - 40, y_pos), 18, (30, 30, 30), -1)
                
                if self.sim_target_type in ["FEATHER", "BOTH"]:
                    cv2.ellipse(frame, (w // 2 + 40, y_pos), (8, 25), 20, 0, 360, (120, 120, 120), -1)
            else:
                self.sim_dropping = False

        return frame
