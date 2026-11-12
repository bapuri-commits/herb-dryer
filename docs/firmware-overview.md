# 펌웨어 구성 설명

`firmware/` 폴더에 무엇이 있고 왜 그렇게 정했는지 정리한 문서다.
설치·명령·업로드 문제 해결은 [`firmware/README.md`](../firmware/README.md), 핀 배정 원본은 [`pinmap.md`](pinmap.md)를 본다.

현재 단계: **I2C 스캔만 하는 첫 브레드보드 테스트**. 나머지는 팀 전원이 같은 환경에서 빌드하기 위한 설정과 문서다.

## 파일 구성

| 파일 | 역할 |
|---|---|
| [`platformio.ini`](../firmware/platformio.ini) | 빌드 환경 (보드, 코어 버전, 라이브러리) |
| [`include/pins.h`](../firmware/include/pins.h) | 핀 배정과 안전 한계값 상수 |
| [`src/main.cpp`](../firmware/src/main.cpp) | I2C 스캐너 (첫 테스트) |
| [`README.md`](../firmware/README.md) | 설치, 명령, 업로드 체크리스트 |
| `.gitignore` | `.pio/` 빌드 산출물과 개인 VS Code 설정 제외, 확장 추천만 공유 |
| `.vscode/extensions.json` | 폴더를 열면 PlatformIO 확장 설치를 추천 |

## 1. platformio.ini — 빌드 환경

- **보드**: `esp32dev` (ESP32 DevKitC V4, WROOM-32D)
- **플랫폼 고정**: `espressif32@6.13.0` → Arduino-ESP32 코어 **2.0.17** (ESP-IDF 4.4 기반)
- **시리얼**: 모니터 115200, 업로드 921600. 업로드가 불안정하면 460800으로 낮춰 시험하되 커밋하지 않는다.
- **`-Wall`**: 컴파일 경고를 모두 켠다.

### 왜 버전을 고정하나 — LEDC(PWM) 문법

코어 2.x와 3.x는 PWM API가 다르다. 인터넷 예제를 그대로 가져오면 가장 흔히 걸리는 함정이다.

| 코어 | 문법 |
|---|---|
| 2.x (우리) | `ledcSetup(ch, freq, bits)` → `ledcAttachPin(pin, ch)` → `ledcWrite(ch, duty)` |
| 3.x | `ledcAttach(pin, freq, bits)` → `ledcWrite(pin, duty)` — 이 코어에서 컴파일되지 않음 |

3.x로 올리려면 `espressif32` 8.x가 필요하다. 팀 합의 후 `platformio.ini`와 LEDC 코드를 같은 PR에서 바꾼다.

### 라이브러리 (`lib_deps`)

모두 정확한 버전으로 고정하고, 간접 의존성(BusIO, Unified Sensor)도 고정한다.

| 라이브러리 | 버전 | 부품 |
|---|---|---|
| Adafruit SHT31 | 2.2.2 | 온습도 SHT31 |
| Adafruit BME680 | 2.0.6 | BME688 ×2 (BME680 호환, 가스 히터 프로파일은 기본 기능만) |
| bogde/HX711 | 0.7.5 | 로드셀 앰프 |
| OneWire | 2.3.8 | DS18B20 버스 |
| DallasTemperature | 4.0.6 | DS18B20 |
| LiquidCrystal_I2C | 1.1.4 | LCD1602 I2C 백팩 |
| Adafruit BusIO | 1.17.4 | (의존성) |
| Adafruit Unified Sensor | 1.1.15 | (의존성) |

Wire·SPI·SD는 코어 내장이라 넣지 않는다.

## 2. pins.h — 핀맵과 안전값

[`pinmap.md`](pinmap.md)·BOM `핀맵(ESP32)` 시트를 코드로 옮긴 것이다. **바꿀 때는 세 곳을 같은 PR에서 함께 바꾼다.**

