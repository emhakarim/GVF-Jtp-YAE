#include "actuators.h"

// ================= CONSTRUCTOR =================
ActuatorSystem::ActuatorSystem()
    : _currentCarouselAngle(0),
      _targetCarouselAngle(0),
      _currentFeatherIndex(0),
      _lastCarouselStepTime(0),
      _dropperTriggerTime(0),
      _dropperReturnTime(0),
      _ballTriggerTime(0),
      _pendingReturnDropper(false),
      _pendingCarouselAdvance(false),
      _pendingReturnBall(false),
      _bucketIsOpen(false) {}

// ================= INISIALISASI HARDWARE =================
void ActuatorSystem::begin() {
    Serial.println(F("[ACTUATORS] Inisialisasi Native Hardware LEDC Servos (50Hz)..."));

    // Kanal LEDC hardware mandiri: bebas cross-talk & independen register
    _servoCarousel.attach(PIN_SERVO_FEATHER_CAROUSEL, 0); // Channel 0 -> Pin 5 (Carousel Bulu)
    _servoDropper.attach(PIN_SERVO_FEATHER_DROPPER,   1); // Channel 1 -> Pin 4 (Penjatuh Bulu)
    _servoBall.attach(PIN_SERVO_BALL_DISPENSER,       2); // Channel 2 -> Pin 6 (Bola Besi)
    _servoBucket.attach(PIN_SERVO_BUCKET_RELEASE,     3); // Channel 3 -> Pin 15 (Bucket Simultan)

    Serial.printf("[ACTUATORS] Hardware PWM Channels Ready: S1(P%d,Ch0), S2(P%d,Ch1), S3(P%d,Ch2), S4(P%d,Ch3)\n",
                  PIN_SERVO_FEATHER_CAROUSEL, PIN_SERVO_FEATHER_DROPPER,
                  PIN_SERVO_BALL_DISPENSER, PIN_SERVO_BUCKET_RELEASE);

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
        _dropperReturnTime = millis(); // Rekam timestamp saat mulai kembali ke posisi aman
    }

    // 3. Carousel Delay Advance: Menunggu tuas pendorong mundur tuntas ke 0 deg
    //    (+ margin 400ms mekanik), baru carousel berputar ke slot berikutnya
    if (_pendingCarouselAdvance && !_pendingReturnDropper && (millis() - _dropperReturnTime >= 400)) {
        _pendingCarouselAdvance = false;
        if (_currentFeatherIndex < 10) {
            _currentFeatherIndex++;
            _targetCarouselAngle = _currentFeatherIndex * SERVO1_STEP_DEG;
            if (_targetCarouselAngle > SERVO1_MAX_ANGLE) {
                _targetCarouselAngle = SERVO1_MAX_ANGLE;
            }
        }
    }

    // 4. Auto-return Timer Servo 3 (Kembali ke 0 deg setelah gelontor)
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
    _pendingCarouselAdvance = true; // Tandai agar carousel bergerak HANYA setelah siklus pendorong selesai

    slotOut = _currentFeatherIndex + 1;
    angleOut = _currentCarouselAngle;
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
    _pendingCarouselAdvance = false;
    _pendingReturnBall = false;
}

void ActuatorSystem::resetCarousel() {
    _currentFeatherIndex = 0;
    _targetCarouselAngle = SERVO1_MIN_ANGLE;
    _currentCarouselAngle = SERVO1_MIN_ANGLE;
    _pendingCarouselAdvance = false;
    _servoCarousel.write(SERVO1_MIN_ANGLE);
}

void ActuatorSystem::stepCarousel() {
    if (_currentFeatherIndex < 10) {
        _currentFeatherIndex++;
    } else {
        _currentFeatherIndex = 0; // Siklus penuh: kembali ke slot 1 jika sudah melewati slot 10
    }
    _targetCarouselAngle = _currentFeatherIndex * SERVO1_STEP_DEG;
    if (_targetCarouselAngle > SERVO1_MAX_ANGLE) {
        _targetCarouselAngle = SERVO1_MAX_ANGLE;
    }
}

void ActuatorSystem::setCarouselIndex(int index) {
    if (index < 0) index = 0;
    if (index > 10) index = 10;
    _currentFeatherIndex = index;
    _targetCarouselAngle = _currentFeatherIndex * SERVO1_STEP_DEG;
}

void ActuatorSystem::setDirectAngle(int servoNum, int angle) {
    if (angle < 0) angle = 0;
    if (angle > 180) angle = 180;
    if (servoNum == 1) {
        _currentCarouselAngle = angle;
        _targetCarouselAngle = angle;
        _servoCarousel.write(angle);
    } else if (servoNum == 2) {
        _servoDropper.write(angle);
    } else if (servoNum == 3) {
        _servoBall.write(angle);
    } else if (servoNum == 4) {
        _servoBucket.write(angle);
    }
    Serial.printf("[TEST-PIN] Servo S%d -> %d deg\n", servoNum, angle);
}
