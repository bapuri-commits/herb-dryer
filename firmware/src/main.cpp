// herb-dryer 첫 브레드보드 테스트: I2C 스캔만 한다 (5초마다, 100kHz).
// v3.1 기대 주소: 0x27 LCD, 0x44 SHT31, 0x76 BME688 #2, 0x77 BME688 #1
#include <Arduino.h>
#include <Wire.h>
#include "pins.h"

struct Known { uint8_t addr; const char *name; };
static const Known KNOWN[] = {
    {0x27, "LCD1602 I2C 백팩 (PCF8574)"},
    {0x3F, "LCD1602 I2C 백팩 (PCF8574A)"},
    {0x44, "SHT31"},
    {0x45, "SHT31 (ADDR=HIGH)"},
    {0x76, "BME688 #2 (흡기, SDO=GND)"},
    {0x77, "BME688 #1 (전실)"},
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

void loop() {
  int found = 0;
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.printf("  0x%02X  %s\n", a, nameOf(a));
      found++;
    }
  }
  Serial.printf("found %d device(s)\n\n", found);
  delay(5000);
}
