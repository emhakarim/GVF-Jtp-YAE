#ifndef CONFIG_H
#define CONFIG_H

// ================= PIN MAPPING SERVO AKTUATOR =================
// Menghindari strapping pins (GPIO 0, 2, 12, 15) demi keamanan boot
#define PIN_SERVO_FEATHER   18  // Servo 1: Pemilah & pelepas bulu
#define PIN_SERVO_BALL      19  // Servo 2: Pemilah & pelepas bola besi
#define PIN_SERVO_BOTH      21  // Servo 3: Pelepas simultan (bulu & bola)
#define PIN_STATUS_LED       2  // On-board LED indikator status

// ================= SUDUT SERVO (DEGREES) =================
#define SERVO_HOLD_FEATHER    0
#define SERVO_DROP_FEATHER   90

#define SERVO_HOLD_BALL       0
#define SERVO_DROP_BALL      90

#define SERVO_HOLD_BOTH       0
#define SERVO_DROP_BOTH      90

#define SERVO_ACTION_DELAY_MS 600 // Durasi mempertahankan posisi rilis sebelum kembali standby

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
