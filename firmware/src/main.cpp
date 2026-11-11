// herb-dryer 첫 브레드보드 테스트: I2C 스캔만 한다.
// 기대 주소: 0x27 LCD, 0x44 SHT31, 0x76 BME688 #2, 0x77 BME688 #1 (v3.1: TCS34725 삭제)
#include <Arduino.h>
#include <Wire.h>
#include "pins.h"

struct Known { uint8_t addr; const char *name; };
static const Known KNOWN[] = {
    {0x27, "LCD1602 I2C"}, {0x44, "SHT31"},
    {0x76, "BME688 #2 (흡기)"}, {0x77, "BME688 #1 (전실)"},
};

static const char *nameOf(uint8_t a) {
  for (const auto &k : KNOWN) if (k.addr == a) return k.name;
  return "?";
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  Serial.printf("\nherb-dryer I2C scan (SDA=%d, SCL=%d)\n", PIN_I2C_SDA, PIN_I2C_SCL);
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
  delay(3000);
}
