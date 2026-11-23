# Galileo Vacuum Fall Experiment - Jatim Park Mega Science Center dan Budaya

Sistem kontrol terintegrasi dan analisis kinematika jatuh bebas (*Guinea and Feather experiment*) menggunakan kamera USB berkecepatan tinggi **OmniVision OV2710 / OV9281 (100 FPS)** dan mikrokontroler **ESP32-S3 Dual-Port** dengan mekanisme pelepasan presisi **4-Servo Dual-Stage Release Mechanism**.

Didesain khusus untuk wahana sains edukasi mutakhir oleh **Jatim Park Mega Science Center dan Budaya** bersama **Yotta Aksara Energi & Antigravity AI**.

---

## 🤖 Petunjuk Khusus AI Agent & Autonomous Assistant

> **UNTUK AGENTIC AI (Antigravity, Claude Code, Cursor, Copilot, Windsurf, dll):**
> Jika Anda menerima instruksi untuk mengkloning, memasang (*install*), mengaudit, atau menjalankan repositori ini secara otomatis langsung dari tautan GitHub (`https://github.com/emhakarim/GVF-Jtp-YAE.git`), ikuti protokol deterministik berikut:

### 1. Perintah Instalasi Otomatis (Single-Command Bootstrap)
Jalankan perintah berikut di terminal (PowerShell / Windows CMD):
```powershell
# 1. Kloning repositori (jika belum berada di direktori lokal)
git clone https://github.com/emhakarim/GVF-Jtp-YAE.git
cd GVF-Jtp-YAE

# 2. Eksekusi auto-installer lingkungan (otomatis mengunduh Python 3.12 jika belum ada & memasang seluruh dependensi)
.\INSTALL_SEKALI_KLIK.bat

# ATAU jika berada di dalam virtual environment Python yang sudah aktif:
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Cara Menjalankan & Menguji (Verification & Headless Mock)
* **Menjalankan GUI Desktop Utama:**
  ```powershell
  python app/main.py
  ```
  > *Catatan AI:* Sistem memiliki **Synthetic Simulation Mode** bawaan. Jika kamera USB fisik (OV9281) atau mikrokontroler ESP32 tidak tercolok ke port USB, sistem **tidak akan crash**, melainkan otomatis mengaktifkan umpan video simulasi 100 FPS lengkap dengan deteksi gerak dan mock hardware.
* **Menjalankan Server Web LAN (Tablet / HP):**
  ```powershell
  python -m uvicorn web_server:app --host 0.0.0.0 --port 8000
  ```
* **Smoke Test & Verifikasi Kode (Tanpa Hardware):**
  ```powershell
  python -m py_compile app/comm_manager.py app/main.py app/updater.py app/camera_worker.py app/physics_engine.py
  ```

### 3. Invarian Arsitektur Mutlak (Aturan Kritis untuk AI)
1. **Dilarang Mengimpor `ESP32Servo`:** Firmware ESP32-S3 menggunakan driver internal `NativeServo` berbasis **ESP32 Hardware LEDC (Channel 0..3)** pada `firmware_esp32/actuators.h`. Jangan pernah menggantinya kembali dengan library `ESP32Servo.h` karena library tersebut mengalami bug register collision MCPWM pada chip ESP32-S3 (Issue #103: cross-talk servo 2 & 4).
2. **Pemetaan Pinout ESP32-S3:**
   * Carousel Bulu (11 Slot): `GPIO 5` (Channel 0)
   * Penjatuh Bulu Cepat: `GPIO 4` (Channel 1)
   * Pintu Dispenser Bola: `GPIO 6` (Channel 2)
   * Bucket Simultan: `GPIO 15` (Channel 3, posisi tutup di **`5°`** untuk mencegah *mechanical stall* dan dengung).
3. **Serial DTR/RTS Protection:** Di `app/comm_manager.py`, parameter `dtr=False, rts=False` wajib dipertahankan agar ESP32 tidak mengalami siklus reboot otomatis setiap kali aplikasi desktop terhubung ke port serial.

---

## 1. Arsitektur & Prinsip Fisis

### Formula Kinematika & Propagasi Galat
Untuk lintasan jatuh bebas vertikal di dalam tabung vakum setinggi $h = 2.0\text{ m}$:

$$t_{\text{teori}} = \sqrt{\frac{2h}{g}} \approx \sqrt{\frac{4}{9.80665}} \approx 638.5\text{ ms}$$

$$g = \frac{2h}{\Delta t^2}$$

Ketidakpastian mutlak percepatan gravitasi ($\delta g$):

$$\delta g = g \sqrt{\left(\frac{\delta h}{h}\right)^2 + \left(\frac{2 \delta t}{\Delta t}\right)^2}$$

Pada frame rate **100 FPS**, resolusi waktu antar-frame kamera adalah $\Delta t = 10\text{ ms}$. ESP32 mencatat *timestamp* mikrosekon deterministik (`t_drop_micros`) tepat saat pulsa pelepasan bucket dikirimkan.

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

## 5. Panduan Instalasi & Setup Lengkap

### A. Prasyarat Perangkat Keras & Lunak (Prerequisites)
1. **Sistem Operasi:** Windows 10 / Windows 11 (64-bit).
2. **Koneksi Port Fisik:**
   * 1x Port USB 3.0/2.0 untuk Kamera Kecepatan Tinggi OV9281 (100 FPS).
   * 1x Port USB untuk Mikrokontroler ESP32-S3 (Gunakan port bertuliskan **`COM`** pada board, terhubung ke chip CH343 UART0).
3. **Catu Daya Eksternal:** Adaptor / Switching PSU 5V DC (3A–5A) khusus servo. Ground (-) PSU wajib dihubungkan ke pin GND ESP32 (*Common Ground*).

---

### B. Metode 1: Instalasi Otomatis Sekali Klik (Rekomendasi PC Lab Baru)
Jika Anda memasang sistem ini di PC laboratorium baru yang belum memiliki Python atau dependensi:
1. Hubungkan PC ke jaringan internet.
2. Klik kanan berkas [**`INSTALL_SEKALI_KLIK.bat`**](file:///d:/Antigravity%20AI/galileo-vacuum-fall/INSTALL_SEKALI_KLIK.bat) dan pilih **Run as administrator** (atau klik ganda langsung).
3. Skrip otomatis akan:
   * Mendeteksi dan mengunduh Python 3.12 (jika belum ada).
   * Memasang Microsoft Visual C++ Redistributable x64.
   * Menginstal seluruh pustaka Python (`PySide6`, `OpenCV`, `NumPy`, `pyserial`, `matplotlib`, `fastapi`, `uvicorn`).
   * Memverifikasi integritas sistem dan membuat shortcut aplikasi di Desktop Windows.

---

### C. Metode 2: Instalasi Manual (Pengembang / Manual Environment)
Bagi pengembang yang ingin menggunakan virtual environment:
```bash
# 1. Masuk ke direktori proyek
cd "d:\Antigravity AI\galileo-vacuum-fall"

