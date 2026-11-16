// =================================================================
// Galileo Vacuum Fall Experiment - ESP32 Actuator Controller
// 4-Servo Dual-Stage Release System (Carosel, Dropper, Ball, Bucket)
// Developed for Physics Lab Research | Yotta Aksara Energi & Antigravity AI
// =================================================================

#include <Arduino.h>
#include <ESP32Servo.h>
#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include "config.h"

// Objek 4 Servo Aktuator
Servo servoCarousel; // Servo 1 (Pin 15): Stock Bulu Carousel Indexer
Servo servoDropper;  // Servo 2 (Pin 16): Penjatuh Bulu Cepat ke Bucket
Servo servoBall;     // Servo 3 (Pin 17): Stock Ball Dispenser
Servo servoBucket;   // Servo 4 (Pin 18): Bucket Release Simultan (Jatuh Bebas)

// Server WebSocket
WebSocketsServer webSocket = WebSocketsServer(WEBSOCKET_PORT);

// State tracking Servo 1 (Gerak Halus Non-blocking)
int currentCarouselAngle = 0;
int targetCarouselAngle = 0;
int currentFeatherIndex = 0; // Index 0 s/d 10 (Total 11 slot: 0, 18, 36 ... 180 deg)
unsigned long lastCarouselStepTime = 0;

// State tracking Servo 2 & Servo 3 (Auto-return timer)
unsigned long dropperTriggerTime = 0;
unsigned long ballTriggerTime = 0;
bool pendingReturnDropper = false;
bool pendingReturnBall = false;

// State tracking Servo 4 (Latched open saat drop hingga reset eksplisit)
bool bucketIsOpen = false;

// Forward declaration
void setupServos();
void updateCarouselSmoothMotion();
void updateStagingTimers();
void stageFeather();
void stageBall();
void releaseBucketSimultaneous();
void resetAllServos();
void resetCarousel();
void sendResponse(const JsonDocument& doc, uint8_t numClient = 255);
void handleCommand(const String& jsonStr, uint8_t numClient = 255);
void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length);

void setup() {
    Serial.begin(SERIAL_BAUD_RATE);
    pinMode(PIN_STATUS_LED, OUTPUT);
    digitalWrite(PIN_STATUS_LED, LOW);

    setupServos();

    // Inisialisasi Wi-Fi (Station dengan Fallback ke AP)
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.println(F("[WIFI] Menghubungkan ke jaringan Wi-Fi..."));

    unsigned long startAttemptTime = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < 6000) {
        delay(200);
        digitalWrite(PIN_STATUS_LED, !digitalRead(PIN_STATUS_LED));
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.print(F("[WIFI] Terhubung. IP ESP32: "));
        Serial.println(WiFi.localIP());
        digitalWrite(PIN_STATUS_LED, HIGH);
    } else {
        Serial.println(F("[WIFI] Gagal terhubung ke Station. Mengaktifkan Access Point..."));
        WiFi.mode(WIFI_AP);
        WiFi.softAP(AP_SSID, AP_PASSWORD);
        Serial.print(F("[WIFI] AP Aktif. IP: "));
        Serial.println(WiFi.softAPIP());
    }

    // Inisialisasi WebSocket Server
    webSocket.begin();
    webSocket.onEvent(webSocketEvent);

    Serial.println(F("[SYSTEM] ESP32 Galileo Controller 4-Servo Siap (UART & WebSocket)."));
}

void loop() {
    webSocket.loop();

    // 1. Baca Perintah Serial UART
    if (Serial.available()) {
        String input = Serial.readStringUntil('\n');
        input.trim();
        if (input.length() > 0) {
            handleCommand(input);
        }
    }

    // 2. Interpolasi Sudut Servo 1 (Gerak Lambat & Halus Non-blocking)
    updateCarouselSmoothMotion();

    // 3. Auto-return Timer untuk Servo 2 & 3
    updateStagingTimers();
}

