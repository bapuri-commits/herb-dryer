// herb-dryer ESP32 핀맵 — docs/pinmap.md 와 같은 내용 (BOM "핀맵(ESP32)" 시트 원본)
// 바꿀 때는 docs/pinmap.md, BOM 시트, 이 파일 세 곳을 같은 PR에서 함께 바꾼다.
// v3.0: 블루투스·RTC 없음, 펠티어(2차) 제외. v3.1: TCS34725·LED·부저 삭제
#pragma once

// ---- I2C (50~100kHz): SHT31 0x44, BME688 #1 0x77(전실), BME688 #2 0x76(흡기, P2 헤더 SDO→GND, 안 되면 TCA9548A), LCD 0x27
constexpr int PIN_I2C_SDA = 21;
constexpr int PIN_I2C_SCL = 22;

// ---- HX711 로드셀 앰프 (3.3V 동작)
constexpr int PIN_HX711_DT  = 16;
constexpr int PIN_HX711_SCK = 17;

// ---- 출력
constexpr int PIN_HEATER_PWM   = 25;  // DFR0457 #1 → PTC 100W (LEDC 1kHz, 켤 때 2~3초 소프트 스타트)
constexpr int HEATER_MAX_DUTY_PCT = 80;  // 100W × 80% (10A 어댑터·퓨즈 여유)
constexpr int PIN_FAN_CIRC_PWM = 26;  // 60mm 순환팬 4핀 PWM (운전 중 60~100%)
constexpr int PIN_FAN_IN_PWM   = 27;  // 40mm 흡기팬 PWM = 환기량 = 습도 조절
constexpr int FAN_IN_MAX_DUTY_PCT = 30;  // 100%면 바깥 공기 데우는 데 ~90W
constexpr int PIN_FAN_IN_POWER = 2;   // DFR0457 #3 → 흡기팬 12V 차단 (부팅핀: 업로드 확인)
                                      // 끊기 전에 PIN_FAN_IN_PWM 을 INPUT으로 (PWM·타코선 10kΩ 직렬)

// ---- 팬 타코 (입력 전용 핀, 내부 풀업 없음 → 10kΩ 를 3.3V로)
constexpr int PIN_FAN_CIRC_TACH = 34;  // 멈추면 히터 차단
constexpr int PIN_FAN_IN_TACH   = 35;

// ---- 소프트 한계
constexpr float PLENUM_MAX_C = 58.0f;  // DS18B20 플레넘 온도 상한 (하드웨어 서모스탯 65°C 전)

// ---- DS18B20 OneWire (플레넘)
constexpr int PIN_ONEWIRE = 4;

// ---- 버튼 ▲ ▼ 선택 (INPUT_PULLUP)
constexpr int PIN_BTN_UP     = 13;
constexpr int PIN_BTN_DOWN   = 14;
constexpr int PIN_BTN_SELECT = 15;

// ---- 마이크로SD (SPI, CSV 로그)
constexpr int PIN_SD_SCK  = 18;
constexpr int PIN_SD_MISO = 19;
constexpr int PIN_SD_MOSI = 23;
constexpr int PIN_SD_CS   = 5;

// 쓰지 않는 핀: GPIO32·33(v3.1 비움), GPIO12(부팅 전압), GPIO0(부팅), GPIO6~11(플래시), GPIO36/39
