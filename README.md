# Galileo Vacuum Fall Experiment - Jatim Park Mega Science Center dan Budaya

Sistem kontrol terintegrasi dan analisis kinematika jatuh bebas (*Guinea and Feather experiment*) menggunakan kamera USB berkecepatan tinggi **OmniVision OV2710 / OV9281 (100 FPS)** dan mikrokontroler **ESP32-S3 Dual-Port** dengan mekanisme pelepasan presisi **4-Servo Dual-Stage Release Mechanism**.

Didesain khusus untuk wahana sains edukasi mutakhir oleh **Jatim Park Mega Science Center dan Budaya** bersama **Yotta Aksara Energi & Antigravity AI**.

---

## 1. Arsitektur & Prinsip Fisis

### Formula Kinematika & Propagasi Galat
Untuk lintasan jatuh bebas vertikal di dalam tabung vakum setinggi $h = 2.0\text{ m}$:
$$t_{\text{teori}} = \sqrt{\frac{2h}{g}} \approx \sqrt{\frac{4}{9.80665}} \approx 638.5\text{ ms}$$
$$g = \frac{2h}{\Delta t^2}$$

Ketidakpastian mutlak percepatan gravitasi ($\delta g$):
$$\delta g = g \sqrt{\left(\frac{\delta h}{h}\right)^2 + \left(\frac{2 \delta t}{\Delta t}\right)^2}$$

Pada frame rate **100 FPS**, resolusi waktu antar-frame kamera adalah $\Delta t = 10\text{ ms}$. ESP32 mencatat *timestamp* mikrosekon deterministik ($t_{\text{drop\_micros}}$) tepat saat pulsa pelepasan bucket dikirimkan.

### Sekuens Kinematika Pemuatan Bulu (Anti-Jamming State Machine)
Untuk mencegah benturan mekanik antara lengan pendorong (*feather dropper*) dengan sekat carousel bulu, firmware menerapkan *finite state machine* berurutan (*non-blocking*):
1. **Pendorong Maju (Ketuk):** Servo 2 menyapu cepat ke $180^\circ$ mendorong 1 helai bulu ke dalam wadah bucket.
2. **Tahan Posisi:** Ditahan selama $750\text{ ms}$ untuk memastikan bulu meluncur sempurna.
3. **Pendorong Mundur (Siaga):** Servo 2 kembali ke posisi aman $0^\circ$.
4. **Jeda Transit Mekanik:** Firmware memberi jeda settling $400\text{ ms}$ agar tuas benar-benar keluar tuntas dari jalur rotasi.
5. **Rotasi Carousel:** Servo 1 baru mulai berputar perlahan ($+18^\circ$ per slot) memajukan bulu berikutnya.

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
│   ├── physics_engine.py    # Engine perhitungan fisika, error propagation & drag model
│   └── updater.py           # Auto-synchronization & commit check
├── firmware_esp32/
│   ├── firmware_esp32.ino   # Orchestrator utama, JSON parser & Async Web Server
│   ├── config.h             # Definisi pinout, batas sudut kinematika, dan kredensial AP/STA
│   ├── actuators.h          # Header kelas ActuatorSystem & driver NativeServo (LEDC)
│   ├── actuators.cpp        # State machine, auto-return timer & kalibrasi sudut hening
│   └── webpage.h            # Antarmuka portal web captive (PROGMEM, offline-resilient)
├── web_server.py            # Backend Hybrid FastAPI untuk akses via Tablet/Mobile LAN
├── requirements.txt         # Pustaka Python yang dibutuhkan
├── version.json             # Manifest sinkronisasi versi commit
└── run_app.bat              # Launcher sekali klik Desktop GUI
```

---

## 3. Skema Wiring Hardware ESP32-S3

Sistem menggunakan board **ESP32-S3 Dev Module** (Dual Type-C: Port `COM` / UART0 CH343 dan Port `USB` / Native CDC). Seluruh servo dikendalikan secara mandiri menggunakan **Driver Native Hardware LEDC 50 Hz** (resolusi 14-bit) untuk menjamin isolasi kanal dan mencegah *cross-talk / command leakage*.

> **PERINGATAN CATU DAYA:** Jangan menyuplai 4 servo dari pin 5V board ESP32. Gunakan *power supply* switching eksternal 5V (3A–5A) khusus motor servo dengan **GND bersama (Common Ground)** ke pin GND ESP32.

| Servo | Peruntukan Fisis | GPIO ESP32-S3 | Kanal LEDC | Sudut Kerja / Kalibrasi |
| :--- | :--- | :---: | :---: | :--- |
| **Servo 1** | Carousel Stock Bulu (11 Slot) | `GPIO 5` | Channel 0 | $0^\circ \text{ s.d. } 180^\circ$ ($18^\circ$/slot, sapuan halus $25\text{ ms/deg}$) |
| **Servo 2** | Penjatuh Bulu Cepat ke Bucket | `GPIO 4` | Channel 1 | $0^\circ \text{ (siaga)} \leftrightarrow 180^\circ \text{ (ketuk, hold } 750\text{ ms)}$ |
| **Servo 3** | Pintu Stock Bola Besi (Dispenser) | `GPIO 6` | Channel 2 | $0^\circ \text{ (tutup)} \leftrightarrow 90^\circ \text{ (buka, hold } 750\text{ ms)}$ |
| **Servo 4** | Bucket Release Simultan | `GPIO 15` | Channel 3 | **$5^\circ$ (Tutup rapat hening, bebas stall)** $\leftrightarrow 90^\circ$ (Buka lepas) |
| **Status LED** | Indikator Jaringan & Boot | `GPIO 2` | Digital I/O | Berkedip saat pairing Wi-Fi / Menyala saat aktif |

### Parameter Wajib Kompilasi Arduino IDE (ESP32-S3)
Saat melakukan upload firmware melalui Arduino IDE:
* **Board:** `ESP32S3 Dev Module`
* **USB CDC On Boot:** `Disabled` *(Wajib saat kabel terhubung ke port COM/CH343)*
* **Flash Mode:** `DIO 80MHz`
* **PSRAM:** `Disabled`
* **Upload Speed:** `921600`

---

## 4. Protokol JSON Komunikasi (PC $\leftrightarrow$ ESP32)

Komunikasi beroperasi dua arah secara deterministik via **USB Serial UART (115200 Baud)** dan **WebSocket (Port 80, `/ws`)**.

### A. Perintah dari PC / GUI:
* **Muat Bulu:** `{"cmd": "DROP_FEATHER"}`
* **Muat Bola Besi:** `{"cmd": "DROP_BALL"}`
* **Rilis Simultan (Jatuh Bebas):** `{"cmd": "DROP_BOTH"}`
* **Reset Pintu Bucket:** `{"cmd": "RESET"}`
* **Putar Manual Carousel (+1 Slot):** `{"cmd": "STEP_CAROUSEL"}`
* **Reset Carousel ke Slot 1 (0°):** `{"cmd": "RESET_CAROUSEL"}`
* **Uji Sudut Tertentu (Diagnostik):** `{"cmd": "TEST_PIN", "pin": 15, "angle": 5}`
* **Heartbeat & Status Telemetri:** `{"cmd": "PING"}`

### B. Respon Deterministik dari ESP32:
```json
// Respon Pelepasan Simultan (t_drop_micros digunakan untuk sinkronisasi kamera)
{
  "event": "RELEASED",
  "target": "BOTH",
  "t_drop_micros": 45120300,
  "millis": 45120
}

