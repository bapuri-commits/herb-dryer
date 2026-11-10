# herb-dryer — ESP32 허브(스피어민트) 건조기

대학 컴퓨터공학과 팀 프로젝트. 하드웨어 설계의 원본은 **CadQuery 스크립트 하나**([`cad/herb_dryer_cad.py`](cad/herb_dryer_cad.py))이고,
여기서 STEP·가공 도면·STL이 만들어진다. 버전은 git 태그(`v2.9.0`)로 관리한다.

**📦 파일은 [최신 Release](https://github.com/bapuri-commits/herb-dryer/releases/latest)에서 받는다** (STEP, 구멍표 PDF, 1:1 인쇄 PDF, DXF, STL, 렌더, BOM). 레포를 직접 실행할 필요는 없다.

## 한 장 요약

- **외형** 300 × 300 × 270 mm (W×D×H). 포맥스 5T 외판 + 단열 폼 10T + 알루미늄 0.5T 라이너
- **위 = 건조 챔버**: 타공판(z80) 위에 로드셀 트레이(245×215). 천장에 컬러센서(TCS34725)·LED, 왼벽 SHT31, 덕트 뒷벽 BME688 #1
- **아래 = 전장부** (높이 65): ESP32 + 모듈 캐리어, 히터 덕트
- **순환 구조**: 덕트·칸막이 벽(P04) 한 장이 전장부를 **플레넘(앞)** 과 **복귀실(뒤)** 로 나눈다.
  60mm 순환팬이 복귀실 공기를 빨아 PTC 80W 덕트를 거쳐 플레넘으로 밀고 → 타공판 → 챔버 → 덕트 벽 뒤로 내려와 복귀실로.
  앞판 40mm 흡기팬(활성탄 + BME688 #2)으로 바깥 공기를 들이고, 천장 뒤 무동력 플랩으로 내보낸다 (흡기 PWM = 환기량 = 습도 조절)
- **1차 / 2차**: 1차는 PTC 히터 건조. 2차(`phase=2`, `X_P2_*`)는 뒷판 펠티어 2개 제습 — 1차에서는 폼으로 구멍을 막아 둔다

## 처음 온 사람이 읽는 순서

1. [CHANGELOG.md](CHANGELOG.md) — 지금 버전, 무엇이 왜 바뀌었는지, 다시 만들어야 할 부품
2. 최신 Release의 **렌더 이미지** (`…_r1_exterior.png` 외관, `r2_cutaway` 내부, `r5/r6_section` 단면)
3. **Fusion에서 STEP 열기**: Release의 `herb_dryer_vX.Y.Z.step`을 Fusion에서 File → Open → Open from my computer (또는 Data 패널 Upload). 부품 이름은 아래 접두어 표
4. [`cad/params.yaml`](cad/params.yaml) — 아직 **가정**인 치수와 실측된 치수
5. **구멍표 PDF** (`…_holes.pdf`) — 판마다 구멍 좌표. 재단할 땐 `…_print_1to1.pdf`를 100%로 인쇄

## CAD 바디 접두어

| 접두어 | 분류 | 접두어 | 분류 |
|---|---|---|---|
| **P** | 포맥스판 | **I** | 흡기 |
| **F** | 폼 | **L** | 로드셀 |
| **A** | 알루미늄 | **T** | 트레이 |
| **B** | 블록 | **S** | 천장 센서 |
| **D** | 문 | **C** | 챔버 센서 |
| **E** | 전장 | **X_P2** | 2차 |
| **H** | 히터 | | |

자세한 규칙: [docs/naming.md](docs/naming.md)

## 변경 요청 절차

```
이슈 ──▶ 통합 담당이 PR ──▶ CI (빌드 + 간섭 검사) ──▶ 병합 ──▶ 태그 ──▶ Release
```

- CAD·BOM은 **통합 담당 한 명만** 고친다. 나머지는 [이슈 양식](https://github.com/bapuri-commits/herb-dryer/issues/new/choose)으로 요청한다: `CAD 변경 요청` / `실측 결과` / `부품 구매·확정`
- 실측 반영은 `params.yaml`만 바꾸는 PR → **패치** 버전 (`v2.9.1`). 형상이 바뀌면 **마이너** (`v2.10.0`)
- **만든 실물에 버전을 남긴다**: STL 파일 이름에 버전이 있고, 재단한 판은 뒷면에 연필로 `P02 v2.9.0`
- 자세히: [docs/workflow.md](docs/workflow.md) · 핀맵: [docs/pinmap.md](docs/pinmap.md) · 실측 기록: [docs/measurements/](docs/measurements/)

## 로컬 빌드 (통합 담당용)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                          # cadquery 2.8, ezdxf, matplotlib, openpyxl, pyvista, vtk
python build.py          # 또는 make all
```

`build/`에 생긴다 (git에는 안 올라감):

| 파일 | 내용 |
|---|---|
| `herb_dryer.step` | 전체 조립 STEP |
| `interference.txt` | 간섭 검사. **1건이라도 있으면 빌드 실패** (1차↔2차 제외) |
| `drawings/` | `herb_dryer_holes.pdf` 구멍표, `herb_dryer_print_1to1.pdf` 1:1 인쇄, `dxf/` |
| `stl/` | 3D 프린트 부품 28개, 파일 이름에 버전 |
| `render/` | 외관·내부·단면 PNG (리눅스 서버는 `xvfb-run python build.py`) |
| `fasteners.csv`, `print_parts.csv` | 체결부품 수량, 3D 프린트 목록 |
| `bom_csv/` | BOM 시트별 CSV |

단계별: `python build.py step check`. 한글 폰트는 Noto Sans CJK → 나눔고딕/맑은 고딕 순으로 찾고, `HERB_FONT=<경로>`로 지정할 수 있다.
리팩터링 검증: `python cad/tools/compare_step.py 옛.step build/herb_dryer.step`

펌웨어: `firmware/` (PlatformIO, `esp32dev`). `pio run -d firmware -t upload` — 지금은 I2C 스캔만 한다.

## 레포 관리자가 직접 할 설정

- **main 브랜치 보호**: Settings → Branches → Add rule(`main`) → *Require a pull request* + *Require review from Code Owners* + *Require status checks*: `cad-build`, `firmware-build`. ([자세히](docs/workflow.md#main-브랜치-보호-설정-레포-관리자가-한-번))
- **CODEOWNERS**: 통합 담당이 정해지면 [`.github/CODEOWNERS`](.github/CODEOWNERS)의 아이디를 바꾼다
- **팀원 초대**: Settings → Collaborators → Add people (Write 권한)
- **Projects 보드**: 프로필 → Projects → New project → *Board* → 이름 `herb-dryer` → 열(Status)을 아래 5개로 바꾸고, 레포 Projects 탭에서 연결. 이슈는 단계 열로 옮긴다
  1. 주문·측정 도구
  2. 병행 작업 (펌웨어 브레드보드 / 외함 외곽 재단 / 실측과 무관한 3D 프린트)
  3. 실측 → CAD 패치
  4. 상자 밖 히터 벤치 시험
  5. 조립·시운전
- **라벨**은 [`.github/labels.yml`](.github/labels.yml)에서 Actions가 자동으로 만든다 (분야: `cad` `외함` `3d프린트` `전장` `펌웨어` `구매` / 상태: `실측필요` `안전` `2차`)
