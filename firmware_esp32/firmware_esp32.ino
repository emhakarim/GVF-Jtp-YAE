// =================================================================
// Galileo Vacuum Fall Experiment - ESP32 Actuator Controller
// 4-Servo Dual-Stage Release System (Modular C++ Architecture)
// Crafted for Physics Lab Research | Yotta Aksara Energi & Antigravity AI
// =================================================================

#include <Arduino.h>
#include <WiFi.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>

#include "config.h"
#include "actuators.h"
#include "webpage.h"

// ================= OBJECTS =================
ActuatorSystem actuators;
AsyncWebServer server(HTTP_PORT);
AsyncWebSocket ws("/ws");
AsyncWebSocket wsRoot("/"); // Kompatibilitas jika klien menghubungkan langsung ke root "/"

// ================= PROTOTYPES =================
void onWsEvent(AsyncWebSocket *server, AsyncWebSocketClient *client,
               AwsEventType type, void *arg, uint8_t *data, size_t len);
void handleWsMessage(void *arg, uint8_t *data, size_t len, AsyncWebSocketClient *client);
void handleCommand(const String& jsonStr, AsyncWebSocketClient *client = nullptr);
void broadcastJson(const JsonDocument& doc);
void sendClientJson(AsyncWebSocketClient *client, const JsonDocument& doc);

// ================= SETUP =================
void setup() {
    Serial.begin(SERIAL_BAUD_RATE);
    delay(300); // Waktu stabilisasi clock UART/USB setelah ROM bootloader

    Serial.println();
    Serial.println(F("================================================="));
    Serial.println(F("[SYSTEM] ESP32-S3 Galileo Release Controller Aktif"));
    Serial.println(F("[PINS] S1(Carousel)=15, S2(Dropper)=4, S3(Ball)=5, S4(Bucket)=6"));
    Serial.println(F("================================================="));

    Serial.setTimeout(10); // Menghindari blocking UART jika ada fragmentasi serial byte
    pinMode(PIN_STATUS_LED, OUTPUT);
    digitalWrite(PIN_STATUS_LED, LOW);

    // Inisialisasi Subsistem Aktuator 4-Servo (Fail-safe initial hold)
    Serial.println(F("[INIT] Memulai inisialisasi aktuator servo..."));
    actuators.begin();
    Serial.println(F("[INIT] Aktuator servo siap."));

    // Koneksi Wi-Fi (Mode Station dengan fallback cepat ke Soft-AP agar USB UART langsung responsif)
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.println(F("[WIFI] Memulai Wi-Fi..."));

    unsigned long startAttemptTime = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - startAttemptTime < 1200) {
        delay(100);
        digitalWrite(PIN_STATUS_LED, !digitalRead(PIN_STATUS_LED));
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.print(F("[WIFI] Terhubung. IP ESP32: http://"));
        Serial.println(WiFi.localIP());
        digitalWrite(PIN_STATUS_LED, HIGH);
    } else {
        Serial.println(F("[WIFI] Station Standby. Mengaktifkan Access Point..."));
        WiFi.mode(WIFI_AP);
        WiFi.softAP(AP_SSID, AP_PASSWORD);
        Serial.print(F("[WIFI] AP Aktif. IP: http://"));
        Serial.println(WiFi.softAPIP());
    }

    // Web Server HTTP Routes (PROGMEM Offline-Resilient Portal)
    server.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
        request->send_P(200, "text/html", MAIN_page);
    });

    // WebSocket Handlers (/ws dan /)
    ws.onEvent(onWsEvent);
    wsRoot.onEvent(onWsEvent);
    server.addHandler(&ws);
    server.addHandler(&wsRoot);

    server.begin();
    Serial.println(F("[HTTP] Asynchronous Web Server & WebSocket Aktif Port 80"));
    Serial.println(F("[SYSTEM] ESP32 Galileo Controller Siap (UART & WebSocket)."));
}

// ================= LOOP =================
void loop() {
    ws.cleanupClients();
    wsRoot.cleanupClients();

    // Update state machine aktuator non-blocking (Servo 1 smooth sweep & timers)
    actuators.update();

    // Baca perintah Serial UART (Prioritas latensi rendah PC)
    if (Serial.available()) {
        String input = Serial.readStringUntil('\n');
        input.trim();
        if (input.length() > 0) {
            Serial.print(F("[UART-RX] "));
            Serial.println(input);
            handleCommand(input, nullptr);
        }
    }
}

