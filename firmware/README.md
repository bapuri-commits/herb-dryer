# herb-dryer 펌웨어

ESP32 DevKitC V4 (WROOM-32D) · PlatformIO · Arduino-ESP32 코어 **2.0.17** (`espressif32@6.13.0`)
핀 배정은 [`docs/pinmap.md`](../docs/pinmap.md) → [`include/pins.h`](include/pins.h).

## 설치

1. **VS Code** + **PlatformIO IDE** 확장 (이 폴더를 열면 설치를 추천한다). 첫 빌드 때 툴체인을 받느라 5분쯤 걸린다.
2. 터미널에서 `pio`를 쓰려면 PATH에 `%USERPROFILE%\.platformio\penv\Scripts` (macOS·Linux: `~/.platformio/penv/bin`) 추가.
3. **Windows**: 보드를 꽂아 장치 관리자 → 포트에 `Silicon Labs CP210x ... (COMx)`가 없으면
   [CP210x 드라이버](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers) 설치.

**VS Code에서는 `firmware/` 폴더를 직접 연다** (레포 루트를 열면 PlatformIO가 프로젝트를 못 찾는다).

## 명령 (`firmware/`에서)

```sh
pio run                 # 빌드
pio run -t upload       # 업로드
pio device monitor      # 시리얼 모니터 (115200, 종료 Ctrl+C)
pio device list         # 포트 확인
```

**업로드할 때는 12V 전원(히터·팬)을 빼고 USB만 연결한다.**

## 업로드가 안 될 때

- [ ] **데이터 케이블**인가? 충전 전용 케이블이면 `pio device list`에 아무것도 안 나온다
- [ ] **드라이버**: 장치 관리자에 CP210x COM 포트가 보이는가?
- [ ] `Connecting....____`에서 멈추면 **BOOT 버튼을 누른 채** 기다렸다가 `Writing`이 뜨면 뗀다
- [ ] **GPIO12에 아무것도 물리지 않았나?** (부팅 때 HIGH면 플래시 전압이 틀려 부팅 실패)
- [ ] GPIO2(흡기팬 전원 MOSFET)를 빼고 해 보기. 이 핀이 HIGH면 다운로드 모드로 못 들어간다
- [ ] 921600에서 오류가 나면 `platformio.ini`의 `upload_speed`를 `460800`으로 낮춰 시험 (커밋하지 말 것)
- [ ] 다른 프로그램(Arduino IDE 시리얼 모니터 등)이 포트를 잡고 있지 않은가?

## 버전 고정

플랫폼·라이브러리 버전은 `platformio.ini`에 정확히 고정한다. 올릴 때는 PR 하나로 올리고 팀에 알린다.
LEDC(PWM)는 코어 2.x 문법(`ledcSetup` / `ledcAttachPin` / `ledcWrite(채널, …)`)을 쓴다.
