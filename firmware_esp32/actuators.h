#ifndef ACTUATORS_H
#define ACTUATORS_H

#include <Arduino.h>
#include "config.h"

#if defined(ESP_ARDUINO_VERSION_VAL)
  #if ESP_ARDUINO_VERSION >= ESP_ARDUINO_VERSION_VAL(3, 0, 0)
    #define USE_LEDC_CORE_V3 1
  #endif
#elif defined(ESP_ARDUINO_VERSION_MAJOR) && (ESP_ARDUINO_VERSION_MAJOR >= 3)
  #define USE_LEDC_CORE_V3 1
#endif

// ================= DRIVER SERVO NATIVE ESP32 HARDWARE LEDC =================
// Menghilangkan bug cross-talk MCPWM pada ESP32-S3 (ESP32Servo Issue #103)
// Setiap servo memiliki kanal hardware LEDC independen (Channel 0..3).
class NativeServo {
private:
    int _pin;
    int _channel;
    int _minUs;
    int _maxUs;
    int _currentAngle;

public:
    NativeServo() : _pin(-1), _channel(-1), _minUs(500), _maxUs(2400), _currentAngle(0) {}

    bool attach(int pin, int channel, int minUs = 500, int maxUs = 2400) {
        _pin = pin;
        _channel = channel;
        _minUs = minUs;
        _maxUs = maxUs;

#ifdef USE_LEDC_CORE_V3
        return ledcAttachChannel(_pin, 50, 14, _channel);
#else
        ledcSetup(_channel, 50, 14); // 50 Hz, 14-bit
        ledcAttachPin(_pin, _channel);
        return true;
#endif
    }

    void writeMicroseconds(int us) {
        if (_pin < 0) return;
        us = constrain(us, _minUs, _maxUs);
        // Periode 50 Hz = 20000 us. Resolusi 14-bit = 16384 ticks.
        uint32_t duty = (uint32_t)(((uint64_t)us * 16384ULL) / 20000ULL);

#ifdef USE_LEDC_CORE_V3
        ledcWrite(_pin, duty);
#else
        ledcWrite(_channel, duty);
#endif
    }

    void write(int angle) {
        angle = constrain(angle, 0, 180);
        _currentAngle = angle;
        int us = map(angle, 0, 180, _minUs, _maxUs);
        writeMicroseconds(us);
    }

    int read() const {
        return _currentAngle;
    }
};

// ================= KELAS MANAJEMEN 4-SERVO =================
class ActuatorSystem {
private:
    NativeServo _servoCarousel; // Servo 1: Carousel Indexer Stock Bulu (Pin 15, Channel 0)
    NativeServo _servoDropper;  // Servo 2: Penjatuh Bulu Cepat ke Bucket (Pin 4, Channel 1)
    NativeServo _servoBall;     // Servo 3: Stock Ball Dispenser (Pin 5, Channel 2)
    NativeServo _servoBucket;   // Servo 4: Release Pintu Bucket Simultan (Pin 6, Channel 3)

  int _currentCarouselAngle;
  int _targetCarouselAngle;
  int _currentFeatherIndex; // 0 s/d 10 (Total 11 slot: 0, 18, 36 ... 180 deg)
  unsigned long _lastCarouselStepTime;

  unsigned long _dropperTriggerTime;
  unsigned long _ballTriggerTime;
  bool _pendingReturnDropper;
  bool _pendingReturnBall;

  bool _bucketIsOpen;

public:
  ActuatorSystem();

  void begin();
  void update(); // Wajib dipanggil di loop() untuk non-blocking sweep & timers

  bool stageFeather(int &slotOut, int &angleOut);
  bool stageBall();
  uint32_t releaseBucket();
  void resetAll();
  void resetCarousel();
  void stepCarousel();
  void setCarouselIndex(int index);
  void setDirectAngle(int servoNum, int angle);

  // Getters status
  int getFeatherIndex() const { return _currentFeatherIndex; }
  int getCarouselAngle() const { return _currentCarouselAngle; }
  bool isBucketOpen() const { return _bucketIsOpen; }
  bool isDropperResetDone(bool &wasPending);
  bool isBallResetDone(bool &wasPending);
};

#endif // ACTUATORS_H
