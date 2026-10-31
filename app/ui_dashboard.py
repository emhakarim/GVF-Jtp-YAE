"""
Antarmuka Grafis Desktop (PySide6) Galileo Vacuum Fall Experiment
Jatim Park Mega Science Center dan Budaya
Engineered by Yotta Aksara Energi

Arsitektur Tampilan:
- ID-Scoped CSS untuk mencegah kebocoran styling (No Qt CSS inheritance bugs).
- Zero text-clipping: Dimensi dan ukuran font terkalibrasi presisi dengan layout otomatis.
- Tombol dengan kontras tinggi yang jelas dan terbaca.
- Telemetri dominan dan tajam ala instrumen lab modern.
"""

import sys
import os
import numpy as np
import cv2
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QLineEdit, QSlider, QGroupBox,
    QTextEdit, QFrame, QSplitter
)
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QImage, QPixmap, QFont

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Stylesheet Global Terpadu dengan ID-Scoping Ketat (Mencegah Bug Inheritansi Qt)
APP_STYLE = """
/* Dasar Jendela */
QMainWindow {
    background-color: #f1f5f9;
}
QWidget {
    font-family: 'Segoe UI', 'Plus Jakarta Sans', 'Inter', sans-serif;
    color: #0f172a;
}

/* Header Terpadu Ramping */
#topUnifiedBar {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 6px 14px;
}
#topUnifiedBar QLabel {
    color: #334155;
}

/* Strip Kontrol Hardware di Tengah */
#controlStrip {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 3px 10px;
}
#controlStrip QLabel {
    font-weight: 700;
    font-size: 11px;
    color: #475569;
    background: transparent;
    border: none;
}
#controlStrip QComboBox {
    background-color: #ffffff;
    border: 1px solid #94a3b8;
    border-radius: 5px;
    padding: 4px 8px;
    font-size: 11px;
    color: #0f172a;
    font-weight: 600;
}
#controlStrip QPushButton {
    background-color: #0284c7;
    color: #ffffff;
    font-weight: 700;
    font-size: 11px;
    border: 1px solid #0369a1;
    border-radius: 5px;
    padding: 5px 12px;
}
#controlStrip QPushButton:hover {
    background-color: #0369a1;
}
#btnUpdate {
    background-color: #ffffff;
    color: #0284c7;
    font-weight: 700;
    font-size: 11px;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 5px 10px;
}
#btnUpdate:hover {
    background-color: #e0f2fe;
    border-color: #7dd3fc;
}
#btnFullscreen {
    background-color: #0f172a;
    color: #f8fafc;
    font-weight: 700;
    font-size: 11px;
    border: 1px solid #334155;
    border-radius: 5px;
    padding: 5px 14px;
}
#btnFullscreen:hover {
    background-color: #1e293b;
    border-color: #475569;
}

/* Badges Status Kompak */
#badgeStatus, #pillStatusStandby {
    background-color: #e0f2fe;
    color: #0369a1;
    font-weight: 800;
    font-size: 10px;
    padding: 4px 10px;
    border-radius: 14px;
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    border: 1px solid #bae6fd;
}
#badgeFps, #pillStatusFps {
    background-color: #dcfce7;
    color: #15803d;
    font-weight: 800;
    font-size: 10px;
    padding: 4px 10px;
    border-radius: 14px;
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    border: 1px solid #bbf7d0;
}

/* Panel Kontrol Aktuator */
#groupActuators {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    margin-top: 2px;
}
#groupActuators QLabel {
    border: none;
    background: transparent;
}
QPushButton#btnDropBoth {
    background-color: #16a34a;
    color: #ffffff;
    font-size: 12px;
    font-weight: 800;
    border: 1px solid #15803d;
    border-radius: 6px;
    padding: 9px 14px;
    letter-spacing: 0.3px;
}
QPushButton#btnDropBoth:hover {
    background-color: #15803d;
}
QPushButton#btnDropBoth:pressed {
    background-color: #166534;
}
QPushButton#btnDropFeather {
    background-color: #ea580c;
    color: #ffffff;
    font-size: 11px;
    font-weight: 700;
    border: 1px solid #c2410c;
    border-radius: 6px;
    padding: 7px 10px;
}
QPushButton#btnDropFeather:hover {
    background-color: #c2410c;
}
QPushButton#btnDropBall {
    background-color: #334155;
    color: #ffffff;
    font-size: 11px;
    font-weight: 700;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 7px 10px;
}
QPushButton#btnDropBall:hover {
    background-color: #1e293b;
}
QPushButton#btnReset {
    background-color: #fee2e2;
    color: #b91c1c;
    font-size: 11px;
    font-weight: 700;
    border: 1px solid #fecaca;
    border-radius: 6px;
    padding: 7px 10px;
}
QPushButton#btnReset:hover {
    background-color: #fca5a5;
}

/* Hero Cards Telemetri */
#cardGravity {
    background-color: #ecfdf5;
    border: 2px solid #34d399;
    border-radius: 8px;
}
#cardGravity QLabel {
    border: none;
    background: transparent;
}
#valGravity {
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-size: 28px;
    font-weight: 900;
    color: #065f46;
}

#cardTime {
    background-color: #fff7ed;
    border: 2px solid #fb923c;
    border-radius: 8px;
}
#cardTime QLabel {
    border: none;
    background: transparent;
}
#valTime {
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-size: 28px;
    font-weight: 900;
    color: #9a3412;
}

#cardVelocity {
    background-color: #f0f9ff;
    border: 1px solid #7dd3fc;
    border-radius: 6px;
}
#cardVelocity QLabel {
    border: none;
    background: transparent;
}
#cardDev {
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
}
#cardDev QLabel {
    border: none;
    background: transparent;
}

/* Dock Bawah */
#dockBottom {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
}
#dockBottom QLabel {
    border: none;
    background: transparent;
}
#dockBottom QPushButton {
    background-color: #f1f5f9;
    color: #1e293b;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    font-weight: 700;
    font-size: 11px;
    padding: 5px 12px;
}
#dockBottom QPushButton:hover {
    background-color: #e2e8f0;
}
#dockBottom QPushButton:disabled {
    color: #94a3b8;
    background-color: #f8fafc;
    border-color: #e2e8f0;
}

/* Terminal Log */
#termLog {
    background-color: #090d16;
    color: #38bdf8;
    font-family: 'Consolas', 'JetBrains Mono', monospace;
    font-size: 11px;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 6px;
}
"""