| 그룹 | 핀 | 비고 |
|---|---|---|
| I2C | SDA 21, SCL 22, 100kHz | 배선이 길고 히터선 근처라 속도를 낮춤 |
| HX711 | DT 16, SCK 17 | 로드셀 |
| 히터 PWM | 25 | PTC 100W, **최대 듀티 80%** (어댑터·퓨즈 여유) |
| 순환팬 PWM | 26 | 60mm 4핀 팬, 운전 중 60~100% |
| 흡기팬 PWM | 27 | 환기량 = 습도 조절, **최대 30%** (바깥 공기 가열 전력 제한) |
| 흡기팬 전원 | 2 | MOSFET으로 12V 차단. 차단 전에 27번을 INPUT으로 전환 |
| 팬 타코 | 34 순환, 35 흡기 | 입력 전용·내부 풀업 없음 → 10kΩ를 3.3V로. 순환팬이 멈추면 히터 차단 |
| DS18B20 | 4 | 플레넘 온도. 소프트 상한 **58°C** (하드웨어 서모스탯 65°C보다 먼저) |
| 버튼 | 13 ▲, 14 ▼, 15 선택 | INPUT_PULLUP, 누르면 LOW |
| microSD | SCK 18, MISO 19, MOSI 23, CS 5 | CSV 로그 |

### 부팅(스트래핑) 핀

리셋 순간의 전압으로 부팅 모드가 정해지는 핀들이다.

| 핀 | 주의 |
|---|---|
| GPIO0 | LOW면 다운로드 모드. 쓰지 않는다 (BOOT 버튼 전용) |
| GPIO2 | 다운로드 모드 진입 시 LOW 또는 플로팅이어야 한다. 흡기팬 MOSFET이 물려 있으니 **모듈을 연결한 채 업로드되는지 확인** |
| GPIO12 | 부팅 때 HIGH면 플래시 전압이 1.8V로 잡혀 부팅 실패. **아무것도 연결하지 않는다** |
| GPIO15 | LOW면 부팅 로그만 안 나오고 동작은 정상. 평소 열린 버튼이라 OK |
| GPIO5 | SDIO 타이밍 선택. SD CS(평소 HIGH)로 써도 무방 |

### 설계 이력

- v3.0: 블루투스·Wi-Fi·RTC 없음, 펠티어 완전히 제외
- v3.1: TCS34725 컬러센서, LED(GPIO32), 부저(GPIO33) 삭제

## 3. main.cpp — I2C 스캐너

센서 배선을 처음 확인하기 위한 코드다.

1. **`setup()` 맨 앞에서 히터·팬 출력 4개(25, 26, 27, 2)를 LOW로 고정**한다.
   `pinMode(OUTPUT)`보다 `digitalWrite(LOW)`를 먼저 호출해, 출력으로 바뀌는 순간에도 HIGH가 튀지 않게 한다. 부팅 중 히터가 켜지는 사고를 막는다.
2. 시리얼 115200, I2C를 21/22번 핀·100kHz로 시작한다.
3. `loop()`는 5초마다 주소 0x01~0x7E를 훑고, 아는 주소면 부품 이름을 함께 출력한다.

### 기대 결과

```
  0x27  LCD1602 I2C 백팩 (PCF8574)
  0x44  SHT31
  0x76  BME688 #2 (흡기, SDO=GND)
  0x77  BME688 #1 (전실)
found 4 device(s)
```

| 증상 | 확인 |
|---|---|
| LCD가 0x3F로 나옴 | PCF8574A 칩 백팩. 코드에서 주소만 바꾸면 된다 |
| SHT31이 0x45로 나옴 | ADDR 핀이 HIGH |
| BME688이 하나만 나옴 (0x77) | 흡기 쪽 P2 헤더 SDO→GND 확인. 안 되면 TCA9548A 멀티플렉서 |
| 0x29가 나옴 | v3.1에서 삭제된 TCS34725가 아직 연결됨 |
| 아무것도 안 나옴 | SDA/SCL 바뀜, 풀업, 3.3V/GND 배선 |

## 4. README.md

- 설치: VS Code + PlatformIO, `pio` PATH 설정, CP210x 드라이버
- VS Code에서는 레포 루트가 아니라 **`firmware/` 폴더를 직접 연다**
- 명령: `pio run`, `pio run -t upload`, `pio device monitor`, `pio device list`
- **업로드할 때는 12V 전원(히터·팬)을 빼고 USB만 연결한다**
- 업로드 실패 체크리스트: 데이터 케이블, 드라이버, BOOT 버튼, GPIO12·GPIO2, 업로드 속도, 포트 점유
