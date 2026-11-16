#ifndef CONFIG_H
#define CONFIG_H

// ================= PIN MAPPING 4 SERVO AKTUATOR =================
// Sesuai konfigurasi mekanik sistem pelepasan dua tahap:
#define PIN_SERVO_FEATHER_CAROUSEL 15  // Servo 1: Stock bulu (0 - 180 deg)
#define PIN_SERVO_FEATHER_DROPPER  16  // Servo 2: Penjatuh bulu (0 - 180 deg cepat)
#define PIN_SERVO_BALL_DISPENSER   17  // Servo 3: Stock ball (0 deg ambil, 90 deg jatuhkan)
#define PIN_SERVO_BUCKET_RELEASE   18  // Servo 4: Release bulu & ball (0 deg tutup, 90 deg buka)
#define PIN_STATUS_LED              2  // On-board LED indikator status

// ================= PARAMETER KINEMATIKA & SUDUT (DEGREES) =================
// Servo 1: Carousel Stock Bulu (Gerak Lambat/Halus Non-blocking)
#define SERVO1_MIN_ANGLE            0
#define SERVO1_MAX_ANGLE          180
#define SERVO1_STEP_DEG            18   // Interval sudut per bulu (10 interval = 11 slot: 0, 18, 36... 180)
#define SERVO1_STEP_INTERVAL_MS    25   // Kecepatan sapuan: 25 ms/derajat (halus, bebas osilasi mekanik)

// Servo 2: Penjatuh Bulu ke Bucket (Gerak Cepat)
#define SERVO2_HOLD_ANGLE           0   // Posisi siaga
#define SERVO2_DROP_ANGLE         180   // Gerak cepat menjatuhkan bulu ke bucket
#define SERVO2_STRIKE_HOLD_MS     750   // Waktu jeda di 180 deg sebelum kembali otomatis ke 0 deg

// Servo 3: Stock Ball Dispenser
#define SERVO3_HOLD_TAKE_ANGLE      0   // 0 derajat: Posisi ambil bola / standby
#define SERVO3_DROP_ANGLE          90   // 90 derajat: Menjatuhkan 1 bola ke bucket
#define SERVO3_DISPENSE_HOLD_MS   750   // Waktu jeda di 90 deg sebelum kembali otomatis ke 0 deg

// Servo 4: Release Bulu dan Ball (Bucket Dropper Simultan)
#define SERVO4_CLOSE_HOLD_ANGLE     0   // 0 derajat: Tutup bucket penampung (Hold)
#define SERVO4_OPEN_RELEASE_ANGLE  90   // 90 derajat: Buka pintu bucket cepat (Simultaneous Drop)

// ================= KOMUNIKASI & JARINGAN =================
#define SERIAL_BAUD_RATE     115200

// Kredensial Wi-Fi Mode Station (Koneksi ke Router Lab)
#define WIFI_SSID            "LAB_PHYSICS_WIFI"
#define WIFI_PASSWORD        "Galileo1589"

// Fallback Access Point jika Wi-Fi Station gagal
#define AP_SSID              "Galileo_ESP32_AP"
#define AP_PASSWORD          "12345678"
#define WEBSOCKET_PORT       81

#endif // CONFIG_H