void setupServos() {
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    ESP32PWM::allocateTimer(2);
    ESP32PWM::allocateTimer(3);

    servoCarousel.setPeriodHertz(50);
    servoDropper.setPeriodHertz(50);
    servoBall.setPeriodHertz(50);
    servoBucket.setPeriodHertz(50);

    servoCarousel.attach(PIN_SERVO_FEATHER_CAROUSEL, 500, 2400);
    servoDropper.attach(PIN_SERVO_FEATHER_DROPPER, 500, 2400);
    servoBall.attach(PIN_SERVO_BALL_DISPENSER, 500, 2400);
    servoBucket.attach(PIN_SERVO_BUCKET_RELEASE, 500, 2400);

    resetAllServos();
    currentCarouselAngle = SERVO1_MIN_ANGLE;
    targetCarouselAngle = SERVO1_MIN_ANGLE;
    currentFeatherIndex = 0;
    servoCarousel.write(currentCarouselAngle);
}

void updateCarouselSmoothMotion() {
    if (currentCarouselAngle != targetCarouselAngle) {
        if (millis() - lastCarouselStepTime >= SERVO1_STEP_INTERVAL_MS) {
            if (currentCarouselAngle < targetCarouselAngle) {
                currentCarouselAngle++;
            } else if (currentCarouselAngle > targetCarouselAngle) {
                currentCarouselAngle--;
            }
            servoCarousel.write(currentCarouselAngle);
            lastCarouselStepTime = millis();
        }
    }
}

void updateStagingTimers() {
    // Servo 2 kembali ke posisi siaga 0 deg setelah memukul/menjatuhkan bulu
    if (pendingReturnDropper && (millis() - dropperTriggerTime >= SERVO2_STRIKE_HOLD_MS)) {
        servoDropper.write(SERVO2_HOLD_ANGLE);
        pendingReturnDropper = false;

        StaticJsonDocument<128> doc;
        doc["status"] = "STAGING_READY";
        doc["target"] = "FEATHER_DROPPER";
        doc["feather_index"] = currentFeatherIndex;
        doc["angle"] = currentCarouselAngle;
        sendResponse(doc);
    }

    // Servo 3 kembali ke posisi siaga 0 deg setelah menjatuhkan 1 bola
    if (pendingReturnBall && (millis() - ballTriggerTime >= SERVO3_DISPENSE_HOLD_MS)) {
        servoBall.write(SERVO3_HOLD_TAKE_ANGLE);
        pendingReturnBall = false;

        StaticJsonDocument<128> doc;
        doc["status"] = "STAGING_READY";
        doc["target"] = "BALL_DISPENSER";
        sendResponse(doc);
    }
}

void stageFeather() {
    // 1. Gerakkan Servo 2 cepat ke 180 deg untuk menjatuhkan bulu yang berada di slot aktif ke bucket
    servoDropper.write(SERVO2_DROP_ANGLE);
    dropperTriggerTime = millis();
    pendingReturnDropper = true;

    // Respon konfirmasi instan
    StaticJsonDocument<192> doc;
    doc["event"] = "STAGED";
    doc["target"] = "FEATHER";
    doc["feather_slot"] = currentFeatherIndex + 1;
    doc["slot_angle"] = currentCarouselAngle;
    doc["millis"] = millis();
    sendResponse(doc);

    // 2. Majukan Carousel Servo 1 ke bulu berikutnya secara lambat dan otomatis
    if (currentFeatherIndex < 10) {
        currentFeatherIndex++;
        targetCarouselAngle = currentFeatherIndex * SERVO1_STEP_DEG;
        if (targetCarouselAngle > SERVO1_MAX_ANGLE) {
            targetCarouselAngle = SERVO1_MAX_ANGLE;
        }
    }
}

void stageBall() {
    // Gerakkan Servo 3 dari 0 deg ke 90 deg untuk menggelontorkan 1 bola ke bucket
    servoBall.write(SERVO3_DROP_ANGLE);
    ballTriggerTime = millis();
    pendingReturnBall = true;

    StaticJsonDocument<128> doc;
    doc["event"] = "STAGED";
    doc["target"] = "BALL";
    doc["millis"] = millis();
    sendResponse(doc);
}

void releaseBucketSimultaneous() {
    // Servo 4: Buka pintu bucket cepat ke 90 deg
    uint32_t t_drop_micros = micros();
    servoBucket.write(SERVO4_OPEN_RELEASE_ANGLE);
    bucketIsOpen = true;

    StaticJsonDocument<256> doc;
    doc["event"] = "RELEASED";
    doc["target"] = "BOTH";
    doc["t_drop_micros"] = t_drop_micros;
    doc["millis"] = millis();
    sendResponse(doc);
}

