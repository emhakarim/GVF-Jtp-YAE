# Galileo Vacuum Fall Experiment - Jatim Park Mega Science Center dan Budaya

Sistem kontrol terintegrasi dan analisis kinematika jatuh bebas (*Guinea and Feather experiment*) menggunakan kamera USB berkecepatan tinggi **OmniVision OV2710 / OV9281 (100 FPS)** dan mikrokontroler **ESP32** dengan aktuator **3-Servo Release Mechanism**.

Didesain khusus untuk wahana sains edukasi oleh **Jatim Park Mega Science Center dan Budaya** bersama **Yotta Aksara Energi**.

---

## 1. Arsitektur & Prinsip Fisis

### Formula Kinematika & Propagasi Galat
Untuk lintasan jatuh bebas vertikal setinggi $h = 2.0\text{ m}$:
$$t_{\text{teori}} = \sqrt{\frac{2h}{g}} \approx \sqrt{\frac{4}{9.80665}} \approx 638.5\text{ ms}$$
$$g = \frac{2h}{\Delta t^2}$$

Ketidakpastian mutlak percepatan gravitasi ($\delta g$):
$$\delta g = g \sqrt{\left(\frac{\delta h}{h}\right)^2 + \left(\frac{2 \delta t}{\Delta t}\right)^2}$$

Pada frame rate **100 FPS**, resolusi waktu antar-frame adalah $\Delta t = 10\text{ ms}$.

---

## 2. Struktur Proyek

```text
galileo-vacuum-fall/
├── app/
│   ├── main.py              # Entry point aplikasi desktop PySide6
│   ├── ui_dashboard.py      # Antarmuka lab (Scientific Light Mode & Plot Canvas)
│   ├── camera_worker.py     # Thread akuisisi OV9281 (100 FPS) & Fallback Mock Mode
│   ├── scene_detector.py    # Algoritma Frame Differencing & Rolling Slow-Mo Buffer
│   ├── comm_manager.py      # Dual-Channel ESP32 (USB Serial UART & Wi-Fi WebSocket)
│   └── physics_engine.py    # Engine perhitungan fisika, error propagation & drag model
├── firmware_esp32/
│   ├── firmware_esp32.ino   # Firmware ESP32 aktuator 3 servo
│   └── config.h             # Pinout servo, sudut buka/tutup, dan kredensial Wi-Fi
└── requirements.txt         # Pustaka Python yang dibutuhkan
```

---

## 3. Skema Wiring Hardware ESP32

> **PERINGATAN DAYA:** Jangan menyuplai 3 servo langsung dari pin 5V/VIN ESP32. Gunakan *power supply* eksternal 5V (2A--3A) khusus servo dengan **GND bersama (Common Ground)**.

| Komponen | Pin ESP32 | Keterangan |
|---|---|---|
| **Servo 1 (Bulu)** | `GPIO 18` | Sinyal PWM (50 Hz) pemilah bulu |
| **Servo 2 (Bola Besi)** | `GPIO 19` | Sinyal PWM (50 Hz) pemilah bola logam |
| **Servo 3 (Simultan)** | `GPIO 21` | Sinyal PWM (50 Hz) pelepas kedua objek |
| **LED Indikator** | `GPIO 2` | Status koneksi Wi-Fi / boot |
| **Koneksi PC** | USB Serial / Wi-Fi | 115200 Baud (UART) atau Port 81 (WS) |

---

## 4. Protokol JSON Komunikasi (PC $\leftrightarrow$ ESP32)

### Perintah dari PC:
- Lepas Bulu: `{"cmd": "DROP_FEATHER"}`
- Lepas Bola: `{"cmd": "DROP_BALL"}`
- Lepas Simultan: `{"cmd": "DROP_BOTH"}`
- Reset Standby: `{"cmd": "RESET"}`

### Respon dari ESP32:
```json
{
  "event": "RELEASED",
  "target": "BOTH",
  "t_drop_micros": 45120300,
  "millis": 45120
}
```

---

## 5. Cara Menjalankan

### Persiapan Dependensi
```bash
cd "d:\Antigravity AI\galileo-vacuum-fall"
pip install -r requirements.txt
```

### Opsi A: Menjalankan Versi Desktop GUI (PySide6)
Klik ganda berkas [**`run_app.bat`**](file:///d:/Antigravity%20AI/galileo-vacuum-fall/run_app.bat) atau jalankan:
```bash
python app/main.py
```
*(Untuk membuat icon di desktop, klik ganda [**`buat_shortcut_desktop.bat`**](file:///d:/Antigravity%20AI/galileo-vacuum-fall/buat_shortcut_desktop.bat)).*

### Opsi B: Menjalankan Versi Hybrid Web-Based GUI (FastAPI + HTML5)
Klik ganda berkas [**`run_web.bat`**](file:///d:/Antigravity%20AI/galileo-vacuum-fall/run_web.bat) atau jalankan:
```bash
python -m uvicorn web_server:app --host 0.0.0.0 --port 8000
```
Browser akan otomatis terbuka di `http://localhost:8000`. Dashboard ini juga dapat diakses dari **tablet / HP di laboratorium** dengan membuka alamat IP laptop Anda (misal `http://192.168.1.15:8000`).


*Catatan:* Jika kamera fisik OV9281 belum tersambung ke port USB, sistem secara otomatis mengaktifkan **Synthetic Simulation Mode (100 FPS)** lengkap dengan animasi jatuh bebas sintetis, sehingga fungsi ROI, deteksi motion, kalkulasi gravitasi, dan slow-motion replay dapat diuji langsung.
