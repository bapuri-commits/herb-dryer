// herb-dryer 첫 브레드보드 테스트: I2C 스캔만 한다 (5초마다, 100kHz).
// v3.6.0 기대 구성: 메인 0x44 SHT31 · 0x70 DFR0576(TCA9548A)
//                  먹스 ch0 0x77 BME688 #1, ch1 0x77 BME688 #2, ch2 0x27 LCD
#include <Arduino.h>
#include <Wire.h>
#include "pins.h"

struct Known { uint8_t addr; const char *name; };
static const Known KNOWN[] = {
    {0x27, "LCD1602 I2C 백팩 (PCF8574)"},
    {0x3F, "LCD1602 I2C 백팩 (PCF8574A)"},
    {0x44, "SHT31"},
    {0x45, "SHT31 (ADDR=HIGH)"},
    {0x70, "DFR0576 I2C 멀티플렉서 (TCA9548A)"},
    {0x77, "BME688 (#1 = ch0 전실, #2 = ch1 흡기)"},
    {0x29, "TCS34725 (v3.1에서 삭제된 부품)"},
};

static const char *nameOf(uint8_t a) {
  for (const auto &k : KNOWN) if (k.addr == a) return k.name;
  return "?";
}

void setup() {
  // 전력 출력은 가장 먼저 LOW: 부팅 중 히터·팬이 켜지지 않게
  const int outputs[] = {PIN_HEATER_PWM, PIN_FAN_CIRC_PWM, PIN_FAN_IN_PWM, PIN_FAN_IN_POWER};
  for (int p : outputs) {
    digitalWrite(p, LOW);
    pinMode(p, OUTPUT);
  }

  Serial.begin(115200);
  delay(500);
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL, I2C_FREQ_HZ);
  Serial.printf("\nherb-dryer I2C scan (SDA=%d, SCL=%d, %lu Hz)\n",
                PIN_I2C_SDA, PIN_I2C_SCL, (unsigned long)I2C_FREQ_HZ);
}

static bool muxSelect(uint8_t mask) {   // 비트마스크로 채널 열기 (0 = 모두 닫기)
  Wire.beginTransmission(I2C_MUX_ADDR);
  Wire.write(mask);
  return Wire.endTransmission() == 0;
}

static int scanBus(bool skipMux) {
  int found = 0;
  for (uint8_t a = 1; a < 127; a++) {
    if (skipMux && a == I2C_MUX_ADDR) continue;
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  0x%02X  %s\n", a, nameOf(a));
      found++;
    }
  }
  return found;
}

void loop() {
  Serial.println("[main]");
  int found = scanBus(false);
  if (muxSelect(0)) {                     // 0x70 응답 = 먹스 있음 → 채널마다 스캔
    for (uint8_t ch = 0; ch < 8; ch++) {
      muxSelect(1 << ch);
      Serial.printf("[mux ch%u]\n", ch);
      found += scanBus(true);
    }
    muxSelect(0);                         // 끝나면 모든 채널 닫기
  } else {
    Serial.println("  (DFR0576 0x70 없음 → 채널 스캔 생략)");
  }
  Serial.printf("found %d device(s)\n\n", found);
  delay(5000);
}