class FastMotionPlot(FigureCanvas):
    """Plot Canvas Ringan & Non-blocking."""
    def __init__(self, parent=None, width=4, height=1.3, dpi=90):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor('#ffffff')
        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor('#f8fafc')
        self.axes.grid(True, linestyle='--', alpha=0.5, color='#cbd5e1')
        self.axes.set_ylim(0, 100)
        self.axes.set_xlim(0, 100)
        self.axes.tick_params(labelsize=8)
        self.fig.subplots_adjust(left=0.10, right=0.96, top=0.86, bottom=0.24)
        
        self.line, = self.axes.plot([], [], color='#0284c7', linewidth=1.5)
        self.axes.set_title("INTENSITAS PERUBAHAN SCENE ROI (%)", fontsize=8, fontweight='bold', color='#475569')

        super().__init__(self.fig)
        self.data_buffer = []
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._render_plot)
        self.timer.start(100)  # 10 Hz refresh

    def push_data_point(self, val: float):
        self.data_buffer.append(val)
        if len(self.data_buffer) > 100:
            self.data_buffer.pop(0)

    def _render_plot(self):
        if not self.data_buffer:
            return
        y = self.data_buffer
        x = list(range(len(y)))
        self.line.set_data(x, y)
        self.axes.set_xlim(0, max(100, len(y)))
        self.draw_idle()


class DashboardWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Galileo Vacuum Fall Experiment - Jatim Park Mega Science Center dan Budaya")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 640)
        self.setStyleSheet(APP_STYLE)

        self._build_interface()

    def _build_interface(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(12, 8, 12, 8)
        root_layout.setSpacing(6)

        # 1. HEADER TERPADU KOMPAK (ZERO EXCESS WHITE SPACE)
        header_card = QFrame()
        header_card.setObjectName("topUnifiedBar")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(10, 6, 12, 6)
        h_layout.setSpacing(14)

        # Kiri: Logo Jawa Timur Park Group
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assets_dir = os.path.join(base_dir, "assets")

        logo_jtp_path = os.path.join(self.assets_dir, "logo_jtp.png")
        if os.path.exists(logo_jtp_path):
            lbl_jtp = QLabel()
            pix_jtp = QPixmap(logo_jtp_path)
            lbl_jtp.setPixmap(pix_jtp.scaledToHeight(52, Qt.SmoothTransformation))
            h_layout.addWidget(lbl_jtp, alignment=Qt.AlignVCenter)

        # Divider Kiri
        d_left = QFrame()
        d_left.setFrameShape(QFrame.VLine)
        d_left.setStyleSheet("color: #cbd5e1; max-height: 52px;")
        h_layout.addWidget(d_left, alignment=Qt.AlignVCenter)

        # TENGAH: Judul, Badges & Kontrol Terkumpul Terpusat
        center_col = QVBoxLayout()
        center_col.setSpacing(4)
        center_col.setAlignment(Qt.AlignCenter)

        # Baris 1 Tengah: Judul & Badges
        c_top = QHBoxLayout()
        c_top.setSpacing(12)
        c_top.setAlignment(Qt.AlignCenter)

        title_inner = QVBoxLayout()
        title_inner.setSpacing(1)
        t1 = QLabel("GALILEO VACUUM FALL EXPERIMENT")
        t1.setStyleSheet("font-size: 17px; font-weight: 800; color: #0f172a; letter-spacing: -0.01em;")
        t2 = QLabel("Wahana Fisika & Kinematika Vakum (100 FPS) • Yotta Aksara Energi")
        t2.setStyleSheet("font-size: 11px; font-weight: 600; color: #475569;")
        title_inner.addWidget(t1)
        title_inner.addWidget(t2)
        c_top.addLayout(title_inner)

        c_top.addSpacing(10)
        self.badge_status = QLabel("● ESP32: STANDBY")
        self.badge_status.setObjectName("pillStatusStandby")
        c_top.addWidget(self.badge_status)

        self.fps_badge = QLabel("● CAM: 100 FPS")
        self.fps_badge.setObjectName("pillStatusFps")
        c_top.addWidget(self.fps_badge)

        center_col.addLayout(c_top)

        # Baris 2 Tengah: Strip Kontrol Hardware Ringkas
        c_bot = QFrame()
        c_bot.setObjectName("controlStrip")
        c_bot_l = QHBoxLayout(c_bot)
        c_bot_l.setContentsMargins(8, 3, 8, 3)
        c_bot_l.setSpacing(8)
        c_bot_l.setAlignment(Qt.AlignCenter)

        c_bot_l.addWidget(QLabel("📹 Kamera:"))
        self.combo_cameras = QComboBox()
        self.combo_cameras.setMinimumWidth(210)
        c_bot_l.addWidget(self.combo_cameras)

        self.btn_refresh_cameras = QPushButton("Scan")
        c_bot_l.addWidget(self.btn_refresh_cameras)

        d_mid = QFrame()
        d_mid.setFrameShape(QFrame.VLine)
        d_mid.setStyleSheet("color: #cbd5e1; max-height: 18px;")
        c_bot_l.addWidget(d_mid)

        c_bot_l.addWidget(QLabel("⚡ ESP32:"))
        self.combo_ports = QComboBox()
        self.combo_ports.setMinimumWidth(160)
        c_bot_l.addWidget(self.combo_ports)

        self.btn_connect_serial = QPushButton("Hubungkan")
        c_bot_l.addWidget(self.btn_connect_serial)

        d_mid2 = QFrame()
        d_mid2.setFrameShape(QFrame.VLine)
        d_mid2.setStyleSheet("color: #cbd5e1; max-height: 18px;")
        c_bot_l.addWidget(d_mid2)

        self.btn_update = QPushButton("🔄 Update")
        self.btn_update.setObjectName("btnUpdate")
        self.btn_update.setToolTip("Periksa dan Sinkronkan Pembaruan dari GitHub")
        c_bot_l.addWidget(self.btn_update)

        self.btn_fullscreen = QPushButton("⛶ Layar Penuh (F11)")
        self.btn_fullscreen.setObjectName("btnFullscreen")
        self.btn_fullscreen.setToolTip("Alihkan Tampilan Layar Penuh (F11 / Esc)")
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        c_bot_l.addWidget(self.btn_fullscreen)

        center_col.addWidget(c_bot)
        h_layout.addLayout(center_col, stretch=1)

        # Divider Kanan
        d_right = QFrame()
        d_right.setFrameShape(QFrame.VLine)
        d_right.setStyleSheet("color: #cbd5e1; max-height: 52px;")
        h_layout.addWidget(d_right, alignment=Qt.AlignVCenter)

        # Kanan: Logo Museum Mega Science Center (Besar: 74px)
        logo_sc_clean = os.path.join(self.assets_dir, "logo_science_center_clean.png")
        if os.path.exists(logo_sc_clean):
            lbl_sc = QLabel()
            pix_sc = QPixmap(logo_sc_clean)
            lbl_sc.setPixmap(pix_sc.scaledToHeight(74, Qt.SmoothTransformation))
            h_layout.addWidget(lbl_sc, alignment=Qt.AlignVCenter)

        root_layout.addWidget(header_card)

        # 2. SPLITTER AREA UTAMA (KIRI & KANAN)
        splitter = QSplitter(Qt.Horizontal)

        # ================= KIRI: VIDEO & DOCK KONTROL =================
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        # Video Viewport
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #090d16; border-radius: 8px; border: 1px solid #1e293b;")
        self.video_label.setMinimumSize(700, 560)
        left_layout.addWidget(self.video_label, stretch=5)

        # Compact Dock Bawah (Slow-Mo & Sensitivitas ROI Berdampingan)
        dock = QFrame()
        dock.setObjectName("dockBottom")
        dock_layout = QHBoxLayout(dock)
        dock_layout.setContentsMargins(14, 8, 14, 8)
        dock_layout.setSpacing(16)

        # Kolom Slow-Mo
        sm_box = QVBoxLayout()
        sm_top = QHBoxLayout()
        l_sm = QLabel("INSPEKSI SLOW-MOTION (100 FPS)")
        l_sm.setStyleSheet("font-size: 11px; font-weight: 800; color: #334155;")
        self.replay_lbl = QLabel("Standby (0 Frame)")
        self.replay_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #0284c7; font-family: monospace;")
        sm_top.addWidget(l_sm)
        sm_top.addStretch()
        sm_top.addWidget(self.replay_lbl)
        sm_box.addLayout(sm_top)

        self.replay_slider = QSlider(Qt.Horizontal)
        self.replay_slider.setEnabled(False)
        sm_box.addWidget(self.replay_slider)

        sm_nav = QHBoxLayout()
        self.btn_step_prev = QPushButton("◀ -10 ms")
        self.btn_step_prev.setEnabled(False)
        self.btn_step_next = QPushButton("+10 ms ▶")
        self.btn_step_next.setEnabled(False)
        self.lbl_frame_time = QLabel("Δt = 0.0 ms")
        self.lbl_frame_time.setStyleSheet("font-size: 11px; font-family: monospace; color: #0284c7; font-weight: 700;")
        self.btn_live_feed = QPushButton("🔴 Live Camera")
        self.btn_live_feed.setStyleSheet("background-color: #fee2e2; color: #b91c1c; font-weight: 700; border: 1px solid #fecaca; padding: 4px 10px; border-radius: 5px; font-size: 11px;")
        sm_nav.addWidget(self.btn_step_prev)
        sm_nav.addWidget(self.lbl_frame_time)
        sm_nav.addWidget(self.btn_step_next)
        sm_nav.addStretch()
        sm_nav.addWidget(self.btn_live_feed)
        sm_box.addLayout(sm_nav)
        dock_layout.addLayout(sm_box, stretch=3)

        # Divider
        d_dock = QFrame()
        d_dock.setFrameShape(QFrame.VLine)
        d_dock.setStyleSheet("color: #cbd5e1;")
        dock_layout.addWidget(d_dock)

        # Kolom Sensitivitas ROI
        roi_box = QVBoxLayout()
        roi_top = QHBoxLayout()
        l_roi = QLabel("SENSITIVITAS DETEKSI ROI")
        l_roi.setStyleSheet("font-size: 11px; font-weight: 800; color: #334155;")
        self.lbl_thresh_val = QLabel("0.4 %")
        self.lbl_thresh_val.setStyleSheet("font-size: 11px; font-weight: 700; color: #ea580c; font-family: monospace;")
        roi_top.addWidget(l_roi)
        roi_top.addStretch()
        roi_top.addWidget(self.lbl_thresh_val)
        roi_box.addLayout(roi_top)

        self.slider_thresh = QSlider(Qt.Horizontal)
        self.slider_thresh.setRange(1, 30) # 0.1% s/d 3.0%
        self.slider_thresh.setValue(4)     # Default 0.4%
        roi_box.addWidget(self.slider_thresh)

        l_sub = QLabel("Ambang perubahan piksel (0.1% - 3.0%)")
        l_sub.setStyleSheet("font-size: 10px; color: #94a3b8;")
        roi_box.addWidget(l_sub)
        dock_layout.addLayout(roi_box, stretch=2)

        left_layout.addWidget(dock, stretch=1)
        splitter.addWidget(left_container)

        # ================= KANAN: AKTATOR & TELEMETRI =================
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # 1. Panel Kendali Aktuator
        p_act = QFrame()
        p_act.setObjectName("groupActuators")
        act_layout = QVBoxLayout(p_act)
        act_layout.setContentsMargins(12, 10, 12, 10)
        act_layout.setSpacing(8)

        l_act_title = QLabel("KENDALI PELEPASAN AKTATOR (3 SERVO)")
        l_act_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #475569; letter-spacing: 0.5px;")
        act_layout.addWidget(l_act_title)

        self.btn_drop_both = QPushButton("LEPAS KEDUANYA SIMULTAN (SERVO 3)")
        self.btn_drop_both.setObjectName("btnDropBoth")
        act_layout.addWidget(self.btn_drop_both)

        indiv_row = QHBoxLayout()
        self.btn_drop_feather = QPushButton("Lepas Bulu (Servo 1)")
        self.btn_drop_feather.setObjectName("btnDropFeather")
        self.btn_drop_ball = QPushButton("Lepas Bola Besi (Servo 2)")
        self.btn_drop_ball.setObjectName("btnDropBall")
        indiv_row.addWidget(self.btn_drop_feather)
        indiv_row.addWidget(self.btn_drop_ball)
        act_layout.addLayout(indiv_row)

        self.btn_reset = QPushButton("Reset Posisi Aktuator (Standby)")
        self.btn_reset.setObjectName("btnReset")
        act_layout.addWidget(self.btn_reset)
        right_layout.addWidget(p_act)

        # 2. Telemetri Kinematika & Gravitasi (Hero Highlight Cards)
        p_tele = QFrame()
        p_tele.setObjectName("groupActuators")
        tele_layout = QVBoxLayout(p_tele)
        tele_layout.setContentsMargins(12, 10, 12, 10)
        tele_layout.setSpacing(8)

        l_tele_title = QLabel("TELEMETRI KINEMATIKA & GRAVITASI (h = 2.000 m)")
        l_tele_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #475569; letter-spacing: 0.5px;")
        tele_layout.addWidget(l_tele_title)

        # Card 1: Gravitasi Estimasi g
        cg = QFrame()
        cg.setObjectName("cardGravity")
        cg_l = QVBoxLayout(cg)
        cg_l.setContentsMargins(12, 8, 12, 8)
        cg_l.setSpacing(2)

        lbl_cg_t = QLabel("PERCEPATAN GRAVITASI ESTIMASI (g)")
        lbl_cg_t.setStyleSheet("font-size: 10px; font-weight: 800; color: #047857; letter-spacing: 0.5px;")
        cg_l.addWidget(lbl_cg_t)

        cg_row = QHBoxLayout()
        self.val_g = QLabel("0.000")
        self.val_g.setObjectName("valGravity")
        lbl_cg_u = QLabel("m/s²")
        lbl_cg_u.setStyleSheet("font-size: 16px; font-weight: 800; color: #047857; margin-top: 10px;")
        cg_row.addWidget(self.val_g)
        cg_row.addWidget(lbl_cg_u)
        cg_row.addStretch()
        cg_l.addLayout(cg_row)

        self.val_g_err = QLabel("Toleransi Galat: ± 0.00 m/s²")
        self.val_g_err.setStyleSheet("font-size: 11px; font-weight: 700; color: #059669; font-family: monospace;")
        cg_l.addWidget(self.val_g_err)
        tele_layout.addWidget(cg)

        # Card 2: Waktu Jatuh dt
        ct = QFrame()
        ct.setObjectName("cardTime")
        ct_l = QVBoxLayout(ct)
        ct_l.setContentsMargins(12, 8, 12, 8)
        ct_l.setSpacing(2)

        lbl_ct_t = QLabel("WAKTU JATUH TERUKUR (dt)")
        lbl_ct_t.setStyleSheet("font-size: 10px; font-weight: 800; color: #c2410c; letter-spacing: 0.5px;")
        ct_l.addWidget(lbl_ct_t)

        ct_row = QHBoxLayout()
        self.val_dt = QLabel("0.0")
        self.val_dt.setObjectName("valTime")
        lbl_ct_u = QLabel("ms")
        lbl_ct_u.setStyleSheet("font-size: 16px; font-weight: 800; color: #c2410c; margin-top: 10px;")
        ct_row.addWidget(self.val_dt)
        ct_row.addWidget(lbl_ct_u)
        ct_row.addStretch()
        ct_l.addLayout(ct_row)

        self.lbl_dt_theo = QLabel("Nilai Teoritis Vakum: 638.5 ms")
        self.lbl_dt_theo.setStyleSheet("font-size: 11px; font-weight: 700; color: #ea580c; font-family: monospace;")
        ct_l.addWidget(self.lbl_dt_theo)
        tele_layout.addWidget(ct)

        # Sub-Card: Kecepatan & Deviasi
        sub_grid = QGridLayout()
        sub_grid.setSpacing(8)

        cv = QFrame()
        cv.setObjectName("cardVelocity")
        cv_l = QVBoxLayout(cv)
        cv_l.setContentsMargins(10, 6, 10, 6)
        l_cv_t = QLabel("KECEPATAN AKHIR (v)")
        l_cv_t.setStyleSheet("font-size: 10px; font-weight: 700; color: #0369a1;")
        self.val_v = QLabel("0.00 m/s")
        self.val_v.setStyleSheet("font-family: monospace; font-size: 17px; font-weight: 900; color: #0284c7;")
        cv_l.addWidget(l_cv_t)
        cv_l.addWidget(self.val_v)
        sub_grid.addWidget(cv, 0, 0)

        cdev = QFrame()
        cdev.setObjectName("cardDev")
        cdev_l = QVBoxLayout(cdev)
        cdev_l.setContentsMargins(10, 6, 10, 6)
        l_cd_t = QLabel("DEVIASI thd 9.807")
        l_cd_t.setStyleSheet("font-size: 10px; font-weight: 700; color: #475569;")
        self.val_dev = QLabel("0.00 %")
        self.val_dev.setStyleSheet("font-family: monospace; font-size: 17px; font-weight: 900; color: #334155;")
        cdev_l.addWidget(l_cd_t)
        cdev_l.addWidget(self.val_dev)
        sub_grid.addWidget(cdev, 0, 1)

        tele_layout.addLayout(sub_grid)
        right_layout.addWidget(p_tele)

        # 3. Canvas Plot Profil Gerak
        self.plot_canvas = FastMotionPlot(self)
        right_layout.addWidget(self.plot_canvas)

        # 4. Terminal Log
        self.log_console = QTextEdit()
        self.log_console.setObjectName("termLog")
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(85)
        right_layout.addWidget(self.log_console)

        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        root_layout.addWidget(splitter)

    @Slot(np.ndarray)
    def update_camera_view(self, cv_frame: np.ndarray):
        """Merender frame OpenCV ke format QPixmap PySide6."""
        h, w, ch = cv_frame.shape
        bytes_per_line = ch * w
        rgb_frame = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
        qt_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pix = QPixmap.fromImage(qt_img)
        self.video_label.setPixmap(pix.scaled(
            self.video_label.size(), Qt.KeepAspectRatio, Qt.FastTransformation
        ))

    def append_log(self, text: str):
        self.log_console.append(text)
        self.log_console.verticalScrollBar().setValue(
            self.log_console.verticalScrollBar().maximum()
        )

    def toggle_fullscreen(self):
        """Alihkan mode tampilan layar penuh (Fullscreen) untuk kiosk/touch monitor."""
        if self.isFullScreen():
            self.showNormal()
            self.showMaximized()
            self.btn_fullscreen.setText("⛶ Layar Penuh (F11)")
        else:
            self.showFullScreen()
            self.btn_fullscreen.setText("❐ Keluar Layar Penuh (Esc)")

    def keyPressEvent(self, event):
        """Shortcut keyboard F11 dan Escape untuk navigasi layar penuh."""
        if event.key() == Qt.Key_F11:
            self.toggle_fullscreen()
            event.accept()
        elif event.key() == Qt.Key_Escape and self.isFullScreen():
            self.toggle_fullscreen()
            event.accept()
        else:
            super().keyPressEvent(event)
