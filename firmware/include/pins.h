// herb-dryer ESP32 핀맵 — docs/pinmap.md 와 같은 내용 (BOM "핀맵(ESP32)" 시트 원본)
// 바꿀 때는 docs/pinmap.md, BOM 시트, 이 파일 세 곳을 같은 PR에서 함께 바꾼다.
// v3.0: 블루투스·Wi-Fi·RTC 없음, 펠티어 설계에서 완전히 제외. v3.1: TCS34725·LED·부저 삭제
//
// 부팅(스트래핑) 핀 주의 — 리셋 순간의 전압으로 부팅 모드가 정해진다:
//   GPIO0  : LOW면 다운로드 모드. 쓰지 않는다 (BOOT 버튼 전용).
//   GPIO2  : 다운로드 모드 진입 시 LOW 또는 플로팅이어야 한다. 흡기팬 전원 MOSFET이 물려 있으니
//            모듈을 연결한 채 업로드가 되는지 꼭 확인할 것.
//   GPIO12 : 플래시 전압 선택(MTDI). 부팅 때 HIGH면 1.8V로 잡혀 부팅 실패. 아무것도 연결하지 않는다.
//   GPIO15 : 부팅 로그 출력 여부(MTDO). LOW면 부팅 로그가 안 나올 뿐 동작은 정상.
//   GPIO5  : SDIO 타이밍 선택. SD CS로 써도 무방(평소 HIGH).
#pragma once
#include <stdint.h>

// ---- I2C (50~100kHz): SHT31 0x44, BME688 #1 0x77(전실), BME688 #2 0x76(흡기, P2 헤더 SDO→GND, 안 되면 TCA9548A), LCD 0x27
constexpr int PIN_I2C_SDA = 21;  // I2C 데이터
constexpr int PIN_I2C_SCL = 22;  // I2C 클럭
constexpr uint32_t I2C_FREQ_HZ = 100000;  // 배선이 길고 히터선 근처라 100kHz 이하

// ---- HX711 로드셀 앰프 (3.3V 동작)
constexpr int PIN_HX711_DT  = 16;  // HX711 데이터 출력
constexpr int PIN_HX711_SCK = 17;  // HX711 클럭

// ---- 출력 (setup() 맨 앞에서 LOW로 둔다)
constexpr int PIN_HEATER_PWM   = 25;  // DFR0457 #1 → PTC 100W (LEDC 1kHz, 켤 때 2~3초 소프트 스타트)
constexpr int HEATER_MAX_DUTY_PCT = 80;  // 100W × 80% (10A 어댑터·퓨즈 여유)
constexpr int PIN_FAN_CIRC_PWM = 26;  // 60mm 순환팬 4핀 PWM (운전 중 60~100%)
constexpr int PIN_FAN_IN_PWM   = 27;  // 40mm 흡기팬 PWM = 환기량 = 습도 조절 (10kΩ 직렬)
constexpr int FAN_IN_MAX_DUTY_PCT = 30;  // 100%면 바깥 공기 데우는 데 ~90W
constexpr int PIN_FAN_IN_POWER = 2;   // DFR0457 #3 → 흡기팬 12V 차단 (부팅핀: 위 주의 참고)
                                      // 끊기 전에 PIN_FAN_IN_PWM 을 INPUT으로 (PWM·타코선 10kΩ 직렬)

// ---- 팬 타코 (입력 전용 핀, 내부 풀업 없음 → 10kΩ 를 3.3V로)
constexpr int PIN_FAN_CIRC_TACH = 34;  // 순환팬 회전 감지 — 멈추면 히터 차단
constexpr int PIN_FAN_IN_TACH   = 35;  // 흡기팬 회전 감지 (10kΩ 직렬)

// ---- 소프트 한계
constexpr float PLENUM_MAX_C = 58.0f;  // DS18B20 플레넘 온도 상한 (하드웨어 서모스탯 65°C 전)

// ---- DS18B20 OneWire (플레넘)
constexpr int PIN_ONEWIRE = 4;  // DS18B20 데이터 (4.7kΩ 풀업)

// ---- 버튼 ▲ ▼ 선택 (INPUT_PULLUP, 누르면 LOW)
constexpr int PIN_BTN_UP     = 13;  // ▲
constexpr int PIN_BTN_DOWN   = 14;  // ▼
constexpr int PIN_BTN_SELECT = 15;  // 선택 (부팅핀이지만 평소 열린 버튼이라 OK)

// ---- 마이크로SD (SPI, CSV 로그)
constexpr int PIN_SD_SCK  = 18;  // SPI 클럭
constexpr int PIN_SD_MISO = 19;  // SPI MISO
constexpr int PIN_SD_MOSI = 23;  // SPI MOSI
constexpr int PIN_SD_CS   = 5;   // SD 칩 선택

// ---- 쓰지 않는 핀
// GPIO12 : 비워 둔다 (플래시 전압 부팅핀). 예전 펠티어 배정은 설계에서 빠졌다.
// GPIO32 : 비움 (v3.1 LED 삭제)      GPIO33 : 비움 (v3.1 부저 삭제)
// GPIO0(부팅), GPIO6~11(내부 플래시), GPIO36/39(입력 전용, 미사용)
