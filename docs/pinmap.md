# ESP32 핀맵

BOM `핀맵(ESP32)` 시트와 같은 내용. 코드는 [`firmware/include/pins.h`](../firmware/include/pins.h).
**바꿀 때는 이 문서, BOM 시트, `pins.h` 세 곳을 같은 PR에서 함께 바꾼다.**

보드: ESP32 DevKitC V4 (WROOM-32D, 38핀) + 38핀 확장보드

| 핀 | 연결 | 비고 |
|---|---|---|
| GPIO21 / 22 | I2C SDA / SCL, 100kHz | 메인: SHT31 0x44 · DFR0576(TCA9548A) 0x70. 먹스 채널: ch0 BME688 #1 0x77(전실) · ch1 BME688 #2 0x77(흡기) · ch2 LCD 0x27. DFR0576 VCC = 3V3(5V 금지). LCD VCC는 5V(MP1584), LCD SDA·SCL·GND만 ch2 (v3.6.0). SDA·SCL을 GND와 꼬아 히터선과 다른 관통구로 |
| GPIO16 / 17 | HX711 DT / SCK | 3.3V 동작 OK |
| GPIO25 | 히터 PWM | DFR0457 #1 → PTC 100W (LEDC 1kHz, **최대 80%**, 켤 때 2~3초 소프트 스타트) |
| GPIO26 | 순환팬 60mm PWM | 4핀 팬 PWM선 직결, 운전 중 60~100% |
| GPIO27 | 흡기팬 40mm PWM | PWM = 환기량 = 습도 조절. **최대 30%** (100%면 바깥 공기 데우는 데만 ~90W). 10kΩ 직렬, #3으로 전원 끊기 전 입력으로 전환 |
| GPIO2 | 흡기팬 전원 차단 | DFR0457 #3 (PWM 0%에서도 도는 팬을 완전히 멈춤). 부팅핀 — 모듈을 연결한 채 업로드되는지 확인 |
| GPIO32 | 비움 | v3.1 LED 삭제 (DFR0457 #2 삭제) |
| GPIO34 / 35 | 순환팬 / 흡기팬 타코 | 입력 전용·풀업 없음 → 10kΩ를 3.3V로. 순환팬이 멈추면 히터 차단. 흡기팬 타코(35)는 10kΩ 직렬 추가 |
| GPIO33 | 비움 | v3.1 부저 삭제 |
| GPIO4 | DS18B20 OneWire | 플레넘 온도 |
| GPIO13 / 14 / 15 | 버튼 ▲ ▼ 선택 | INPUT_PULLUP. 15는 부팅핀이지만 평소 열린 버튼이라 OK |
| GPIO18 / 19 / 23 / 5 | 마이크로SD SPI (SCK/MISO/MOSI/CS) | CSV 로그 (회차 번호 + 경과 시간, 날짜는 수기) |
| GPIO12 | 비움 | 플래시 전압 선택 부팅핀 — 쓰지 않는다 |
| 5V(VIN) | MP1584 5.0V 출력 | USB 동시 연결 시 USB 뽑고 공급 |
| 3V3 | 센서 전원 (SHT31·BME688×2·HX711·DFR0576) | LCD만 5V (백팩 5V 풀업은 DFR0576 ch2가 메인 버스와 분리) |
| — | 쓰지 않는 것 | 블루투스·Wi-Fi(v3.0에서 제거), RTC 없음. GPIO0(부팅), GPIO6~11(플래시), GPIO36/39 |
