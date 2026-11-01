"""
Modul Deteksi Perubahan Scene & Analisis Gerak (100 FPS)
Menggunakan algoritma Frame Differencing berkecepatan tinggi pada ROI target,
dilengkapi Circular Rolling Buffer untuk slow-motion replay dan ekstraksi waktu tiba.
"""

from collections import deque
import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal

class SceneDetector(QObject):
    # Sinyal event deteksi
    arrival_detected = Signal(dict)          # Metadata event impak/kedatangan
    motion_level_updated = Signal(float)    # Tingkat perubahan scene saat ini (0 - 100%)
    slowmo_replay_ready = Signal(list)       # Buffer frame slow-motion (pre + post event)

    def __init__(self, buffer_size: int = 150):
        super().__init__()
        self.buffer_size = buffer_size
        self.frame_buffer = deque(maxlen=buffer_size)
        
        # Parameter ROI (Region of Interest) - Default area bawah (Full-width 100%, lower 84%)
        # Format: (x_start_ratio, y_start_ratio, width_ratio, height_ratio)
        self.roi_normalized = (0.00, 0.16, 1.00, 0.84)
        
        # Ambang batas sensitivitas deteksi (persentase piksel berubah)
        self.motion_threshold = 0.4  # Default 0.4% (sensitif terhadap bola besi ~113 px)
        
        # Band-Pass Filter Ukuran Target Fisik (Piksel)
        self.min_blob_area = 6.0     # Sensitif hingga bola sangat kecil dari kejauhan (~3 px diameter)
        self.max_blob_area = 750.0   # Memfilter dan membuang gangguan kaki/tangan/badan operator (>750 px)
        
        # Callbacks langsung untuk backend non-Qt (FastAPI Web Server)
        self.arrival_callback = None
        self.motion_callback = None
        self.slowmo_callback = None
        
        # State machine
        self.state = "IDLE"  # IDLE, ARMED, RECORDING_POST_EVENT, COMPLETED
        self.prev_gray_roi = None
        self.ref_gray_roi = None

        
        # Tracking data event saat drop
        self.armed_timestamp = 0.0
        self.drop_target_mode = "BOTH"  # FEATHER, BALL, BOTH
        self.recorded_events = []
        self.post_event_counter = 0
        self.post_event_target_frames = 40

    def set_roi(self, x_ratio: float, y_ratio: float, w_ratio: float, h_ratio: float):
        """Memperbarui zona ROI deteksi."""
        self.roi_normalized = (
            max(0.0, min(1.0, x_ratio)),
            max(0.0, min(1.0, y_ratio)),
            max(0.05, min(1.0, w_ratio)),
            max(0.05, min(1.0, h_ratio))
        )

    def set_threshold(self, threshold_percent: float):
        """Mengatur sensitivitas perubahan scene."""
        self.motion_threshold = threshold_percent

    def arm_detection(self, target_mode: str = "BOTH", t_trigger: float = 0.0):
        """Mengaktifkan pendeteksian sebelum servo melepaskan beban."""
        self.drop_target_mode = target_mode
        self.armed_timestamp = t_trigger
        self.recorded_events.clear()
        self.post_event_counter = 0
        self.ref_gray_roi = None
        self.state = "ARMED"

    def reset(self):
        """Reset state kembali ke standby."""
        self.state = "IDLE"
        self.prev_gray_roi = None
        self.ref_gray_roi = None
        self.recorded_events.clear()

    def process_frame(self, frame: np.ndarray, timestamp: float, frame_idx: int) -> np.ndarray:
        """
        Memproses frame 100 FPS, menghitung diferensial piksel pada ROI,
        dan menggambar overlay visual status deteksi.
        """
        h, w = frame.shape[:2]
        
        # Hitung koordinat piksel ROI aktual
        rx = int(self.roi_normalized[0] * w)
        ry = int(self.roi_normalized[1] * h)
        rw = int(self.roi_normalized[2] * w)
        rh = int(self.roi_normalized[3] * h)
        
        # Pastikan batas berada dalam ukuran frame
        rx = max(0, min(w - 10, rx))
        ry = max(0, min(h - 10, ry))
        rw = min(w - rx, rw)
        rh = min(h - ry, rh)

        # Simpan frame ke dalam rolling circular buffer
        self.frame_buffer.append((frame.copy(), timestamp, frame_idx))

        # Ekstraksi Region of Interest & Konversi ke Grayscale
        roi_bgr = frame[ry:ry+rh, rx:rx+rw]
        gray_roi = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        gray_roi = cv2.GaussianBlur(gray_roi, (5, 5), 0)

        motion_percent = 0.0
        max_blob_area = 0.0
        detected_blob_box = None
        
        if self.prev_gray_roi is not None and self.prev_gray_roi.shape == gray_roi.shape:
            # 1. Delta Differencing antar-frame
            delta_prev = cv2.absdiff(gray_roi, self.prev_gray_roi)
            _, thresh_prev = cv2.threshold(delta_prev, 20, 255, cv2.THRESH_BINARY)
            
            # Jika dalam mode ARMED, simpan baseline background kosong saat awal
            if self.ref_gray_roi is None:
                self.ref_gray_roi = gray_roi.copy()

            thresh_combined = thresh_prev
            if self.ref_gray_roi is not None and self.ref_gray_roi.shape == gray_roi.shape:
                delta_ref = cv2.absdiff(gray_roi, self.ref_gray_roi)
                _, thresh_ref = cv2.threshold(delta_ref, 25, 255, cv2.THRESH_BINARY)
                thresh_combined = cv2.bitwise_or(thresh_prev, thresh_ref)

            # Filter noise dengan morfologi (kernel 3x3)
            kernel = np.ones((3, 3), np.uint8)
            thresh_clean = cv2.morphologyEx(thresh_combined, cv2.MORPH_OPEN, kernel)
            
            non_zero_count = cv2.countNonZero(thresh_clean)
            total_pixels = rw * rh
            motion_percent = (non_zero_count / float(total_pixels)) * 100.0

            # Deteksi kontur dengan Band-Pass Size Filter (6 px <= Area <= 750 px)
            contours, _ = cv2.findContours(thresh_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            valid_targets = []
            for c in contours:
                area = cv2.contourArea(c)
                if self.min_blob_area <= area <= self.max_blob_area:
                    bx, by, bw, bh = cv2.boundingRect(c)
                    valid_targets.append({
                        "area": area,
                        "box": (rx + bx, ry + by, bw, bh)
                    })

            # Jika terdeteksi target bola dalam rentang fisik yang valid
            if valid_targets:
                best_target = max(valid_targets, key=lambda x: x["area"])
                max_blob_area = best_target["area"]
                detected_blob_box = best_target["box"]

            # Evaluasi Trigger saat sistem berstatus ARMED:
            # Trigger jika: terdeteksi target fisik valid (bola/bulu) ATAU persentase melampaui ambang batas tanpa gangguan makro
            has_valid_target = (max_blob_area >= self.min_blob_area)
            is_triggered = has_valid_target or (motion_percent >= self.motion_threshold and motion_percent <= 15.0)

            # Evaluasi Trigger saat sistem berstatus ARMED
            if self.state == "ARMED" and is_triggered:
                # Objek terdeteksi melintasi garis pandang kamera!
                event_data = {
                    "timestamp": timestamp,
                    "frame_idx": frame_idx,
                    "motion_level": motion_percent,
                    "blob_area": max_blob_area,
                    "target_mode": self.drop_target_mode,
                    "t_armed": self.armed_timestamp
                }
                self.recorded_events.append(event_data)
                self.state = "RECORDING_POST_EVENT"
                self.post_event_counter = 0
                    
            elif self.state == "RECORDING_POST_EVENT":
                self.post_event_counter += 1
                if self.post_event_counter >= self.post_event_target_frames:
                    # Ambil snapshot buffer untuk slow-motion replay
                    self.state = "COMPLETED"
                    buffered_frames = list(self.frame_buffer)
                    self.slowmo_replay_ready.emit(buffered_frames)
                    if self.slowmo_callback:
                        self.slowmo_callback(buffered_frames)
                    
                    if self.recorded_events:
                        self.arrival_detected.emit(self.recorded_events[0])
                        if self.arrival_callback:
                            self.arrival_callback(self.recorded_events[0])

        self.prev_gray_roi = gray_roi
        self.motion_level_updated.emit(motion_percent)
        if self.motion_callback:
            self.motion_callback(motion_percent)


        # ================= VISUAL OVERLAY PADA FRAME =================
        annotated_frame = frame.copy()
        
        # Warna ROI box: Hijau (Standby), Oranye (Armed), Merah (Impact/Detected)
        if self.state == "ARMED":
            box_color = (0, 165, 255) # Oranye
            status_text = "STATUS: ARMED - MENUNGGU BENDA JATUH"
        elif self.state in ["RECORDING_POST_EVENT", "COMPLETED"]:
            box_color = (0, 0, 255)   # Merah terang
            status_text = "STATUS: IMPACT TERDETEKSI!"
        else:
            box_color = (0, 200, 0)   # Hijau
            status_text = "STATUS: STANDBY"

        # Gambar kotak ROI dan garis bidik
        cv2.rectangle(annotated_frame, (rx, ry), (rx + rw, ry + rh), box_color, 2)
        cv2.line(annotated_frame, (rx, ry + rh // 2), (rx + rw, ry + rh // 2), box_color, 1)

        # Gambar bounding box blob target fisik yang terdeteksi (bola / bulu)
        if detected_blob_box is not None and max_blob_area >= self.min_blob_area:
            bx, by, bw, bh = detected_blob_box
            cv2.rectangle(annotated_frame, (bx, by), (bx + bw, by + bh), (0, 255, 255), 2)
            cv2.putText(annotated_frame, f"TARGET BOLA {int(max_blob_area)}px", (bx, max(15, by - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)

        # Header telemetri visual
        cv2.putText(annotated_frame, f"ROI MOTION: {motion_percent:.1f}% (BLOB: {int(max_blob_area)}px | TH: {self.motion_threshold:.1f}%)", 
                    (rx + 10, max(25, ry - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, box_color, 2)
        cv2.putText(annotated_frame, status_text, (20, h - 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, box_color, 2)

        return annotated_frame