void resetAllServos() {
    // Tutup bucket penampung & kembalikan penjatuh ke posisi hold
    servoBucket.write(SERVO4_CLOSE_HOLD_ANGLE);
    servoDropper.write(SERVO2_HOLD_ANGLE);
    servoBall.write(SERVO3_HOLD_TAKE_ANGLE);
    bucketIsOpen = false;
    pendingReturnDropper = false;
    pendingReturnBall = false;
}

void resetCarousel() {
    // Putar balik Servo 1 ke slot pertama (0 deg) secara halus
    currentFeatherIndex = 0;
    targetCarouselAngle = SERVO1_MIN_ANGLE;
}

void sendResponse(const JsonDocument& doc, uint8_t numClient) {
    String resp;
    serializeJson(doc, resp);
    Serial.println(resp);
    if (numClient < 255) {
        webSocket.sendTXT(numClient, resp);
    } else {
        webSocket.broadcastTXT(resp);
    }
}

void handleCommand(const String& jsonStr, uint8_t numClient) {
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, jsonStr);

    if (error) {
        StaticJsonDocument<128> errDoc;
        errDoc["status"] = "ERROR";
        errDoc["msg"] = "INVALID_JSON";
        sendResponse(errDoc, numClient);
        return;
    }

    const char* cmd = doc["cmd"];
    if (!cmd) return;

    if (strcmp(cmd, "DROP_FEATHER") == 0 || strcmp(cmd, "STAGE_FEATHER") == 0) {
        stageFeather();
    } else if (strcmp(cmd, "DROP_BALL") == 0 || strcmp(cmd, "STAGE_BALL") == 0) {
        stageBall();
    } else if (strcmp(cmd, "DROP_BOTH") == 0) {
        releaseBucketSimultaneous();
    } else if (strcmp(cmd, "RESET") == 0) {
        resetAllServos();
        StaticJsonDocument<128> rDoc;
        rDoc["status"] = "MANUAL_RESET_OK";
        rDoc["bucket"] = "CLOSED";
        sendResponse(rDoc, numClient);
    } else if (strcmp(cmd, "RESET_CAROUSEL") == 0) {
        resetCarousel();
        StaticJsonDocument<128> cDoc;
        cDoc["status"] = "CAROUSEL_RESET";
        cDoc["target_slot"] = 1;
        cDoc["target_angle"] = 0;
        sendResponse(cDoc, numClient);
    } else if (strcmp(cmd, "STEP_CAROUSEL") == 0) {
        if (currentFeatherIndex < 10) {
            currentFeatherIndex++;
            targetCarouselAngle = currentFeatherIndex * SERVO1_STEP_DEG;
            if (targetCarouselAngle > SERVO1_MAX_ANGLE) targetCarouselAngle = SERVO1_MAX_ANGLE;
        }
        StaticJsonDocument<128> sDoc;
        sDoc["status"] = "CAROUSEL_STEP";
        sDoc["feather_slot"] = currentFeatherIndex + 1;
        sDoc["target_angle"] = targetCarouselAngle;
        sendResponse(sDoc, numClient);
    } else if (strcmp(cmd, "SET_CAROUSEL") == 0) {
        int idx = doc["index"] | 0;
        if (idx < 0) idx = 0;
        if (idx > 10) idx = 10;
        currentFeatherIndex = idx;
        targetCarouselAngle = currentFeatherIndex * SERVO1_STEP_DEG;
        StaticJsonDocument<128> setDoc;
        setDoc["status"] = "CAROUSEL_SET";
        setDoc["feather_slot"] = currentFeatherIndex + 1;
        setDoc["target_angle"] = targetCarouselAngle;
        sendResponse(setDoc, numClient);
    } else if (strcmp(cmd, "PING") == 0) {
        StaticJsonDocument<192> pDoc;
        pDoc["status"] = "PONG";
        pDoc["uptime_ms"] = millis();
        pDoc["feather_slot"] = currentFeatherIndex + 1;
        pDoc["carousel_angle"] = currentCarouselAngle;
        pDoc["bucket_open"] = bucketIsOpen;
        sendResponse(pDoc, numClient);
    }
}

void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            Serial.printf("[WS] Client #%u Disconnected\n", num);
            break;
        case WStype_CONNECTED:
            Serial.printf("[WS] Client #%u Connected\n", num);
            break;
        case WStype_TEXT: {
            String text = String((char*)payload);
            handleCommand(text, num);
            break;
        }
        default:
            break;
    }
}
