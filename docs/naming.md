# CAD 바디 이름 규칙

STEP·도면·STL·이슈에서 부품을 부를 때 이 이름을 쓴다. Fusion에서 STEP을 열면 브라우저 트리에 같은 이름으로 보인다.

형식: `<접두어><번호>_<설명>[_<재료·치수>]` — 예: `P02_front_foamex5T`, `H02_heater_duct_PETG`

| 접두어 | 분류 | 예 |
|---|---|---|
| **P** | 포맥스판 (외판·칸막이·받침 턱) | `P01_side_L_foamex5T`, `P04_duct_partition_wall_foamex5T`, `P06_bottom_plate_foamex5T` |
| **F** | 단열 폼 | `F01_foam_bottom_270x270`, `F05_phase1_peltier_plug_foam_1` |
| **A** | 알루미늄 (라이너 0.5T, 타공판·차폐판·배플 1T) | `A04_liner_ch_L_270x171.5`, `A10_perforated_floor_Al1T` |
| **B** | 블록 (너트블록·코너블록, 3D 프린트) | `B01_nut_block_bottom_L_30`, `B02_corner_block_top_10_10` |
| **D** | 문 (바깥판, 플러그, 가스켓, 자석, 경첩) | `D01_door_outer_foamex5T`, `D06_hinge_25mm_1` |
| **E** | 전장 (ESP32, 캐리어, 모듈, 터미널, LCD, 버튼, 잭) | `E01_ESP32_38pin_expansion_board`, `E03_module_carrier_PETG_66x148` |
| **H** | 히터 (60mm 순환팬, 히터 덕트, PTC, 서모스탯) | `H02_heater_duct_PETG`, `H03_PTC_fin_12V_80W` |
| **I** | 흡기 (흡기 박스, 40mm 팬, 활성탄, BME688 #2) | `I01_intake_box_PETG`, `I02_fan_40mm_intake_PWM` |
| **L** | 로드셀 (블록, 로드셀, 받침판) | `L01_loadcell_base_block`, `L02_loadcell_1kg_bar` |
| **T** | 트레이 | `T01_tray_frame_245x215_PETG`, `T02_tray_mesh_241x211` |
| **S** | 천장 센서 (센서 인서트, TCS34725, LED, 배기 플랩) | `S01_sensor_insert_PETG_100x100`, `S05_exhaust_flap_PET0.3` |
| **C** | 챔버 센서 (SHT31·BME688 #1 홀더, 케이블 클립) | `C01_SHT31_holder_PETG_5mm`, `C05_cable_clip_1` |
| **X_P2** | 2차 (펠티어, `phase=2`, 참조용) | `X_P2_TEC1-12706_1`, `X_P2_fan_120mm` |

## Fusion 브라우저 폴더 (STEP 어셈블리 그룹)

STEP은 아래 그룹 안에 부품이 들어간 2단 구조로 저장된다 (`cad/herb_dryer_cad.py`의 `GROUPS`).
Fusion에서 열면 그룹이 하위 컴포넌트(폴더처럼 접히는 항목)로 보인다. 그룹 이름은 STEP 호환을 위해 영문이다.

| 그룹 | 들어가는 부품 | 담당 |
|---|---|---|
| `01_shell_foamex` | P01·P02·P03·P06·P07 외판, B 블록 | 외함 |
| `02_insulation_foam` | F 단열 폼, 펠티어 막음 폼 | 외함 |
| `03_liner_Al` | A01~A07 라이너 | 외함 |
| `04_partition_floor` | P04 칸막이 벽, P05 받침 턱, A10 타공판, A12·A13 배플 | 외함 |
| `05_door` | D 문 | 외함 |
| `06_heater` | H 순환팬·덕트·PTC·서모스탯 | 전장 |
| `07_intake` | I 흡기 박스 | 기구·전장 |
| `08_electronics` | E 전장 전부 | 전장 |
| `09_loadcell_tray` | L 로드셀, A11 차폐판, T 트레이 | 기구 |
| `10_sensors_ceiling` | S 천장 센서 인서트·플랩 | 기구 |
| `11_sensors_chamber` | C 챔버 센서 홀더·클립 | 기구 |
| `90_fasteners` | 모든 볼트·너트·스탠드오프·스페이서 | — |
| `99_phase2_peltier` | 2차 부품 (`phase=2`) | — |

- 새 부품의 그룹은 접두어로 자동으로 정해진다. 새 접두어를 만들면 `GROUPS`에 한 줄 추가한다.
- 체결부품을 한 그룹에 모아 둔 이유: Fusion에서 `90_fasteners`의 눈 아이콘 하나로 볼트를 전부 숨기려고.

## 체결부품 이름

볼트·너트·스탠드오프는 붙는 부품의 접두어 뒤에 `_bolt_`, `_nut_`, `_so_`를 붙인다
(예: `E01_so_0`, `E01_bolt_0`, `D_hinge_bolt_0_1`, `C_nut_SHT31`). 수량은 `build/fasteners.csv`에서 자동 집계된다.

## 메타데이터 (CAD 스크립트의 `add()`)

| 필드 | 뜻 |
|---|---|
| `mat` | 재료 (포맥스 5T, PETG, …) |
| `proc` | 가공: `재단`, `재단+타공`, `재단+절곡`, `3D프린트` → `3D프린트`는 STL로 나간다 |
| `phase` | 1 = 1차, 2 = 2차(펠티어). 1차↔2차 사이 간섭은 검사하지 않는다 |
| `kind` | `part`(만드는 것), `buy`(사는 것), `fastener`(체결부품) |

## 새 부품 추가할 때

- 같은 분류의 다음 번호를 쓴다 (`H06_…`). 기존 번호는 바꾸지 않는다 (이슈·실물 기록이 깨짐)
- 삭제한 번호는 다시 쓰지 않는다
- 판재 도면 대상은 `cad/tools/drawings.py`의 `FLAT_PREFIX`·`TITLE`에도 추가
