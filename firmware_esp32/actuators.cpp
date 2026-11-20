#include "actuators.h"

// ================= CONSTRUCTOR =================
ActuatorSystem::ActuatorSystem()
    : _currentCarouselAngle(0),
      _targetCarouselAngle(0),
      _currentFeatherIndex(0),
      _lastCarouselStepTime(0),
      _dropperTriggerTime(0),
      _ballTriggerTime(0),
      _pendingReturnDropper(false),
      _pendingReturnBall(false),
      _bucketIsOpen(false) {}

// ================= INISIALISASI HARDWARE =================
void ActuatorSystem::begin() {
    // Alokasi 4 timer hardware PWM ESP32
    ESP32PWM::allocateTimer(0);
    ESP32PWM::allocateTimer(1);
    ESP32PWM::allocateTimer(2);
    ESP32PWM::allocateTimer(3);

    _servoCarousel.setPeriodHertz(50);
    _servoDropper.setPeriodHertz(50);
    _servoBall.setPeriodHertz(50);
    _servoBucket.setPeriodHertz(50);

    int ch1 = _servoCarousel.attach(PIN_SERVO_FEATHER_CAROUSEL, 500, 2400);
    int ch2 = _servoDropper.attach(PIN_SERVO_FEATHER_DROPPER, 500, 2400);
    int ch3 = _servoBall.attach(PIN_SERVO_BALL_DISPENSER, 500, 2400);
    int ch4 = _servoBucket.attach(PIN_SERVO_BUCKET_RELEASE, 500, 2400);

    Serial.printf("[ACTUATORS] Servo Attached Channels: S1=%d, S2=%d, S3=%d, S4=%d\n", ch1, ch2, ch3, ch4);

    // Posisi awal aman (Fail-safe hold)
    resetAll();
    _currentCarouselAngle = SERVO1_MIN_ANGLE;
    _targetCarouselAngle = SERVO1_MIN_ANGLE;
    _currentFeatherIndex = 0;
    _servoCarousel.write(_currentCarouselAngle);
}

// ================= STATE MACHINE & TIMER LOOP =================
void ActuatorSystem::update() {
    // 1. Interpolasi Sudut Servo 1 (Gerak Halus & Lambat Non-blocking)
    if (_currentCarouselAngle != _targetCarouselAngle) {
        if (millis() - _lastCarouselStepTime >= SERVO1_STEP_INTERVAL_MS) {
            if (_currentCarouselAngle < _targetCarouselAngle) {
                _currentCarouselAngle++;
            } else if (_currentCarouselAngle > _targetCarouselAngle) {
                _currentCarouselAngle--;
            }
            _servoCarousel.write(_currentCarouselAngle);
            _lastCarouselStepTime = millis();
        }
    }

    // 2. Auto-return Timer Servo 2 (Kembali ke 0 deg setelah ketuk)
    if (_pendingReturnDropper && (millis() - _dropperTriggerTime >= SERVO2_STRIKE_HOLD_MS)) {
        _servoDropper.write(SERVO2_HOLD_ANGLE);
        _pendingReturnDropper = false;
    }

    // 3. Auto-return Timer Servo 3 (Kembali ke 0 deg setelah gelontor)
    if (_pendingReturnBall && (millis() - _ballTriggerTime >= SERVO3_DISPENSE_HOLD_MS)) {
        _servoBall.write(SERVO3_HOLD_TAKE_ANGLE);
        _pendingReturnBall = false;
    }
}

// ================= AKSI PELEPASAN & STAGING =================
bool ActuatorSystem::stageFeather(int &slotOut, int &angleOut) {
    // Gerakkan Servo 2 cepat ke 180 deg untuk menjatuhkan bulu slot aktif ke bucket
    _servoDropper.write(SERVO2_DROP_ANGLE);
    _dropperTriggerTime = millis();
    _pendingReturnDropper = true;

    slotOut = _currentFeatherIndex + 1;
    angleOut = _currentCarouselAngle;

    // Majukan target Servo 1 ke slot berikutnya secara otomatis & lambat
    if (_currentFeatherIndex < 10) {
        _currentFeatherIndex++;
        _targetCarouselAngle = _currentFeatherIndex * SERVO1_STEP_DEG;
        if (_targetCarouselAngle > SERVO1_MAX_ANGLE) {
            _targetCarouselAngle = SERVO1_MAX_ANGLE;
        }
    }
    return true;
}

bool ActuatorSystem::stageBall() {
    // Gerakkan Servo 3 ke 90 deg untuk menggelontorkan 1 bola ke bucket
    _servoBall.write(SERVO3_DROP_ANGLE);
    _ballTriggerTime = millis();
    _pendingReturnBall = true;
    return true;
}

uint32_t ActuatorSystem::releaseBucket() {
    // Catat timestamp mikrosekon deterministik sebelum pulsa PWM bergerak
    uint32_t t_micros = micros();

    // Buka pintu bucket cepat ke 90 deg (Latched open)
    _servoBucket.write(SERVO4_OPEN_RELEASE_ANGLE);
    _bucketIsOpen = true;

    return t_micros;
}

void ActuatorSystem::resetAll() {
    _servoBucket.write(SERVO4_CLOSE_HOLD_ANGLE);
    _servoDropper.write(SERVO2_HOLD_ANGLE);
    _servoBall.write(SERVO3_HOLD_TAKE_ANGLE);
    _bucketIsOpen = false;
    _pendingReturnDropper = false;
    _pendingReturnBall = false;
}

void ActuatorSystem::resetCarousel() {
    _currentFeatherIndex = 0;
    _targetCarouselAngle = SERVO1_MIN_ANGLE;
}

void ActuatorSystem::stepCarousel() {
    if (_currentFeatherIndex < 10) {
        _currentFeatherIndex++;
        _targetCarouselAngle = _currentFeatherIndex * SERVO1_STEP_DEG;
        if (_targetCarouselAngle > SERVO1_MAX_ANGLE) {
            _targetCarouselAngle = SERVO1_MAX_ANGLE;
        }
    }
}

void ActuatorSystem::setCarouselIndex(int index) {
    if (index < 0) index = 0;
    if (index > 10) index = 10;
    _currentFeatherIndex = index;
    _targetCarouselAngle = _currentFeatherIndex * SERVO1_STEP_DEG;
}
