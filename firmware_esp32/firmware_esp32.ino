// =================================================================
// Galileo Vacuum Fall Experiment - ESP32 Actuator Controller
// 3-Servo Drop Mechanism (Feather, Ball, Simultaneous)
// Developed for Physics Lab Research | Yotta Aksara Energi & Antigravity AI
// =================================================================

#include <Arduino.h>
#include <ESP32Servo.h>
#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include "config.h"

// Objek Servo
Servo servoFeather;
Servo servoBall;
Servo servoBoth;

// Server WebSocket
WebSocketsServer webSocket = WebSocketsServer(WEBSOCKET_PORT);

// State tracking (auto-close independen untuk staging Servo 1 & 2; Servo 3 latched hingga RESET)
unsigned long featherDropTime = 0;
unsigned long ballDropTime = 0;
bool pendingCloseFeather = false;
bool pendingCloseBall = false;

// Forward declaration
void setupServos();
void executeDrop(const char* target);
void resetAllServos();
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

    Serial.println(F("[SYSTEM] ESP32 Galileo Controller Siap Menerima Perintah (UART & WebSocket)."));
}

void publishStandbyStatus(const char* target) {
    StaticJsonDocument<128> doc;
    doc["status"] = "SERVOS_RESET_STANDBY";
    doc["target"] = target;
    doc["t_micros"] = micros();
    String resp;
    serializeJson(doc, resp);
    Serial.println(resp);
    webSocket.broadcastTXT(resp);
}

void loop() {
    webSocket.loop();

    // Membaca perintah Serial UART
    if (Serial.available()) {
        String input = Serial.readStringUntil('\n');
        input.trim();
        if (input.length() > 0) {
            handleCommand(input);
        }
    }

    // Auto-close independen untuk servo staging (Servo 1 & 2) setelah 1500 ms; Servo 3 tetap terbuka hingga RESET
    if (pendingCloseFeather && (millis() - featherDropTime >= SERVO_STAGE_CLOSE_DELAY_MS)) {
        servoFeather.write(SERVO_HOLD_FEATHER);
        pendingCloseFeather = false;
        publishStandbyStatus("FEATHER");
    }
    if (pendingCloseBall && (millis() - ballDropTime >= SERVO_STAGE_CLOSE_DELAY_MS)) {
        servoBall.write(SERVO_HOLD_BALL);
        pendingCloseBall = false;
        publishStandbyStatus("BALL");
    }
}

void setupServos() {
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    ESP32PWM::allocateTimer(2);
    ESP32PWM::allocateTimer(3);

    servoFeather.setPeriodHertz(50);
    servoBall.setPeriodHertz(50);
    servoBoth.setPeriodHertz(50);

    servoFeather.attach(PIN_SERVO_FEATHER, 500, 2400);
    servoBall.attach(PIN_SERVO_BALL, 500, 2400);
    servoBoth.attach(PIN_SERVO_BOTH, 500, 2400);

    resetAllServos();
}

void resetAllServos() {
    servoFeather.write(SERVO_HOLD_FEATHER);
    servoBall.write(SERVO_HOLD_BALL);
    servoBoth.write(SERVO_HOLD_BOTH);
}

void executeDrop(const char* target) {
    uint32_t t_drop_micros = micros();

    if (strcmp(target, "FEATHER") == 0) {
        servoFeather.write(SERVO_DROP_FEATHER);
        featherDropTime = millis();
        pendingCloseFeather = true;
    } else if (strcmp(target, "BALL") == 0) {
        servoBall.write(SERVO_DROP_BALL);
        ballDropTime = millis();
        pendingCloseBall = true;
    } else if (strcmp(target, "BOTH") == 0) {
        // Bucket kolektor tetap terbuka (latched) sampai menerima perintah RESET eksplisit
        servoBoth.write(SERVO_DROP_BOTH);
    } else {
        return;
    }

    // Respon konfirmasi ke PC dengan timestamp mikrosekon deterministik
    StaticJsonDocument<256> doc;
    doc["event"] = "RELEASED";
    doc["target"] = target;
    doc["t_drop_micros"] = t_drop_micros;
    doc["millis"] = millis();

    String resp;
    serializeJson(doc, resp);
    Serial.println(resp);
    webSocket.broadcastTXT(resp);
}

void handleCommand(const String& jsonStr, uint8_t numClient) {
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, jsonStr);

    if (error) {
        StaticJsonDocument<128> errDoc;
        errDoc["status"] = "ERROR";
        errDoc["msg"] = "INVALID_JSON";
        String errResp;
        serializeJson(errDoc, errResp);
        if (numClient < 255) webSocket.sendTXT(numClient, errResp);
        else Serial.println(errResp);
        return;
    }

    const char* cmd = doc["cmd"];
    if (!cmd) return;

    if (strcmp(cmd, "DROP_FEATHER") == 0) {
        executeDrop("FEATHER");
    } else if (strcmp(cmd, "DROP_BALL") == 0) {
        executeDrop("BALL");
    } else if (strcmp(cmd, "DROP_BOTH") == 0) {
        executeDrop("BOTH");
    } else if (strcmp(cmd, "RESET") == 0) {
        resetAllServos();
        pendingCloseFeather = false;
        pendingCloseBall = false;
        StaticJsonDocument<128> rDoc;
        rDoc["status"] = "MANUAL_RESET_OK";
        String rResp;
        serializeJson(rDoc, rResp);
        if (numClient < 255) webSocket.sendTXT(numClient, rResp);
        else Serial.println(rResp);
    } else if (strcmp(cmd, "PING") == 0) {
        StaticJsonDocument<128> pDoc;
        pDoc["status"] = "PONG";
        pDoc["uptime_ms"] = millis();
        String pResp;
        serializeJson(pDoc, pResp);
        if (numClient < 255) webSocket.sendTXT(numClient, pResp);
        else Serial.println(pResp);
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
