#ifndef CONFIG_H
#define CONFIG_H

// ================= PIN DEFINITIONS =================
// Konfigurasi pin bersih ESP32-S3 (Bebas USB-JTAG & Bebas Strapping)
#define PIN_SERVO_FEATHER_CAROUSEL  5 // Servo 1: Stock Bulu Carousel Indexer (Pin 5)
#define PIN_SERVO_FEATHER_DROPPER   4 // Servo 2: Penjatuh Bulu Cepat ke Bucket (Pin 4)
#define PIN_SERVO_BALL_DISPENSER    6 // Servo 3: Stock Ball Dispenser / Pintu Bola (Pin 6)
#define PIN_SERVO_BUCKET_RELEASE   15 // Servo 4: Release Pintu Bucket Simultan (Pin 15)
#define PIN_STATUS_LED 2              // On-board LED indikator status

// ================= PARAMETER KINEMATIKA & SUDUT =================
// Servo 1: Carousel Stock Bulu (Gerak Lambat & Halus Non-blocking)
#define SERVO1_MIN_ANGLE 0
#define SERVO1_MAX_ANGLE 180
#define SERVO1_STEP_DEG                                                        \
  18 // Interval sudut per bulu (18 deg x 10 = 180 deg, total 11 slot)
#define SERVO1_STEP_INTERVAL_MS                                                \
  65 // Kecepatan sapuan: 65 ms/derajat (~1.17 detik per slot 18 deg, sangat halus, tenang & bebas getaran)

// Servo 2: Penjatuh Bulu ke Bucket (Gerak Cepat)
#define SERVO2_HOLD_ANGLE 0   // Posisi siaga (0 deg)
#define SERVO2_DROP_ANGLE 180 // Gerak cepat ketuk bulu ke bucket (180 deg)
#define SERVO2_STRIKE_HOLD_MS                                                  \
  750 // Waktu jeda di 180 deg sebelum kembali otomatis ke 0 deg

// Servo 3: Stock Ball Dispenser
#define SERVO3_HOLD_TAKE_ANGLE 0 // 0 derajat: Posisi ambil bola / standby
#define SERVO3_DROP_ANGLE 90     // 90 derajat: Menjatuhkan 1 bola ke bucket
#define SERVO3_DISPENSE_HOLD_MS                                                \
  750 // Waktu jeda di 90 deg sebelum kembali otomatis ke 0 deg

// Servo 4: Release Bulu dan Bola (Bucket Dropper Simultan)
#define SERVO4_CLOSE_HOLD_ANGLE 5 // 5 derajat: Tutup rapat pintu bucket & hening (bebas stall)
#define SERVO4_OPEN_RELEASE_ANGLE                                              \
  90 // 90 derajat: Buka pintu bucket cepat (Simultaneous Drop)

// ================= KOMUNIKASI & JARINGAN =================
#define SERIAL_BAUD_RATE 115200

// Kredensial Wi-Fi Mode Station (Koneksi ke Router Lab)
#define WIFI_SSID "LAB_PHYSICS_WIFI"
#define WIFI_PASSWORD "Galileo1589"

// Fallback Access Point jika Wi-Fi Station gagal
#define AP_SSID "Galileo_ESP32_AP"
#define AP_PASSWORD "12345678"
#define HTTP_PORT 80

#endif // CONFIG_H