// ================= EKSEKUSI PERINTAH & PROTOKOL JSON =================
void handleCommand(const String& jsonStr, AsyncWebSocketClient *client) {
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, jsonStr);

    if (error) {
        StaticJsonDocument<128> errDoc;
        errDoc["status"] = "ERROR";
        errDoc["msg"] = "INVALID_JSON";
        if (client) sendClientJson(client, errDoc);
        else {
            String r; serializeJson(errDoc, r); Serial.println(r);
        }
        return;
    }

    const char* cmd = doc["cmd"];
    if (!cmd) return;

    // 1. Muat Bulu (Servo 2 ketuk cepat, Servo 1 majukan slot carousel)
    if (strcmp(cmd, "DROP_FEATHER") == 0 || strcmp(cmd, "STAGE_FEATHER") == 0) {
        int slot = 0, angle = 0;
        actuators.stageFeather(slot, angle);

        StaticJsonDocument<192> respDoc;
        respDoc["event"] = "STAGED";
        respDoc["target"] = "FEATHER";
        respDoc["feather_slot"] = slot;
        respDoc["slot_angle"] = angle;
        respDoc["millis"] = millis();
        broadcastJson(respDoc);
    }
    // 2. Muat Bola Besi (Servo 3 gelontorkan 1 bola ke bucket)
    else if (strcmp(cmd, "DROP_BALL") == 0 || strcmp(cmd, "STAGE_BALL") == 0) {
        actuators.stageBall();

        StaticJsonDocument<128> respDoc;
        respDoc["event"] = "STAGED";
        respDoc["target"] = "BALL";
        respDoc["millis"] = millis();
        broadcastJson(respDoc);
    }
    // 3. Buka Bucket (Servo 4 buka cepat 90 deg - Jatuh Bebas Simultan)
    else if (strcmp(cmd, "DROP_BOTH") == 0) {
        uint32_t t_drop_micros = actuators.releaseBucket();

        StaticJsonDocument<256> respDoc;
        respDoc["event"] = "RELEASED";
        respDoc["target"] = "BOTH";
        respDoc["t_drop_micros"] = t_drop_micros;
        respDoc["millis"] = millis();
        broadcastJson(respDoc);
    }
    // 4. Reset Posisi Aktuator (Servo 4 tutup ke 0 deg)
    else if (strcmp(cmd, "RESET") == 0) {
        actuators.resetAll();

        StaticJsonDocument<128> respDoc;
        respDoc["status"] = "MANUAL_RESET_OK";
        respDoc["bucket"] = "CLOSED";
        broadcastJson(respDoc);
    }
    // 5. Reset Carousel Bulu ke Slot 1 (0 deg)
    else if (strcmp(cmd, "RESET_CAROUSEL") == 0) {
        actuators.resetCarousel();

        StaticJsonDocument<128> respDoc;
        respDoc["status"] = "CAROUSEL_RESET";
        respDoc["target_slot"] = 1;
        respDoc["target_angle"] = 0;
        broadcastJson(respDoc);
    }
    // 6. Langkah Manual Carousel (+18 deg)
    else if (strcmp(cmd, "STEP_CAROUSEL") == 0) {
        actuators.stepCarousel();

        StaticJsonDocument<128> respDoc;
        respDoc["status"] = "CAROUSEL_STEP";
        respDoc["feather_slot"] = actuators.getFeatherIndex() + 1;
        respDoc["target_angle"] = actuators.getCarouselAngle();
        broadcastJson(respDoc);
    }
    // 7. Set Slot Spesifik Carousel
    else if (strcmp(cmd, "SET_CAROUSEL") == 0) {
        int idx = doc["index"] | 0;
        actuators.setCarouselIndex(idx);

        StaticJsonDocument<128> respDoc;
        respDoc["status"] = "CAROUSEL_SET";
        respDoc["feather_slot"] = actuators.getFeatherIndex() + 1;
        respDoc["target_angle"] = actuators.getCarouselAngle();
        broadcastJson(respDoc);
    }
    // 8. Heartbeat PING
    else if (strcmp(cmd, "PING") == 0) {
        StaticJsonDocument<192> respDoc;
        respDoc["status"] = "PONG";
        respDoc["uptime_ms"] = millis();
        respDoc["feather_slot"] = actuators.getFeatherIndex() + 1;
        respDoc["carousel_angle"] = actuators.getCarouselAngle();
        respDoc["bucket_open"] = actuators.isBucketOpen();
        if (client) sendClientJson(client, respDoc);
        else {
            String r; serializeJson(respDoc, r); Serial.println(r);
        }
    }
    // 9. Uji Langsung Per Pin (Direct Diagnostic Pin Test)
    else if (strcmp(cmd, "TEST_PIN") == 0) {
        int pin = doc["pin"] | 0;
        int sNum = doc["servo"] | 0;
        int angle = doc["angle"] | 0;

        if (pin == PIN_SERVO_FEATHER_CAROUSEL || sNum == 1) sNum = 1;
        else if (pin == PIN_SERVO_FEATHER_DROPPER || sNum == 2) sNum = 2;
        else if (pin == PIN_SERVO_BALL_DISPENSER || sNum == 3) sNum = 3;
        else if (pin == PIN_SERVO_BUCKET_RELEASE || sNum == 4) sNum = 4;

        if (sNum >= 1 && sNum <= 4) {
            actuators.setDirectAngle(sNum, angle);
        }

        StaticJsonDocument<128> tDoc;
        tDoc["status"] = "TEST_PIN_OK";
        tDoc["servo"] = sNum;
        tDoc["angle"] = angle;
        broadcastJson(tDoc);
    }
}

// ================= BROADCAST & TRANSMISI DATA =================
void broadcastJson(const JsonDocument& doc) {
    String output;
    serializeJson(doc, output);
    Serial.println(output);
    ws.textAll(output);
    wsRoot.textAll(output);
}

void sendClientJson(AsyncWebSocketClient *client, const JsonDocument& doc) {
    if (client && client->status() == WS_CONNECTED) {
        String output;
        serializeJson(doc, output);
        client->text(output);
    }
}

// ================= WEBSOCKET EVENT LISTENERS =================
void onWsEvent(AsyncWebSocket *server, AsyncWebSocketClient *client,
               AwsEventType type, void *arg, uint8_t *data, size_t len) {
    switch (type) {
        case WS_EVT_CONNECT:
            Serial.printf("[WS] Klien #%u terhubung dari %s\n", client->id(), client->remoteIP().toString().c_str());
            break;
        case WS_EVT_DISCONNECT:
            Serial.printf("[WS] Klien #%u terputus\n", client->id());
            break;
        case WS_EVT_DATA:
            handleWsMessage(arg, data, len, client);
            break;
        default:
            break;
    }
}

void handleWsMessage(void *arg, uint8_t *data, size_t len, AsyncWebSocketClient *client) {
    AwsFrameInfo *info = (AwsFrameInfo*)arg;
    if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT) {
        data[len] = 0;
        handleCommand(String((char*)data), client);
    }
}