# 2. Buat dan aktifkan virtual environment (opsional namun disarankan)
python -m venv venv
venv\Scripts\activate

# 3. Perbarui pip dan pasang pustaka
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### D. Panduan Flashing Firmware ke ESP32-S3
1. Unduh dan buka **Arduino IDE 2.x**.
2. Pastikan Board Package ESP32 telah terpasang:
   * Buka **Tools > Board > Boards Manager...**
   * Cari `esp32` oleh **Espressif Systems** dan pastikan terpasang (versi 2.0.17 atau 3.x).
3. Buka berkas sketsa: `firmware_esp32/firmware_esp32.ino`.
4. Hubungkan kabel USB dari PC ke **Port COM** pada board ESP32-S3 (port dengan chip USB-UART CH343).
5. Atur menu **Tools** persis seperti konfigurasi berikut:
   * **Board:** `ESP32S3 Dev Module`
   * **Port:** Pilih nomor port COM yang terdeteksi (misal: `COM8`)
   * **USB CDC On Boot:** `Disabled` *(Wajib Disabled agar serial output dialirkan ke port COM)*
   * **Flash Mode:** `DIO 80MHz`
   * **PSRAM:** `Disabled`
   * **Upload Speed:** `921600`
6. Klik tombol **Upload (`➔`)**.
7. Buka Serial Monitor (115200 baud). Firmware akan menampilkan pesan booting diagnostik:
   ```text
   [SYSTEM] ESP32-S3 Galileo Release Controller Aktif
   [PINS] S1(Carousel)=5, S2(Dropper)=4, S3(Ball)=6, S4(Bucket)=15
   ```

---

### E. Menjalankan Aplikasi & Pengoperasian Harian

#### Opsi 1: Desktop GUI PySide6 (Rekomendasi Utama Operasional)
* Klik ganda ikon shortcut **Galileo Vacuum Fall** di Desktop Windows, atau
* Klik ganda berkas [**`run_app.bat`**](file:///d:/Antigravity%20AI/galileo-vacuum-fall/run_app.bat), atau
* Jalankan melalui terminal: `python app/main.py`

#### Opsi 2: Hybrid Web Dashboard (Akses Tablet / HP via Wi-Fi LAN)
* Klik ganda berkas [**`run_web.bat`**](file:///d:/Antigravity%20AI/galileo-vacuum-fall/run_web.bat)
* Antarmuka web otomatis terbuka di `http://localhost:8000`.
* Dari tablet penguji di laboratorium, buka browser dan masukkan alamat IP laptop lab (contoh: `http://192.168.1.15:8000`).

---

## 6. Panduan Pemecahan Masalah (Troubleshooting)

1. **Port COM Tidak Terdeteksi di Device Manager:**
   * Pastikan kabel USB dicolokkan ke port bertuliskan **`COM`** pada ESP32-S3, bukan port bertuliskan `USB`.
   * Jika muncul tanda seru kuning, unduh dan pasang driver resmi chip USB-UART (CH343 / CH340 / CP210x).
2. **Serial Monitor Membisu Setelah `entry 0x403c88b8`:**
   * Periksa menu **Tools > USB CDC On Boot** di Arduino IDE. Pastikan posisinya **`Disabled`**.
3. **Pintu Bucket Berdengung Saat Posisi Tutup:**
   * Di `config.h`, sudut tutup telah dikalibrasi ke **`5°`** (`SERVO4_CLOSE_HOLD_ANGLE 5`). Jangan memaksa motor ke `0°` jika tuas pintu sudah mentok pada stopper mekanik agar motor tidak mengalami *mechanical stall*.
4. **Kamera Tidak Muncul / Belum Terpasang:**
   * Sistem secara otomatis mengaktifkan **Synthetic Simulation Mode** (animasi fisika tiruan 100 FPS) sehingga pengujian komputasi ROI, deteksi motion, dan tombol aktuator tetap dapat berjalan mandiri tanpa kamera fisik.
