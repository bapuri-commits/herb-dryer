# ESP32 핀맵

BOM `핀맵(ESP32)` 시트와 같은 내용. 코드는 [`firmware/include/pins.h`](../firmware/include/pins.h).
**바꿀 때는 이 문서, BOM 시트, `pins.h` 세 곳을 같은 PR에서 함께 바꾼다.**

보드: ESP32 DevKitC V4 (WROOM-32D, 38핀) + 38핀 확장보드

| 핀 | 연결 | 비고 |
|---|---|---|
| GPIO21 / 22 | I2C SDA / SCL | TCS34725 0x29 · SHT31 0x44 · BME688 #1 0x77(배기) · BME688 #2 0x76(흡기, P2 헤더 SDO→GND) · LCD 0x27. 주소 변경 불가 시 TCA9548A |
| GPIO16 / 17 | HX711 DT / SCK | 3.3V 동작 OK |
| GPIO25 | 히터 MOSFET PWM | DFR0457 #1 → PTC 50W (LEDC 1kHz, 켤 때 2~3초 소프트 스타트) |
| GPIO26 | 순환팬 60mm PWM | 4핀 팬 PWM선 직결, 운전 중 60~100% |
| GPIO27 | 흡기팬 40mm PWM | PWM = 환기량 = 습도 조절. **최대 30%** (100%면 바깥 공기 데우는 데만 ~90W, 50W 히터로 못 따라감) |
| GPIO32 | LED 스트립 ON/OFF | DFR0457 #2 |
| GPIO33 | 부저 | |
| GPIO4 | DS18B20 OneWire | 플레넘 1차, 2차 냉각핀 2개 공유 |
| GPIO13 / 14 / 15 | 버튼 ▲ ▼ 선택 | INPUT_PULLUP (34~39는 풀업 없음, 쓰지 말 것) |
| GPIO18 / 19 / 23 / 5 | 마이크로SD SPI (SCK/MISO/MOSI/CS) | CSV 로그 |
| GPIO2 / 12 | [2차] 펠티어 1 / 2 MOSFET | 12는 부팅 중 LOW 유지(모듈 풀다운 OK) |
| 내장 BT/Wi-Fi | 폰 로깅·모니터링 | BluetoothSerial 또는 Wi-Fi 웹페이지. HC-06 불필요 |
| 5V(VIN) | MP1584 5.0V 출력 | USB 동시 연결 시 USB 뽑고 공급 |
| 3V3 | 센서 전원 (TCS·SHT31·BME688×2·HX711) | LCD만 5V |
| — | 쓰지 않는 핀 | GPIO0(부팅), GPIO6~11(플래시), GPIO34~39(입력 전용, 풀업 없음) |
