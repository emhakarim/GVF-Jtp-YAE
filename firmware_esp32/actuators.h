#ifndef ACTUATORS_H
#define ACTUATORS_H

#include "config.h"
#include <Arduino.h>
#include <ESP32Servo.h>

// ================= KELAS MANAJEMEN 4-SERVO =================
class ActuatorSystem {
private:
  Servo _servoCarousel; // Servo 1: Carousel Indexer Stock Bulu (Pin 15)
  Servo _servoDropper;  // Servo 2: Penjatuh Bulu Cepat ke Bucket (Pin 16)
  Servo _servoBall;     // Servo 3: Stock Ball Dispenser (Pin 17)
  Servo _servoBucket;   // Servo 4: Release Pintu Bucket Simultan (Pin 18)

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

  // Getters status
  int getFeatherIndex() const { return _currentFeatherIndex; }
  int getCarouselAngle() const { return _currentCarouselAngle; }
  bool isBucketOpen() const { return _bucketIsOpen; }
  bool isDropperResetDone(bool &wasPending);
  bool isBallResetDone(bool &wasPending);
};

#endif // ACTUATORS_H
