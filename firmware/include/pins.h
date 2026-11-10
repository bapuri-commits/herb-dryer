// herb-dryer ESP32 핀맵 — docs/pinmap.md 와 같은 내용 (BOM "핀맵(ESP32)" 시트 원본)
// 바꿀 때는 docs/pinmap.md, BOM 시트, 이 파일 세 곳을 같은 PR에서 함께 바꾼다.
#pragma once

// ---- I2C: TCS34725 0x29, SHT31 0x44, BME688 #1 0x77(배기), BME688 #2 0x76(흡기), LCD 0x27
constexpr int PIN_I2C_SDA = 21;
constexpr int PIN_I2C_SCL = 22;

// ---- HX711 로드셀 앰프 (3.3V 동작)
constexpr int PIN_HX711_DT  = 16;
constexpr int PIN_HX711_SCK = 17;

// ---- 출력
constexpr int PIN_HEATER_PWM   = 25;  // D4184 #1 → PTC 80W (LEDC 1kHz)
constexpr int PIN_FAN_CIRC_PWM = 26;  // 60mm 순환팬 4핀 PWM (운전 중 60~100%)
constexpr int PIN_FAN_IN_PWM   = 27;  // 40mm 흡기팬 PWM = 환기량 = 습도 조절
constexpr int PIN_LED          = 32;  // D4184 #2 → LED 스트립 ON/OFF
constexpr int PIN_BUZZER       = 33;  // 패시브 부저

// ---- DS18B20 OneWire (플레넘. 2차 냉각핀 2개도 같은 버스)
constexpr int PIN_ONEWIRE = 4;

// ---- 버튼 ▲ ▼ 선택 (INPUT_PULLUP. 34~39는 내부 풀업 없음 → 쓰지 말 것)
constexpr int PIN_BTN_UP     = 13;
constexpr int PIN_BTN_DOWN   = 14;
constexpr int PIN_BTN_SELECT = 15;

// ---- 마이크로SD (SPI, CSV 로그)
constexpr int PIN_SD_SCK  = 18;
constexpr int PIN_SD_MISO = 19;
constexpr int PIN_SD_MOSI = 23;
constexpr int PIN_SD_CS   = 5;

// ---- [2차] 펠티어 MOSFET (12는 부팅 중 LOW 유지: 모듈 풀다운 OK)
constexpr int PIN_PELTIER1 = 2;
constexpr int PIN_PELTIER2 = 12;

// 쓰지 않는 핀: GPIO0(부팅), GPIO6~11(플래시), GPIO34~39(입력 전용, 풀업 없음)