// Respon Pemuatan Bulu & Posisi Carousel
{
  "event": "STAGED",
  "target": "FEATHER",
  "feather_slot": 2,
  "slot_angle": 18,
  "millis": 45890
}
```

---

## 5. Cara Menjalankan Sistem

### Persiapan Dependensi Python
```bash
cd "d:\Antigravity AI\galileo-vacuum-fall"
pip install -r requirements.txt
```

### Opsi A: Menjalankan Versi Desktop GUI (PySide6 - Rekomendasi Utama Lab)
Klik ganda berkas [**`run_app.bat`**](file:///d:/Antigravity%20AI/galileo-vacuum-fall/run_app.bat) atau jalankan via terminal:
```bash
python app/main.py
```
*(Untuk menaruh shortcut di Desktop Windows, klik ganda [**`buat_shortcut_desktop.bat`**](file:///d:/Antigravity%20AI/galileo-vacuum-fall/buat_shortcut_desktop.bat)).*

### Opsi B: Menjalankan Versi Hybrid Web Dashboard (FastAPI + HTML5)
Klik ganda berkas [**`run_web.bat`**](file:///d:/Antigravity%20AI/galileo-vacuum-fall/run_web.bat) atau jalankan:
```bash
python -m uvicorn web_server:app --host 0.0.0.0 --port 8000
```
Dashboard dapat dibuka di browser lokal `http://localhost:8000` atau dari tablet laboratorium melalui IP LAN PC pengontrol.

> **Catatan Mode Uji:** Jika kamera fisik berkecepatan tinggi OV9281 belum terhubung ke port USB, sistem secara otomatis beralih ke **Synthetic Simulation Mode (100 FPS)** lengkap dengan permodelan jatuh bebas tergenerasi, sehingga kalibrasi ROI, filter deteksi, dan kontrol aktuator dapat diuji secara mandiri tanpa kamera fisik.
