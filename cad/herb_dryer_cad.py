"""
허브 건조기 v2.10 — 제작용 CadQuery 모델 (v2.10 변경은 CHANGELOG.md)
좌표: X=폭(좌→우), Y=깊이(앞=0 → 뒤=300), Z=높이(바닥=0). 단위 mm.

v2.8 → v2.9 주요 변경
- 순환 구조: 덕트 벽을 전장부 바닥까지 내려 '플레넘(앞)'과 '복귀실(뒤)'로 분리.
  60mm 순환팬은 칸막이에 달려 복귀실 공기를 빨아 PTC 덕트를 거쳐 플레넘으로 민다.
- 배기팬 삭제, 천장 뒤 무동력 플랩만. 1차 막음판(05b) 삭제.
- 흡기 박스(40mm 흡기팬 + 활성탄 + BME688 #2) 추가.
- 우노 → ESP32 DevKitC + 38핀 확장보드. 소형 모듈은 PETG 캐리어 판에.
- 전장부 높이 60 → 65 (60mm 팬 세워 설치). 앞문 개구부 276 → 260 (경첩·자석 자리).
- 판재를 재단표 단위로 분리, 모든 장착 구멍·체결부품(볼트·너트·스탠드오프) 모델링.

실측 후 수정할 값은 cad/params.yaml 에 있다 (value / status / source).
사지 않았거나 판매처마다 다른 부품. 이 스크립트는 시작할 때 params.yaml 을 읽는다.
버전은 파일 이름이 아니라 git 태그로 관리한다 (docs/workflow.md).

실행: python cad/herb_dryer_cad.py [출력폴더=build]
"""
import math
import os
from pathlib import Path
import cadquery as cq
import yaml

# ============================================================
# 0-a. [실측] 파라미터 읽기 (cad/params.yaml)
# ============================================================
PARAMS_PATH = Path(os.environ.get("HERB_PARAMS", Path(__file__).resolve().with_name("params.yaml")))
STATUSES = ("가정", "판매처 표기", "실측")

def load_params(path=PARAMS_PATH):
    """params.yaml → {그룹: {키: 값}}. status/source 검사도 한다."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    out, meta = {}, {}
    for grp, items in raw.items():
        out[grp], meta[grp] = {}, {}
        for k, v in items.items():
            if not isinstance(v, dict) or "value" not in v:
                continue                      # bom 등 설명용 키
            st, src = v.get("status"), v.get("source")
            if st not in STATUSES:
                raise ValueError(f"params.yaml {grp}.{k}: status '{st}' 는 {STATUSES} 중 하나여야 함")
            if st == "실측" and not src:
                raise ValueError(f"params.yaml {grp}.{k}: status 가 실측이면 source(측정자·날짜)가 필요함")
            val = v["value"]
            out[grp][k] = tuple(val) if isinstance(val, list) else val
            meta[grp][k] = dict(status=st, source=src)
    return out, meta

PARAMS, PARAMS_META = load_params()

# ============================================================
# 0. 파라미터
# ============================================================
OUT = 300            # 외형 폭·깊이
WALL = 5             # 포맥스 5T
INS = 10             # 단열 폼 10T
SKIN = WALL + INS    # 15
IN0, IN1 = SKIN, OUT - SKIN          # 15, 285
T05 = 0.5            # 알루미늄 라이너
WALL_H = 265         # 옆·앞·뒤판 높이
OZ = WALL_H + WALL   # 270 (천장판 포함)

BAY_Z0 = IN0         # 15  전장부 바닥(바닥 폼 윗면)
BAY_H = 65           # 전장부 높이 (v2.8: 60)
FLOOR_Z = BAY_Z0 + BAY_H   # 80  타공판 아랫면
FLOOR_T = 1.0              # 알루미늄 1T 타공판
FLOOR_TOP = FLOOR_Z + FLOOR_T   # 81
LINER_GAP = 2              # 챔버 라이너 하단을 타공판 위로 띄움
LID_Z = WALL_H - INS       # 255 천장 폼 아랫면

WALL2_Y0 = 240             # 덕트·칸막이 벽 앞면
WALL2_Y1 = 245             # 뒷면 (포맥스 5T)
DUCT_TOP = LID_Z - 35      # 220 덕트 벽 윗변 (위 35mm = 배기 전실)

CH_CX = OUT / 2            # 150
CH_CY = (IN0 + WALL2_Y0) / 2   # 127.5 챔버 중심

DOOR_X0, DOOR_X1 = 20, 280      # 앞문 개구부 (v2.8: 12..288)
DOOR_Z0, DOOR_Z1 = FLOOR_TOP, LID_Z - 5   # 81 .. 250
GAP = 2                         # 문 가스켓 눌린 두께

SO_Z = WALL                     # 스탠드오프 시작 높이(바닥판 윗면) 5

# 구매 부품 치수 — [실측] 값은 params.yaml 에서
FAN60 = PARAMS["FAN60"]                        # 60mm 순환팬 (s, t, hole, hd)
FAN40 = PARAMS["FAN40"]                        # 40mm 흡기팬
PTC = PARAMS["PTC"]                            # [실측] PTC 50W 핀 (w=귀 포함 길이 x, d=공기 방향 y, h=높이 z)
EXP = PARAMS["EXP"]                            # [실측] ESP32 38핀 확장보드 (판매처마다 68~78×53~63)
DEVKIT = dict(w=27.9, d=54.4, t=1.6)           # ESP32 DevKitC V4 (공식 54.4×27.9)
LCD = PARAMS["LCD"]                            # [실측] LCD1602 + I2C 백팩
LC = PARAMS["LC"]                              # [실측] 1kg 바형 로드셀 (M4/M5 확인)
MOD = PARAMS["MOD"]                            # [실측] 캐리어 판 위 소형 모듈 (가로×세로×높이)
HINGE = PARAMS["HINGE"]                        # [실측] 25mm 소형 경첩
USBP = PARAMS["USB"]                           # 마이크로USB 패널마운트 Adafruit 3258
USB_HOLE_SP = USBP["hole_sp"]
PWR = PARAMS["PWR"]                            # 전원 인입 PG7 케이블 글랜드 (패널 DC잭 삭제, v2.10)
WAGO = PARAMS["WAGO"]                          # WAGO 221-415 (12P 터미널블록 대체, v2.10)
MOS = PARAMS["MOS"]                            # DFR0457 장착 구멍
TCS = PARAMS["TCS"]                            # TCS34725 보드 외형
SHT = PARAMS["SHT"]                            # SHT31 보드
BME = PARAMS["BME"]                            # BME688 보드
KSD = PARAMS["KSD"]                            # 서모스탯 KSD301

# ============================================================
# 1. 도우미
# ============================================================
def box(x0, y0, z0, x1, y1, z1):
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))

def cyl(axis, c, r, a0, a1):
    """axis 방향 원기둥. c=나머지 두 좌표, a0..a1=축 방향 범위"""
    L = a1 - a0
    if axis == "z":
        return cq.Workplane("XY").circle(r).extrude(L).translate((c[0], c[1], a0))
    if axis == "y":
        return cq.Workplane("XZ").circle(r).extrude(-L).translate((c[0], a0, c[1]))
    if axis == "x":
        return cq.Workplane("YZ").circle(r).extrude(L).translate((a0, c[0], c[1]))

def hexprism(c, af, z0, z1):
    return (cq.Workplane("XY").polygon(6, af / math.cos(math.pi / 6)).extrude(z1 - z0)
            .translate((c[0], c[1], z0)))

PARTS = []      # (name, shape, color, meta)
FASTENERS = {}  # spec -> count

def add(name, shape, color, mat="", proc="", phase=1, kind="part", note=""):
    PARTS.append(dict(name=name, shape=shape, color=color, mat=mat, proc=proc,
                      phase=phase, kind=kind, note=note))
    return shape

def count(spec, n=1):
    FASTENERS[spec] = FASTENERS.get(spec, 0) + n

C_FOAMEX = (0.86, 0.86, 0.83)
C_FOAM = (0.96, 0.90, 0.70, 0.55)
C_AL = (0.74, 0.76, 0.80)
C_PETG = (0.45, 0.55, 0.85)
C_PCB = (0.10, 0.45, 0.25)
C_BLK = (0.15, 0.15, 0.15)
C_BOLT = (0.55, 0.55, 0.58)
C_BRASS = (0.80, 0.65, 0.25)
C_HOT = (0.90, 0.30, 0.20)
C_SENS = (0.10, 0.50, 0.60)
C_P2 = (0.40, 0.60, 0.90, 0.35)

# 볼트: axis 방향으로 head_at 에서 시작해 dir(+1/-1)로 L 만큼
def bolt(name, axis, c, head_at, direction, L, d=3, head="pan", spec=None):
    hd, hh = (5.5, 2.4) if head == "pan" else (6.0, 1.7)
    if d == 4:
        hd, hh = (7.0, 2.8) if head == "pan" else (8.0, 2.3)
    r = d / 2 - 0.05
    if direction > 0:
        sh = cyl(axis, c, r, head_at, head_at + L)
        hdz = cyl(axis, c, hd / 2, head_at - hh, head_at) if head == "pan" else None
    else:
        sh = cyl(axis, c, r, head_at - L, head_at)
        hdz = cyl(axis, c, hd / 2, head_at, head_at + hh) if head == "pan" else None
    s = sh.union(hdz) if hdz is not None else sh
    add(name, s, C_BOLT, kind="fastener")
    count(spec or f"M{d}×{L} {'냄비머리' if head == 'pan' else '접시머리'} 볼트")
    return s

def nut(name, axis, c, a0, direction, d=3):
    af, t = (5.5, 2.4) if d == 3 else (7.0, 3.2)
    a1 = a0 + t * direction
    lo, hi = min(a0, a1), max(a0, a1)
    if axis == "z":
        n = hexprism(c, af, lo, hi)
    else:
        wp = cq.Workplane("XZ" if axis == "y" else "YZ").polygon(6, af / math.cos(math.pi / 6))
        if axis == "y":
            n = wp.extrude(-(hi - lo)).translate((c[0], lo, c[1]))
        else:
            n = wp.extrude(hi - lo).translate((lo, c[0], c[1]))
    n = n.cut(cyl(axis, c, d / 2, lo - 1, hi + 1))
    add(name, n, C_BOLT, kind="fastener")
    count(f"M{d} 너트")
    return n

def standoff(name, x, y, L, z0=SO_Z):
    s = hexprism((x, y), 5.5, z0, z0 + L).cut(cyl("z", (x, y), 1.5, z0 - 1, z0 + L + 1))
    add(name, s, C_BRASS, kind="fastener")
    count(f"M3×{L} 암-암 황동 스탠드오프")
    # 바닥판 아래에서 접시머리 M3×8
    bolt(name + "_screw", "z", (x, y), 0, +1, 8, head="flat", spec="M3×8 접시머리 볼트 (바닥판→스탠드오프)")
    return s

# ============================================================
# 2. 외판 (포맥스 5T) — 재단표 단위
# ============================================================
# 옆판 좌·우: 300 × 265, 바닥판 볼트 구멍 2
SIDE_BOLTS_Y = (30, OUT - 30)
def side_wall(x0):
    w = box(x0, 0, 0, x0 + WALL, OUT, WALL_H)
    for y in SIDE_BOLTS_Y:
        w = w.cut(cyl("x", (y, 10), 1.7, x0 - 1, x0 + WALL + 1))
    return w
SHT_P = (127.5, 170)      # (y, z) 왼쪽 벽 SHT31 홀더 관통 볼트
side_L = add("P01_side_L_foamex5T", side_wall(0).cut(cyl("x", SHT_P, 1.7, -1, WALL + 1)), C_FOAMEX, "포맥스 5T", "재단")
side_R = add("P01_side_R_foamex5T", side_wall(OUT - WALL), C_FOAMEX, "포맥스 5T", "재단")

# 앞판: 290 × 265
front = box(WALL, 0, 0, OUT - WALL, WALL, WALL_H)
door_cut = box(DOOR_X0, -1, DOOR_Z0, DOOR_X1, SKIN + 1, DOOR_Z1)
front = front.cut(door_cut)
INTAKE_C = (60, 41)                      # 흡기팬 중심 (x, z)
front = front.cut(cyl("y", INTAKE_C, 19, -1, WALL + 1))          # 흡기 Ø38
INTAKE_HOLES = [(INTAKE_C[0] + sx * FAN40["hole"] / 2, INTAKE_C[1] + sz * FAN40["hole"] / 2) for sx in (-1, 1) for sz in (-1, 1)]
for p in INTAKE_HOLES:
    front = front.cut(cyl("y", p, 1.7, -1, WALL + 1))
LCD_C = (166.5, 48)                      # LCD 중심 (x, z)
front = front.cut(box(LCD_C[0] - 36, -1, LCD_C[1] - 12.5, LCD_C[0] + 36, WALL + 1, LCD_C[1] + 12.5))  # 창 72×25
LCD_HOLES = [(LCD_C[0] + sx * LCD["hx"] / 2, LCD_C[1] + sz * LCD["hz"] / 2) for sx in (-1, 1) for sz in (-1, 1)]
for p in LCD_HOLES:
    front = front.cut(cyl("y", p, 1.7, -1, WALL + 1))
BTN_X = (228, 248, 268); BTN_Z = 48
for bx in BTN_X:
    front = front.cut(cyl("y", (bx, BTN_Z), 6.1, -1, WALL + 1))   # 12mm 메탈 푸시버튼
# 경첩(왼쪽) 볼트 구멍, 자석 포켓(오른쪽)
HINGE_Z = (DOOR_Z0 + 25, DOOR_Z1 - 50)   # 경첩 하단 z
def hinge_hole_pts(z0):
    zc = z0 + HINGE["L"] / 2
    return [(HINGE["pin_x"] + HINGE["hole_off"], zc - HINGE["hole_sp"] / 2),
            (HINGE["pin_x"] + HINGE["hole_off"], zc + HINGE["hole_sp"] / 2)]
for z0 in HINGE_Z:
    for p in hinge_hole_pts(z0):
        front = front.cut(cyl("y", p, 1.7, -1, WALL + 1))
MAG_X = 290.0; MAG_Z = (110, 166, 222); MAG_D = 8.2   # 8×3 네오디뮴
for mz in MAG_Z:
    front = front.cut(cyl("y", (MAG_X, mz), MAG_D / 2, -1, 3))
add("P02_front_foamex5T", front, C_FOAMEX, "포맥스 5T", "재단")

# 뒷판: 290 × 265
back = box(WALL, OUT - WALL, 0, OUT - WALL, OUT, WALL_H)
PELT_Z = (105, 165)
for z0 in PELT_Z:
    back = back.cut(box(CH_CX - 20, OUT - WALL - 1, z0, CH_CX + 20, OUT + 1, z0 + 40))
GLAND_C = (215, 35)                                # 전원 케이블 글랜드 PG7 (어댑터 플러그를 잘라 넣음)
back = back.cut(cyl("y", GLAND_C, PWR["gland_d"] / 2, OUT - WALL - 1, OUT + 1))
USB_C = (165, 40)                                  # 마이크로USB 패널마운트
back = back.cut(box(USB_C[0] - USBP["cut_w"] / 2, OUT - WALL - 1, USB_C[1] - USBP["cut_h"] / 2,
                    USB_C[0] + USBP["cut_w"] / 2, OUT + 1, USB_C[1] + USBP["cut_h"] / 2))
back = back.cut(box(USB_C[0] - USBP["plug_w"] / 2, OUT - WALL + 1, USB_C[1] - USBP["plug_h"] / 2,
                    USB_C[0] + USBP["plug_w"] / 2, OUT + 1, USB_C[1] + USBP["plug_h"] / 2))     # 바깥 포켓 깊이 4 (플러그 몰딩)
USB_HOLES = [(USB_C[0] - USB_HOLE_SP / 2, USB_C[1]), (USB_C[0] + USB_HOLE_SP / 2, USB_C[1])]
for p in USB_HOLES:
    back = back.cut(cyl("y", p, 1.6, OUT - WALL - 1, OUT + 1))
SW_C = (255, 40)                                   # 로커 스위치 KCD1 컷아웃 19.2×12.9
back = back.cut(box(SW_C[0] - 9.6, OUT - WALL - 1, SW_C[1] - 6.45, SW_C[0] + 9.6, OUT + 1, SW_C[1] + 6.45))
back = back.cut(box(SW_C[0] - 12.5, OUT - WALL - 1, SW_C[1] - 9, SW_C[0] + 12.5, OUT - 1, SW_C[1] + 9))   # 안쪽 카운터보어: 판 1mm 남김 (스냅 클립)
back = back.cut(cyl("y", (CH_CX, 230), 1.7, OUT - WALL - 1, OUT + 1))      # BME688 #1 홀더 볼트
add("P03_back_foamex5T", back, C_FOAMEX, "포맥스 5T", "재단")

# 바닥판: 289 × 289 (옆판 안쪽 삽입, 볼트 4로 너트블록에 고정)
bottom = box(WALL + 0.5, WALL + 0.5, 0, OUT - WALL - 0.5, OUT - WALL - 0.5, WALL)
DRAIN = (CH_CX, 265)
bottom = bottom.cut(cyl("z", DRAIN, 4, -1, WALL + 1))
# 스탠드오프 구멍은 아래 전장부 절에서 추가

# 천장판: 300 × 300
top = box(0, 0, WALL_H, OUT, OUT, OZ)
EXH = (CH_CX - 20, 245, CH_CX + 20, 285)           # 배기 개구 40×40
top = top.cut(box(EXH[0], EXH[1], WALL_H - 1, EXH[2], EXH[3], OZ + 1))
TOP_SCREWS = [(10, 10), (OUT - 10, 10), (10, OUT - 10), (OUT - 10, OUT - 10)]
INSERT = dict(s=100, t=10.5)                       # 천장 센서 인서트 (PETG)
INSERT_SCREWS = [(CH_CX - 40, CH_CY), (CH_CX + 40, CH_CY)]
for p in TOP_SCREWS + INSERT_SCREWS:
    top = top.cut(cyl("z", p, 1.7, WALL_H - 1, OZ + 1))
top_saved = top

# ============================================================
# 3. 단열 폼 10T (재단표 단위) + 링 영역 블록
# ============================================================
foam_bot = box(IN0, IN0, WALL, IN1, IN1, IN0)
foam_bot = foam_bot.cut(cyl("z", DRAIN, 4, 0, 20))
foam_top = box(IN0, IN0, LID_Z, IN1, IN1, LID_Z + INS)
foam_top = foam_top.cut(box(CH_CX - INSERT["s"] / 2 - 0.5, CH_CY - INSERT["s"] / 2 - 0.5, LID_Z - 1,
                            CH_CX + INSERT["s"] / 2 + 0.5, CH_CY + INSERT["s"] / 2 + 0.5, LID_Z + INS + 1))
foam_top = foam_top.cut(box(EXH[0], EXH[1], LID_Z - 1, EXH[2], EXH[3], LID_Z + INS + 1))
foam_top = foam_top.cut(box(CH_CX + 50, CH_CY - 4, LID_Z + 4, OUT - 20, CH_CY + 4, LID_Z + INS + 1))   # 케이블 홈
foam_top = foam_top.cut(box(OUT - 30, 20, LID_Z + 4, OUT - 20, CH_CY + 4, LID_Z + INS + 1))
foam_top = foam_top.cut(cyl("z", (OUT - 25, 25), 4, LID_Z - 1, LID_Z + 5))   # 홈 → 챔버 모서리로 내려가는 구멍

foam_L = box(WALL, WALL, IN0, IN0, OUT - WALL, LID_Z)
foam_R = box(IN1, WALL, IN0, OUT - WALL, OUT - WALL, LID_Z)
foam_F = box(IN0, WALL, IN0, IN1, IN0, LID_Z)
foam_F = foam_F.cut(door_cut)
foam_F = foam_F.cut(box(INTAKE_C[0] - 27, WALL - 1, INTAKE_C[1] - 26, INTAKE_C[0] + 27, IN0 + 1, INTAKE_C[1] + 26))  # 흡기 박스 플랜지
foam_F = foam_F.cut(box(LCD_C[0] - 44, WALL - 1, LCD_C[1] - 22, LCD_C[0] + 44, IN0 + 1, LCD_C[1] + 22))          # LCD 보드
for bx in BTN_X:
    foam_F = foam_F.cut(cyl("y", (bx, BTN_Z), 9, WALL - 1, IN0 + 1))                                          # 버튼 너트
foam_B = box(IN0, OUT - IN0, IN0, IN1, OUT - WALL, LID_Z)
for z0 in PELT_Z:
    foam_B = foam_B.cut(box(CH_CX - 20, OUT - IN0 - 1, z0, CH_CX + 20, OUT - WALL + 1, z0 + 40))
foam_B = foam_B.cut(cyl("y", GLAND_C, PWR["nut_od"] / 2 + 2, OUT - IN0 - 1, OUT - WALL + 1))   # 글랜드 너트
foam_B = foam_B.cut(box(USB_C[0] - 20, OUT - IN0 - 1, USB_C[1] - 10, USB_C[0] + 20, OUT - WALL + 1, USB_C[1] + 10))
foam_B = foam_B.cut(box(SW_C[0] - 13, OUT - IN0 - 1, SW_C[1] - 10, SW_C[0] + 13, OUT - WALL + 1, SW_C[1] + 10))
foam_B = foam_B.cut(box(CH_CX - 8, OUT - IN0 - 1, 230 - 8, CH_CX + 8, OUT - WALL + 1, 230 + 8))  # BME688 #1 너트 포켓
# 옆벽 관통 볼트 포켓 (SHT31 홀더)
SHT_P = (CH_CY, 170)      # (y, z) 왼쪽 벽
foam_L = foam_L.cut(cyl("x", SHT_P, 4, WALL - 1, IN0 + 1))
# 앞판 경첩 볼트 너트 포켓 (왼쪽 옆 폼 앞쪽 끝)
for z0 in HINGE_Z:
    for p in hinge_hole_pts(z0):
        foam_L = foam_L.cut(cyl("y", p, 4, WALL - 1, WALL + 4))

add("F01_foam_bottom_270x270", foam_bot, C_FOAM, "폼보드 10T", "재단")
add("F02_foam_lid_270x270", foam_top, C_FOAM, "폼보드 10T", "재단")
add("F03_foam_side_L_290x240", foam_L, C_FOAM, "폼보드 10T", "재단")
add("F03_foam_side_R_290x240", foam_R, C_FOAM, "폼보드 10T", "재단")
add("F04_foam_front_270x240", foam_F, C_FOAM, "폼보드 10T", "재단")
add("F04_foam_back_270x240", foam_B, C_FOAM, "폼보드 10T", "재단")

# 하부 너트 블록 4 (바닥판 위, 링 영역 z5..15). 옆판 볼트 → 열압입 인서트
for i, x0 in enumerate((WALL + 0.5, OUT - IN0)):
    for y in SIDE_BOLTS_Y:
        blk = box(x0, y - 15, WALL, x0 + 9.5, y + 15, IN0).cut(cyl("x", (y, 10), 2.0, x0 - 1, x0 + 10.5))
        add(f"B01_nut_block_bottom_{'L' if i == 0 else 'R'}_{y}", blk, C_PETG, "PETG", "3D프린트",
            note="M3 열압입 인서트 Ø4.0 구멍")
        count("M3 열압입 인서트 (L4)")
        xh = 0 if i == 0 else OUT
        bolt(f"B01_bolt_{i}_{y}", "x", (y, 10), xh, +1 if i == 0 else -1, 10)
# 상부 코너 블록 4 (옆판 안쪽 모서리, z255..265) — 천장판 나사, 모서리 보강 겸
for (x, y) in TOP_SCREWS:
    blk = box(x - 5, y - 5, LID_Z, x + 5, y + 5, WALL_H).cut(cyl("z", (x, y), 2.0, LID_Z + 2, WALL_H + 1))
    add(f"B02_corner_block_top_{x}_{y}", blk, C_PETG, "PETG", "3D프린트", note="M3 인서트, 옆판에 PVC본드")
    count("M3 열압입 인서트 (L4)")
    bolt(f"B02_bolt_{x}_{y}", "z", (x, y), OZ, -1, 10)

# ============================================================
# 4. 알루미늄 라이너 0.5T (판 단위)
# ============================================================
z_ch0 = FLOOR_TOP + LINER_GAP          # 83
liners = {}
liners["A01_liner_bay_bottom_270x270"] = box(IN0, IN0, IN0, IN1, IN1, IN0 + T05).cut(cyl("z", DRAIN, 4, 0, 20))
liners["A02_liner_bay_L_270x64.5"] = box(IN0, IN0, IN0 + T05, IN0 + T05, IN1, FLOOR_Z)
liners["A02_liner_bay_R_270x64.5"] = box(IN1 - T05, IN0, IN0 + T05, IN1, IN1, FLOOR_Z)
bay_F = box(IN0 + T05, IN0, IN0 + T05, IN1 - T05, IN0 + T05, FLOOR_Z)
bay_F = bay_F.cut(box(INTAKE_C[0] - 25, IN0 - 1, INTAKE_C[1] - 25, INTAKE_C[0] + 25, IN0 + 2, INTAKE_C[1] + 25))   # 흡기 박스 50×50
bay_F = bay_F.cut(box(LCD_C[0] - 27, IN0 - 1, LCD_C[1] - 13, LCD_C[0] + 27, IN0 + 2, LCD_C[1] + 13))  # LCD 백팩
for bx in BTN_X:
    bay_F = bay_F.cut(cyl("y", (bx, BTN_Z), 7, IN0 - 1, IN0 + 2))
ANT_WIN = (159, 189, 30, 50)            # ESP32 안테나 창 (x0,x1,z0,z1)
bay_F = bay_F.cut(box(ANT_WIN[0], IN0 - 1, ANT_WIN[2], ANT_WIN[1], IN0 + 2, ANT_WIN[3]))
# 앞쪽 전장부 라이너는 생략: ESP32 Wi-Fi/BT 전파가 앞판(포맥스·폼)으로 나가게. 앞쪽 플레넘 온도 45~50°C는 폼·포맥스 허용 범위
bay_B = box(IN0 + T05, IN1 - T05, IN0 + T05, IN1 - T05, IN1, FLOOR_Z)
bay_B = bay_B.cut(cyl("y", GLAND_C, PWR["nut_od"] / 2 + 1, IN1 - 2, IN1 + 1))
bay_B = bay_B.cut(box(USB_C[0] - 20, IN1 - 2, USB_C[1] - 10, USB_C[0] + 20, IN1 + 1, USB_C[1] + 10))
bay_B = bay_B.cut(box(SW_C[0] - 13, IN1 - 2, SW_C[1] - 10, SW_C[0] + 13, IN1 + 1, SW_C[1] + 10))
liners["A03_liner_bay_back_269x64.5"] = bay_B
liners["A04_liner_ch_L_270x171.5"] = box(IN0, IN0, z_ch0, IN0 + T05, IN1, LID_Z - T05)
liners["A04_liner_ch_R_270x171.5"] = box(IN1 - T05, IN0, z_ch0, IN1, IN1, LID_Z - T05)
ch_B = box(IN0 + T05, WALL2_Y0 - T05, z_ch0, IN1 - T05, WALL2_Y0, DUCT_TOP)
liners["A05_liner_ch_back_269x137"] = ch_B
duct_B = box(IN0 + T05, IN1 - T05, FLOOR_Z, IN1 - T05, IN1, LID_Z - T05)
for z0 in PELT_Z:
    duct_B = duct_B.cut(box(CH_CX - 20, IN1 - 2, z0, CH_CX + 20, IN1 + 1, z0 + 40))
duct_B = duct_B.cut(cyl("y", (CH_CX, 230), 1.7, IN1 - 2, IN1 + 1))
liners["A06_liner_duct_back_269x174.5"] = duct_B
ceil = box(IN0, IN0, LID_Z - T05, IN1, IN1, LID_Z)
ceil = ceil.cut(box(CH_CX - INSERT["s"] / 2, CH_CY - INSERT["s"] / 2, LID_Z - 2, CH_CX + INSERT["s"] / 2, CH_CY + INSERT["s"] / 2, LID_Z + 1))
ceil = ceil.cut(box(EXH[0], EXH[1], LID_Z - 2, EXH[2], EXH[3], LID_Z + 1))
ceil = ceil.cut(cyl("z", (OUT - 25, 25), 4, LID_Z - 2, LID_Z + 1))
liners["A07_liner_ceiling_270x270"] = ceil
ch_L = liners["A04_liner_ch_L_270x171.5"].cut(cyl("x", SHT_P, 1.7, IN0 - 1, IN0 + 2))
liners["A04_liner_ch_L_270x171.5"] = ch_L
for n, s in liners.items():
    add(n, s, C_AL + (0.65,), "알루미늄 0.5T", "재단")

# ============================================================
# 5. 덕트·칸막이 벽 (포맥스 5T, 전장부 바닥 ~ z220 한 장)
# ============================================================
FAN_C = (65, 48)                              # 순환팬 중심 (x, z)
wall2 = box(IN0 + T05, WALL2_Y0, IN0 + T05, IN1 - T05, WALL2_Y1, DUCT_TOP)
wall2 = wall2.cut(cyl("y", FAN_C, 28.5, WALL2_Y0 - 1, WALL2_Y1 + 1))
FAN_HOLES = [(FAN_C[0] + sx * FAN60["hole"] / 2, FAN_C[1] + sz * FAN60["hole"] / 2) for sx in (-1, 1) for sz in (-1, 1)]
for p in FAN_HOLES:
    wall2 = wall2.cut(cyl("y", p, 1.7, WALL2_Y0 - 1, WALL2_Y1 + 1))
WIRE_PASS = (200, 30)                         # 복귀실→플레넘 배선 통과 (그로밋)
wall2 = wall2.cut(cyl("y", WIRE_PASS, 6, WALL2_Y0 - 1, WALL2_Y1 + 1))
add("P04_duct_partition_wall_foamex5T", wall2, C_FOAMEX, "포맥스 5T", "재단",
    note="전장부 칸막이 + 덕트 벽 한 장. 아랫부분이 플레넘/복귀실을 나눔")

# 타공판 받침 턱 (포맥스 5T 10폭, z75..80, 전장부 라이너 안쪽)
LZ0 = FLOOR_Z - 5
ledges = [
    box(IN0 + T05, IN0 + T05, LZ0, IN1 - T05, IN0 + T05 + 10, FLOOR_Z),                         # 앞
    box(IN0 + T05, IN0 + T05 + 10, LZ0, IN0 + T05 + 10, WALL2_Y0 - 10, FLOOR_Z),               # 왼
    box(IN1 - T05 - 10, IN0 + T05 + 10, LZ0, IN1 - T05, WALL2_Y0 - 10, FLOOR_Z),               # 오
    box(IN0 + T05, WALL2_Y0 - 10, LZ0, FAN_C[0] - 34, WALL2_Y0, FLOOR_Z),                       # 뒤-왼
    box(FAN_C[0] + 34, WALL2_Y0 - 10, LZ0, IN1 - T05, WALL2_Y0, FLOOR_Z),                       # 뒤-오
]
led_u = ledges[0]
for l in ledges[1:]:
    led_u = led_u.union(l)
add("P05_floor_ledge_strips_foamex5T", led_u, C_FOAMEX, "포맥스 5T", "재단", note="10폭 띠 5조각")

# ============================================================
# 6. 타공판 (알루미늄 1T) + 로드셀 + 트레이
# ============================================================
fl_x0, fl_x1 = IN0 + T05 + 0.5, IN1 - T05 - 0.5
fl_y0, fl_y1 = IN0 + T05 + 0.5, WALL2_Y0 - 0.5
floor = box(fl_x0, fl_y0, FLOOR_Z, fl_x1, fl_y1, FLOOR_TOP)
pts = []
for x in range(int(fl_x0) + 15, int(fl_x1) - 12, 10):
    for y in range(int(fl_y0) + 15, int(fl_y1) - 12, 10):
        if abs(x - CH_CX) < 62 and abs(y - CH_CY) < 32:
            continue                                   # 로드셀 자리 미타공
        if math.hypot(x - 265, y - 37) < 10:
            continue
        pts.append((x, y))
N_PERF = len(pts)
floor = floor.cut(cq.Workplane("XY").workplane(offset=FLOOR_Z - 1).pushPoints(pts).circle(2).extrude(FLOOR_T + 2))
FLOOR_WIRE = (265, 37)                                 # 챔버 배선 통과 Ø8
floor = floor.cut(cyl("z", FLOOR_WIRE, 4, FLOOR_Z - 1, FLOOR_TOP + 1))
LC_X0 = CH_CX - LC["L"] / 2                            # 110
LC_CABLE = (LC_X0 - 8, CH_CY)                          # 로드셀 선 Ø6
floor = floor.cut(cyl("z", LC_CABLE, 3, FLOOR_Z - 1, FLOOR_TOP + 1))
lc_base_holes = [(LC_X0 + LC["hole_end"], CH_CY), (LC_X0 + LC["hole_end"] + LC["hole_sp"], CH_CY)]
lc_tray_holes = [(LC_X0 + LC["L"] - LC["hole_end"], CH_CY), (LC_X0 + LC["L"] - LC["hole_end"] - LC["hole_sp"], CH_CY)]
for p in lc_base_holes:
    floor = floor.cut(cyl("z", p, 2.25, FLOOR_Z - 1, FLOOR_TOP + 1))
add("A10_perforated_floor_Al1T", floor, C_AL, "알루미늄 1T", "재단+타공",
    note=f"Ø4 구멍 {N_PERF}개, 10mm 피치 → 기성 타공판 권장")

blk_h1, blk_h2 = 15, 20
lc_z0 = FLOOR_TOP + blk_h1
base_blk = box(LC_X0, CH_CY - 10, FLOOR_TOP, LC_X0 + 25, CH_CY + 10, lc_z0)
for p in lc_base_holes:
    base_blk = base_blk.cut(cyl("z", p, 2.25, FLOOR_TOP - 1, lc_z0 + 1))
add("L01_loadcell_base_block", base_blk, C_PETG, "PETG", "3D프린트")
cell = box(LC_X0, CH_CY - LC["s"] / 2, lc_z0, LC_X0 + LC["L"], CH_CY + LC["s"] / 2, lc_z0 + LC["s"])
for p in lc_base_holes + lc_tray_holes:
    cell = cell.cut(cyl("z", p, LC["thread"] / 2 - 0.05, lc_z0 - 1, lc_z0 + LC["s"] + 1))
add("L02_loadcell_1kg_bar", cell, (0.75, 0.75, 0.8), kind="buy")
tz0 = lc_z0 + LC["s"]
tray_blk = box(LC_X0 + LC["L"] - 25, CH_CY - 10, tz0, LC_X0 + LC["L"], CH_CY + 10, tz0 + blk_h2)
for p in lc_tray_holes:
    tray_blk = tray_blk.cut(cyl("z", p, 2.25, tz0 - 1, tz0 + blk_h2 + 1))
    tray_blk = tray_blk.cut(cyl("z", p, 3.75, tz0 + blk_h2 - 4, tz0 + blk_h2 + 1))   # 머리 묻힘
SH_HOLES = [(LC_X0 + LC["L"] - 12.5, CH_CY - 6.5), (LC_X0 + LC["L"] - 12.5, CH_CY + 6.5)]
add("L03_loadcell_tray_block", tray_blk, C_PETG, "PETG", "3D프린트")
for i, p in enumerate(lc_base_holes):
    bolt(f"L_bolt_base_{i}", "z", p, FLOOR_Z, +1, 25, d=4, spec="M4×25 냄비머리 볼트 (로드셀) [실측: M4/M5]")
for i, p in enumerate(lc_tray_holes):
    bolt(f"L_bolt_tray_{i}", "z", p, tz0 + blk_h2 - 4, -1, 30, d=4, head="flat",
         spec="M4×30 볼트 (로드셀, 머리 묻힘) [실측: M4/M5]")
sz0 = tz0 + blk_h2
shield = box(CH_CX - 50, CH_CY - 20, sz0, CH_CX + 50, CH_CY + 20, sz0 + 1)
add("A11_loadcell_shield_Al1T_100x40", shield, C_AL, "알루미늄 1T", "재단")

# 트레이 허브 (트레이 블록 위, 차폐판을 끼우고 트레이 프레임을 받침)
hub_z0 = sz0 + 1
hub = box(CH_CX - 50, CH_CY - 20, hub_z0, CH_CX + 50, CH_CY + 20, hub_z0 + 4)
add("L04_tray_platform_PETG_100x40", hub, C_PETG, "PETG", "3D프린트",
    note="차폐판과 함께 트레이 블록 윗면에 접착. 트레이가 이 위에 얹힘(포켓으로 위치 잡음)")

TRAY_X, TRAY_Y = 245, 215
tray_z = hub_z0 + 4 - 3          # 트레이 아랫면 포켓 3mm 가 받침판을 감쌈
tx0, ty0 = CH_CX - TRAY_X / 2, CH_CY - TRAY_Y / 2
tray = box(tx0, ty0, tray_z, tx0 + TRAY_X, ty0 + TRAY_Y, tray_z + 10) \
    .cut(box(tx0 + 6, ty0 + 6, tray_z - 1, tx0 + TRAY_X - 6, ty0 + TRAY_Y - 6, tray_z + 11))
ribs = box(tx0, CH_CY - 3, tray_z, tx0 + TRAY_X, CH_CY + 3, tray_z + 6) \
    .union(box(CH_CX - 3, ty0, tray_z, CH_CX + 3, ty0 + TRAY_Y, tray_z + 6)) \
    .union(box(CH_CX - 56, CH_CY - 26, tray_z, CH_CX + 56, CH_CY + 26, tray_z + 6))
tray = tray.union(ribs).cut(box(CH_CX - 50.5, CH_CY - 20.5, tray_z - 1, CH_CX + 50.5, CH_CY + 20.5, tray_z + 3))
add("T01_tray_frame_245x215_PETG", tray, C_PETG, "PETG", "3D프린트", note="메시는 윗면에 케이블타이/클립")
mesh = box(tx0 + 2, ty0 + 2, tray_z + 10, tx0 + TRAY_X - 2, ty0 + TRAY_Y - 2, tray_z + 10.6)
add("T02_tray_mesh_241x211", mesh, (0.8, 0.8, 0.82, 0.5), "스테인리스/PP 메시", "재단")

# ============================================================
# 7. 천장: 센서 인서트(PETG) + TCS34725 + LED 스트립 + 배기 플랩
# ============================================================
ins_z0, ins_z1 = LID_Z - T05, LID_Z + INS
ins = box(CH_CX - 50, CH_CY - 50, ins_z0, CH_CX + 50, CH_CY + 50, ins_z1)
ins = ins.cut(box(CH_CX - TCS["w"] / 2 - 0.5, CH_CY - TCS["d"] / 2 - 0.5, ins_z0 + 3,
                  CH_CX + TCS["w"] / 2 + 0.5, CH_CY + TCS["d"] / 2 + 0.5, ins_z1 + 1))   # TCS 포켓(위에서, 보드+0.5)
ins = ins.cut(cyl("z", (CH_CX, CH_CY), 3, ins_z0 - 1, ins_z0 + 4))                              # 시야창 Ø6
for dy in (-30, 30):                                                                             # LED 홈 2줄 (5cm×2)
    ins = ins.cut(box(CH_CX - 26, CH_CY + dy - 4.5, ins_z0 - 1, CH_CX + 26, CH_CY + dy + 4.5, ins_z0 + 2))
    ins = ins.cut(cyl("z", (CH_CX + 24, CH_CY + dy), 2, ins_z0, ins_z1 + 1))                    # LED 선 구멍
ins = ins.cut(box(CH_CX + 12, CH_CY - 4, ins_z1 - 4, CH_CX + 51, CH_CY + 4, ins_z1 + 1))        # 케이블 홈
ins = ins.cut(box(CH_CX + 21, CH_CY - 32, ins_z1 - 4, CH_CX + 27, CH_CY + 32, ins_z1 + 1))      # LED 선 홈
for p in INSERT_SCREWS:
    ins = ins.cut(cyl("z", p, 2.0, ins_z1 - 6, ins_z1 + 1))
    count("M3 열압입 인서트 (L4)")
    bolt(f"S_insert_bolt_{p[0]}", "z", p, OZ, -1, 10)
add("S01_sensor_insert_PETG_100x100", ins, C_PETG, "PETG", "3D프린트")
add("S02_TCS34725_SEN0212", box(CH_CX - TCS["w"] / 2, CH_CY - TCS["d"] / 2, ins_z0 + 3,
                                  CH_CX + TCS["w"] / 2, CH_CY + TCS["d"] / 2, ins_z0 + 3 + TCS["t"]), C_SENS, kind="buy",
    note="DFRobot 레이아웃 18.51×23, 구멍 없음 → 포켓에 끼우고 위에서 폼으로 누름")
for dy in (-30, 30):
    add(f"S03_LED_strip_50mm_{'F' if dy < 0 else 'B'}", box(CH_CX - 25, CH_CY + dy - 4, ins_z0 + 1, CH_CX + 25, CH_CY + dy + 4, ins_z0 + 2),
        (1, 1, 0.85), kind="buy")
flap_frame = box(EXH[0] - 10, EXH[1] - 5, OZ, EXH[2] + 10, EXH[3] + 5, OZ + 3) \
    .cut(box(EXH[0], EXH[1], OZ - 1, EXH[2], EXH[3], OZ + 4))
add("S04_exhaust_flap_frame_PETG", flap_frame, C_PETG, "PETG", "3D프린트", note="천장판에 PVC본드")
add("S05_exhaust_flap_PET0.3", box(EXH[0] - 4, EXH[1] - 2, OZ + 3, EXH[2] + 4, EXH[3] + 2, OZ + 3.3), (0.9, 0.9, 0.6, 0.6),
    "PET 0.3", "재단", note="뒤쪽 변만 테이프 힌지")

# ============================================================
# 8. 챔버 센서: SHT31(왼벽), BME688 #1(덕트 전실, 뒷벽)
# ============================================================
sht_x0 = IN0 + T05
SH_T = 6                                      # 홀더 두께
sh_face = sht_x0 + SH_T
sht_h = box(sht_x0, SHT_P[0] - 12, SHT_P[1] - 10, sh_face, SHT_P[0] + 12, SHT_P[1] + 10) \
    .cut(cyl("x", SHT_P, 1.7, sht_x0 - 1, sh_face + 1))
sht_h = sht_h.cut(cq.Workplane("YZ").polygon(6, 5.7 / math.cos(math.pi / 6)).extrude(4.1).translate((sh_face - 4, SHT_P[0], SHT_P[1])))  # 너트 포켓
SHT_HOLES = [(SHT_P[0] + sy * SHT["hole_sp"] / 2, SHT_P[1] + SHT["h"] / 2 - SHT["hole_edge"]) for sy in (-1, 1)]
for p in SHT_HOLES:
    sht_h = sht_h.cut(cyl("x", p, 0.8, sh_face - 6, sh_face + 1))                       # M2 셀프태핑 Ø1.6
add("C01_SHT31_holder_PETG_6mm", sht_h, C_PETG, "PETG", "3D프린트", note="벽 관통 M3 1개(너트는 포켓), 보드는 M2×6 셀프태핑 2개")
sb = box(sh_face, SHT_P[0] - SHT["w"] / 2, SHT_P[1] - SHT["h"] / 2, sh_face + SHT["t"], SHT_P[0] + SHT["w"] / 2, SHT_P[1] + SHT["h"] / 2)
for p in SHT_HOLES:
    sb = sb.cut(cyl("x", p, SHT["hole_d"] / 2, sh_face - 1, sh_face + 2))
add("C02_SHT31_SEN0331", sb, C_SENS, kind="buy")
bolt("C_bolt_SHT31", "x", SHT_P, 0, +1, 20)
nut("C_nut_SHT31", "x", SHT_P, sh_face - 4 + 0.05, +1)
for i, p in enumerate(SHT_HOLES):
    s_ = cyl("x", p, 0.8, sh_face - 4.6, sh_face + SHT["t"]).union(cyl("x", p, 1.9, sh_face + SHT["t"], sh_face + SHT["t"] + 1.3))
    add(f"C_screw_SHT31_{i}", s_, C_BOLT, kind="fastener")
    count("M2×6 셀프태핑 나사 (SHT31)")

bme1_y1 = IN1 - T05
BM_T = 6
bm_face = bme1_y1 - BM_T
bme1_h = box(CH_CX - 18, bm_face, 230 - 14, CH_CX + 18, bme1_y1, 230 + 14).cut(cyl("y", (CH_CX, 230), 1.7, bm_face - 1, bme1_y1 + 1))
bme1_h = bme1_h.union(box(CH_CX - 18, bm_face - 1.2, 230 - 14, CH_CX + 18, bm_face, 230 + 14)
                      .cut(box(CH_CX - BME["w"] / 2 - 0.3, bm_face - 2, 230 - BME["h"] / 2 - 0.3, CH_CX + BME["w"] / 2 + 0.3, bm_face + 1, 230 + BME["h"] / 2 + 0.3)))  # 보드 테두리
bme1_h = bme1_h.cut(cq.Workplane("XZ").polygon(6, 5.7 / math.cos(math.pi / 6)).extrude(-4.1).translate((CH_CX, bm_face - 0.05, 230)))  # 너트 포켓
add("C03_BME688_1_holder_PETG", bme1_h, C_PETG, "PETG", "3D프린트", note="보드는 테두리 안에 VHB 양면테이프")
add("C04_BME688_1_SEN0617", box(CH_CX - BME["w"] / 2, bm_face - BME["t"], 230 - BME["h"] / 2, CH_CX + BME["w"] / 2, bm_face, 230 + BME["h"] / 2),
    C_SENS, kind="buy")
bolt("C_bolt_BME1", "y", (CH_CX, 230), OUT, -1, 20)
nut("C_nut_BME1", "y", (CH_CX, 230), bm_face + 4 - 0.05, -1)

# 케이블 클립 (챔버 오른쪽 앞 모서리, 3M 양면) 4개
for k, z in enumerate((100, 140, 180, 220)):
    add(f"C05_cable_clip_{k+1}", box(IN1 - T05 - 8, IN0 + T05 + 22, z, IN1 - T05, IN0 + T05 + 30, z + 10), C_PETG, "PETG", "3D프린트")

# ============================================================
# 9. 앞문: 바깥판 + 플러그 + 가스켓 + 경첩 + 자석
# ============================================================
door_x0, door_x1 = 2, OUT - 2
door_z0, door_z1 = DOOR_Z0 - 10, DOOR_Z1 + 10
door = box(door_x0, -(WALL + GAP), door_z0, door_x1, -GAP, door_z1)
door = door.union(box(door_x1, -(WALL + GAP), (door_z0 + door_z1) / 2 - 30, door_x1 + 10, -GAP, (door_z0 + door_z1) / 2 + 30))  # 손잡이 턱
for mz in MAG_Z:
    door = door.cut(cyl("y", (MAG_X, mz), MAG_D / 2, -GAP - 3, -GAP + 1))
for z0 in HINGE_Z:
    for p in hinge_hole_pts(z0):
        door = door.cut(cyl("y", p, 1.7, -(WALL + GAP) - 1, -GAP + 1))
for p in [(door_x0 + 20, door_z0 + 10), (door_x1 - 20, door_z0 + 10)]:
    pass
add("D01_door_outer_foamex5T", door, C_FOAMEX, "포맥스 5T", "재단", note="손잡이 턱 포함 306 폭")
plug = box(DOOR_X0 + 1.5, -GAP, DOOR_Z0 + 1.5, DOOR_X1 - 1.5, IN0 - 2, DOOR_Z1 - 1.5)
add("D02_door_plug_foam_257x166", plug, C_FOAM, "폼보드 10T + 포맥스 5T", "재단", note="폼 10T 위에 앞판 문 개구부에서 잘라낸 포맥스 5T 조각을 겹쳐 붙여 15T")
add("D03_door_plug_liner_Al0.5", box(DOOR_X0 + 1.5, IN0 - 2, DOOR_Z0 + 1.5, DOOR_X1 - 1.5, IN0 - 1.5, DOOR_Z1 - 1.5),
    C_AL + (0.65,), "알루미늄 0.5T", "재단")
gk_in = (DOOR_X0 - 1, DOOR_Z0 - 1, DOOR_X1 + 1, DOOR_Z1 + 1)
gk = box(DOOR_X0 - 6, -GAP, DOOR_Z0 - 6, DOOR_X1 + 6, 0, DOOR_Z1 + 6).cut(box(gk_in[0], -GAP - 1, gk_in[1], gk_in[2], 1, gk_in[3]))
add("D04_door_gasket_5mm", gk, (0.2, 0.2, 0.2, 0.7), "실리콘 폼 테이프", "재단", note="앞판 바깥면에 부착")
for i, mz in enumerate(MAG_Z):
    add(f"D05_magnet_wall_{i+1}_8x3", cyl("y", (MAG_X, mz), 4, 0, 3), C_BLK, kind="buy")
    add(f"D05_magnet_door_{i+1}_8x3", cyl("y", (MAG_X, mz), 4, -GAP - 3, -GAP), C_BLK, kind="buy")
for i, z0 in enumerate(HINGE_Z):
    # 접힌 상태의 맞대기 경첩 (날개 2장이 앞판과 문 사이에 겹침)
    leaf_w = box(HINGE["pin_x"], -1.0, z0, HINGE["pin_x"] + HINGE["leaf"] + 1, 0, z0 + HINGE["L"])
    leaf_d = box(HINGE["pin_x"], -2.0, z0, HINGE["pin_x"] + HINGE["leaf"] + 1, -1.0, z0 + HINGE["L"])
    pin = cyl("z", (HINGE["pin_x"], -1.0), 1.9, z0, z0 + HINGE["L"])
    hg = leaf_w.union(leaf_d).union(pin)
    for p in hinge_hole_pts(z0):
        hg = hg.cut(cyl("y", p, 1.7, -3, 1))
    add(f"D06_hinge_25mm_{i+1}", hg, C_BOLT, kind="buy", note="[실측] 소형 맞대기 경첩 25mm")
    for j, p in enumerate(hinge_hole_pts(z0)):
        bolt(f"D_hinge_bolt_{i}_{j}", "y", p, -(WALL + GAP), +1, 16, spec="M3×16 냄비머리 볼트 (경첩)")
        nut(f"D_hinge_nut_{i}_{j}", "y", p, WALL, +1)

# ============================================================
# 10. 전장부 — 앞판 부착물 (흡기 박스, LCD, 버튼)
# ============================================================
# 흡기 박스 (PETG): 앞판 안쪽 플랜지 → 팬 → 활성탄 → BME688 #2 → 출구(플랩)
ix, iz = INTAKE_C
ib_y0, ib_y1 = WALL, 66
ibox = box(ix - 26, ib_y0, iz - 26, ix + 26, ib_y0 + 3, iz + 26)                 # 플랜지 52×52 (폼 포켓 안)
ibox = ibox.union(box(ix - 24, ib_y0 + 3, iz - 24, ix + 24, ib_y1, iz + 24)
                  .cut(box(ix - 21.5, ib_y0 + 2, iz - 21.5, ix + 21.5, ib_y1 + 1, iz + 21.5)))
ibox = ibox.cut(cyl("y", INTAKE_C, 19, ib_y0 - 1, ib_y0 + 4))
for p in INTAKE_HOLES:
    ibox = ibox.cut(cyl("y", p, 1.7, ib_y0 - 1, ib_y0 + 4))
ibox = ibox.cut(box(ix - 21.5, 33, iz + 20, ix + 21.5, 39, iz + 25))     # 활성탄 패드 삽입 슬롯(위)
ibox = ibox.cut(box(ix - 16, 49, iz + 20, ix + 16, 51.6, iz + 25))       # BME688 슬롯(위)
ibox = ibox.cut(cyl("z", (ix + 18, 58), 3, iz + 20, iz + 25))            # 센서 선
add("I01_intake_box_PETG", ibox, C_PETG, "PETG", "3D프린트", note="슬롯 위는 테이프로 막음")
fan40 = box(ix - FAN40["s"] / 2, ib_y0 + 3, iz - FAN40["s"] / 2, ix + FAN40["s"] / 2, ib_y0 + 3 + FAN40["t"], iz + FAN40["s"] / 2).cut(cyl("y", INTAKE_C, 18.5, 0, 30))
for p in INTAKE_HOLES:
    fan40 = fan40.cut(cyl("y", p, 1.7, 0, 30))
add("I02_fan_40mm_intake_PWM", fan40, C_BLK, kind="buy")
add("I03_carbon_pad", box(ix - 21, 33.5, iz - 21, ix + 21, 38.5, iz + 21), (0.1, 0.1, 0.1, 0.8), "활성탄 패드", "재단")
add("I04_BME688_2_SEN0617", box(ix - 15, 49.4, iz - 11, ix + 15, 51.0, iz + 11), C_SENS, kind="buy")
add("I05_intake_flap_PET", box(ix - 23, ib_y1, iz - 23, ix + 23, ib_y1 + 0.3, iz + 23), (0.9, 0.9, 0.6, 0.6), "PET 0.3", "재단",
    note="출구 윗변 테이프 힌지 (역류 방지)")
for i, p in enumerate(INTAKE_HOLES):
    bolt(f"I_bolt_{i}", "y", p, 0, +1, 20, spec="M3×20 냄비머리 볼트 (흡기팬)")
    nut(f"I_nut_{i}", "y", p, ib_y0 + 3 + FAN40["t"], +1)

# LCD 16×2 I2C: 앞판 → 스페이서 3 → PCB → 너트
lcd_y0 = WALL + 3
lcd = box(LCD_C[0] - LCD["w"] / 2, lcd_y0, LCD_C[1] - LCD["h"] / 2, LCD_C[0] + LCD["w"] / 2, lcd_y0 + 1.6, LCD_C[1] + LCD["h"] / 2)
for p in LCD_HOLES:
    lcd = lcd.cut(cyl("y", p, 1.6, lcd_y0 - 1, lcd_y0 + 3))
lcd = lcd.union(box(LCD_C[0] - LCD["bez_w"] / 2, lcd_y0 - LCD["bez_t"] + 0.6, LCD_C[1] - LCD["bez_h"] / 2,
                    LCD_C[0] + LCD["bez_w"] / 2, lcd_y0, LCD_C[1] + LCD["bez_h"] / 2))
lcd = lcd.union(box(LCD_C[0] - 21, lcd_y0 + 1.6, LCD_C[1] - 10, LCD_C[0] + 21, lcd_y0 + 13, LCD_C[1] + 10))   # I2C 백팩
add("E10_LCD1602_I2C", lcd, (0.1, 0.4, 0.2), kind="buy", note=f"키트 보유. 구멍 {LCD['hx']}×{LCD['hz']} [실측]")
for i, p in enumerate(LCD_HOLES):
    add(f"E10_spacer_{i}", cyl("y", p, 3, WALL, lcd_y0).cut(cyl("y", p, 1.6, WALL - 1, lcd_y0 + 1)), (0.9, 0.9, 0.9), kind="fastener")
    count("M3 나일론 스페이서 3mm")
    bolt(f"E10_bolt_{i}", "y", p, 0, +1, 12, spec="M3×12 냄비머리 볼트 (LCD)")
    nut(f"E10_nut_{i}", "y", p, lcd_y0 + 1.6, +1)

for i, bx in enumerate(BTN_X):
    b = cyl("y", (bx, BTN_Z), 7.5, -2, 0).union(cyl("y", (bx, BTN_Z), 6, 0, 28))
    add(f"E11_pushbutton_12mm_{i+1}", b, C_BOLT, kind="buy", note="12mm 메탈 모멘터리, 리드선 일체형 (납땜 없음)")
    add(f"E11_pushbutton_nut_{i+1}", cyl("y", (bx, BTN_Z), 8, WALL, WALL + 2).cut(cyl("y", (bx, BTN_Z), 6.1, WALL - 1, WALL + 3)), C_BOLT, kind="fastener")

# ============================================================
# 11. 전장부 — 바닥 스탠드오프 위 (ESP32, 캐리어, 터미널, 히터 덕트, 격벽)
# ============================================================
SO_HOLES = []   # 바닥판·폼·라이너 관통 위치

def so(name, x, y, L):
    SO_HOLES.append((x, y, L))
    return standoff(name, x, y, L)

# ESP32 확장보드 + DevKitC
ex0, ey0 = 135, 45
SO_TOP = SO_Z + 20
exp_holes = [(ex0 + EXP["inset"], ey0 + EXP["inset"]), (ex0 + EXP["w"] - EXP["inset"], ey0 + EXP["inset"]),
             (ex0 + EXP["inset"], ey0 + EXP["d"] - EXP["inset"]), (ex0 + EXP["w"] - EXP["inset"], ey0 + EXP["d"] - EXP["inset"])]
expb = box(ex0, ey0, SO_TOP, ex0 + EXP["w"], ey0 + EXP["d"], SO_TOP + EXP["t"])
for p in exp_holes:
    expb = expb.cut(cyl("z", p, 1.6, SO_TOP - 1, SO_TOP + 3))
expb = expb.union(box(ex0 + 2, ey0 + 9, SO_TOP + EXP["t"], ex0 + 9, ey0 + EXP["d"] - 9, SO_TOP + EXP["t"] + 10))     # 나사 터미널 열
expb = expb.union(box(ex0 + EXP["w"] - 9, ey0 + 9, SO_TOP + EXP["t"], ex0 + EXP["w"] - 2, ey0 + EXP["d"] - 9, SO_TOP + EXP["t"] + 10))
add("E01_ESP32_38pin_expansion_board", expb, C_PCB, kind="buy", note="CMODULE-47 78×52.5. 구멍 위치는 도착 후 실측")
dk_x0 = ex0 + EXP["w"] / 2 - DEVKIT["w"] / 2
dk_z0 = SO_TOP + EXP["t"] + 8.5
devkit = box(dk_x0, ey0 + 4, dk_z0, dk_x0 + DEVKIT["w"], ey0 + 4 + DEVKIT["d"], dk_z0 + DEVKIT["t"])
devkit = devkit.union(box(dk_x0 + 4, ey0 + 4, dk_z0 + DEVKIT["t"], dk_x0 + DEVKIT["w"] - 4, ey0 + 4 + 25.5, dk_z0 + DEVKIT["t"] + 3.2))  # WROOM 모듈 (안테나=앞쪽)
devkit = devkit.union(box(dk_x0 + DEVKIT["w"] / 2 - 4, ey0 + 4 + DEVKIT["d"] - 5, dk_z0 + DEVKIT["t"], dk_x0 + DEVKIT["w"] / 2 + 4, ey0 + 4 + DEVKIT["d"] + 1, dk_z0 + DEVKIT["t"] + 3))  # micro USB (뒤쪽)
add("E02_ESP32_DevKitC_V4_WROOM32D", devkit, (0.15, 0.15, 0.3), kind="buy", note="안테나를 앞(라이너 창) 쪽으로")
for i, (x, y) in enumerate(exp_holes):
    so(f"E01_so_{i}", x, y, 20)
    bolt(f"E01_bolt_{i}", "z", (x, y), SO_TOP + EXP["t"], -1, 6, spec="M3×6 냄비머리 볼트 (보드→스탠드오프)")

# 모듈 캐리어 판 (PETG 3T) — v2.10: DFR0457 MOSFET 2개(볼트 4개씩), SD·HX711·MP1584·부저 모듈(포켓+케이블타이)
cx0, cy0, cx1, cy1 = 214, 36, 280, 206
carrier = box(cx0, cy0, SO_TOP, cx1, cy1, SO_TOP + 3)
car_holes = [(cx0 + 4, cy0 + 4), (cx1 - 4, cy0 + 4), (cx0 + 4, cy1 - 4), (cx1 - 4, cy1 - 4)]
for p in car_holes:
    carrier = carrier.cut(cyl("z", p, 1.7, SO_TOP - 1, SO_TOP + 4))
MOS_SPACER = 3                                 # DFR0457 아래 나일론 스페이서 (스루홀 단자 다리 여유)
y = cy0 + 5
mod_pos = {}
mos_bolts = []
for k, (w, d, h) in MOD.items():
    mx0 = (cx0 + cx1) / 2 - w / 2
    if k.startswith("MOS"):
        hx1 = mx0 + w - MOS["hole_edge"]
        pts_ = [(hx1 - sx * MOS["hole_sp_x"], y + MOS["hole_edge"] + sy * MOS["hole_sp_y"]) for sx in (0, 1) for sy in (0, 1)]
        for p in pts_:
            carrier = carrier.cut(cyl("z", p, 1.7, SO_TOP - 1, SO_TOP + 4))
        mos_bolts.append((k, pts_))
    else:
        rim = box(mx0 - 2, y - 2, SO_TOP + 3, mx0 + w + 2, y + d + 2, SO_TOP + 5).cut(box(mx0 - 0.3, y - 0.3, SO_TOP + 2, mx0 + w + 0.3, y + d + 0.3, SO_TOP + 6))
        carrier = carrier.union(rim)
        for sx in (mx0 - 5.5, mx0 + w + 2.5):      # 케이블타이 슬롯
            carrier = carrier.cut(box(sx, y + d / 2 - 2, SO_TOP - 1, sx + 3, y + d / 2 + 2, SO_TOP + 4))
    mod_pos[k] = (mx0, y, w, d, h)
    y += d + 4
add("E03_module_carrier_PETG_66x170", carrier, C_PETG, "PETG", "3D프린트", note="DFR0457 2개는 M3 볼트, 나머지 모듈은 포켓 + 케이블타이")
for k, (mx0, my0, w, d, h) in mod_pos.items():
    z0 = SO_TOP + 3 + (MOS_SPACER if k.startswith("MOS") else 0)
    shp = box(mx0, my0, z0, mx0 + w, my0 + d, z0 + 1.6).union(box(mx0 + 2, my0 + 2, z0 + 1.6, mx0 + min(w, 14), my0 + d - 2, z0 + h)) \
        if k.startswith("MOS") else box(mx0, my0, z0, mx0 + w, my0 + d, z0 + h)
    if k.startswith("MOS"):
        for (_, pts_) in [mb for mb in mos_bolts if mb[0] == k]:
            for p in pts_:
                shp = shp.cut(cyl("z", p, MOS["hole_d"] / 2, z0 - 1, z0 + 3))
    add(f"E04_{k}" + ("_DFR0457" if k.startswith("MOS") else ""), shp, C_PCB if k != "BUZZER" else C_BLK, kind="buy")
for k, pts_ in mos_bolts:
    for i, p in enumerate(pts_):
        z0 = SO_TOP + 3
        add(f"E04_{k}_spacer_{i}", cyl("z", p, 3, z0, z0 + MOS_SPACER).cut(cyl("z", p, 1.6, z0 - 1, z0 + MOS_SPACER + 1)), (0.9, 0.9, 0.9), kind="fastener")
        count("M3 나일론 스페이서 3mm")
        bolt(f"E04_{k}_bolt_{i}", "z", p, z0 + MOS_SPACER + 1.6, -1, 12, spec="M3×12 냄비머리 볼트 (DFR0457)")
        nut(f"E04_{k}_nut_{i}", "z", p, SO_TOP, -1)
for i, (x, y_) in enumerate(car_holes):
    so(f"E03_so_{i}", x, y_, 20)
    bolt(f"E03_bolt_{i}", "z", (x, y_), SO_TOP + 3, -1, 8, spec="M3×8 냄비머리 볼트 (캐리어)")

# 12V 분배: WAGO 221-415 ×4 를 PETG 홀더에 (v2.10, 12P 터미널블록 대체)
WG_X0, WG_Y0 = 148, 203
wg_pitch = WAGO["w"] + 2.2
wg_w = 2 * 8 + WAGO["n"] * wg_pitch
wg_d = WAGO["d"] + 4
wholder = box(WG_X0, WG_Y0, SO_TOP, WG_X0 + wg_w, WG_Y0 + wg_d, SO_TOP + 3)
for i in range(int(WAGO["n"]) + 1):                     # 칸막이 벽
    xw = WG_X0 + 8 + i * wg_pitch - 1.1
    wholder = wholder.union(box(xw, WG_Y0 + 2, SO_TOP + 3, xw + 1.1, WG_Y0 + wg_d - 2, SO_TOP + 12))
wg_holes = [(WG_X0 + 4, WG_Y0 + wg_d / 2), (WG_X0 + wg_w - 4, WG_Y0 + wg_d / 2)]
for p in wg_holes:
    wholder = wholder.cut(cyl("z", p, 1.7, SO_TOP - 1, SO_TOP + 4))
add("E05_WAGO_holder_PETG", wholder, C_PETG, "PETG", "3D프린트", note="WAGO 221-415 4개 칸, 케이블타이로 묶음")
for i in range(int(WAGO["n"])):
    xw = WG_X0 + 8 + i * wg_pitch + 0.05
    add(f"E05_WAGO_221-415_{i+1}", box(xw, WG_Y0 + 2, SO_TOP + 3, xw + WAGO["w"] - 0.1, WG_Y0 + 2 + WAGO["d"], SO_TOP + 3 + WAGO["h"]),
        (0.85, 0.85, 0.85), kind="buy", note="12V 2개, GND 2개")
for i, (x, y_) in enumerate(wg_holes):
    so(f"E05_so_{i}", x, y_, 20)
    bolt(f"E05_bolt_{i}", "z", (x, y_), SO_TOP + 3, -1, 8, spec="M3×8 냄비머리 볼트 (WAGO 홀더)")

# 서모스탯 KSD301 모델 (캡 + 브래킷 + 단자 몸체), axis 방향으로 캡이 향함
def ksd(name, base, axis_dir, color=(0.85, 0.1, 0.1), note=""):
    """base=(x,y,z) 브래킷 캡쪽 면 중심. axis_dir=+1/-1 (x축 방향으로 캡). 브래킷 구멍은 y 방향 ±br_hole_sp/2"""
    bx, by, bz = base
    cap = cyl("x", (by, bz), KSD["cap_d"] / 2, *sorted((bx, bx + axis_dir * KSD["body_h"])))
    x0, x1 = sorted((bx, bx - axis_dir * KSD["br_t"]))
    br = box(x0, by - KSD["br_l"] / 2, bz - 5, x1, by + KSD["br_l"] / 2, bz + 5)
    for sy in (-1, 1):
        br = br.cut(cyl("x", (by + sy * KSD["br_hole_sp"] / 2, bz), 1.7, x0 - 1, x1 + 1))
    tail = KSD["total_h"] - KSD["body_h"] - KSD["br_t"]
    t0, t1 = sorted((bx - axis_dir * KSD["br_t"], bx - axis_dir * (KSD["br_t"] + tail)))
    tabs = box(t0, by - 6, bz - 3, t1, by + 6, bz + 3)
    add(name, cap.union(br).union(tabs), color, kind="buy", note=note)
    return [(by + sy * KSD["br_hole_sp"] / 2, bz) for sy in (-1, 1)], (x0, x1)

# 순환팬 60mm (칸막이 앞면) + PETG 히터 덕트 + PTC 50W
fx, fz = FAN_C
fan_y1 = WALL2_Y0
fan_y0 = fan_y1 - FAN60["t"]
fan60 = box(fx - FAN60["s"] / 2, fan_y0, fz - FAN60["s"] / 2, fx + FAN60["s"] / 2, fan_y1, fz + FAN60["s"] / 2).cut(cyl("y", FAN_C, 28.5, fan_y0 - 1, fan_y1 + 1))
for p in FAN_HOLES:
    fan60 = fan60.cut(cyl("y", p, FAN60["hd"] / 2, fan_y0 - 1, fan_y1 + 1))
add("H01_fan_60mm_4pin_PWM", fan60, C_BLK, kind="buy", note="Evercool EC6025TH12BP")
hd_y_fl = fan_y0 - 6                           # 덕트 플랜지 6T (팬 앞면, M3 인서트 4)
GAP_PTC = 5                                    # PTC 둘레 틈
ptc_x0 = 27                                    # PTC 귀 포함 왼쪽 끝
PTC_Y0 = 165 - PTC["d"] / 2
PTC_Z0 = FAN_C[1] - PTC["h"] / 2
H_X0 = ptc_x0 - 2 - 2.5                        # 하우징 바깥 (왼쪽 2mm 여유 + 벽 2.5)
H_X1 = ptc_x0 + PTC["w"] + 2 + 2.5
H_Z0 = PTC_Z0 - GAP_PTC - 2.5
H_Z1 = PTC_Z0 + PTC["h"] + GAP_PTC + 2.5
H_Y0, H_Y1 = 145, 187
duct = box(fx - 30, hd_y_fl, fz - 30, fx + 30, fan_y0, fz + 30).cut(cyl("y", FAN_C, 28.5, hd_y_fl - 1, fan_y0 + 1))
for p in FAN_HOLES:
    duct = duct.cut(cyl("y", p, 2.0, hd_y_fl - 1, fan_y0 + 1))   # 열압입 인서트
trans = (cq.Workplane("XZ", origin=(0, hd_y_fl, 0)).center(fx, fz).rect(60, 60)
         .workplane(offset=hd_y_fl - H_Y1).center((H_X0 + H_X1) / 2 - fx, (H_Z0 + H_Z1) / 2 - fz).rect(H_X1 - H_X0, H_Z1 - H_Z0).loft())
trans_in = (cq.Workplane("XZ", origin=(0, hd_y_fl + 0.01, 0)).center(fx, fz).rect(55, 55)
            .workplane(offset=hd_y_fl - H_Y1 + 0.02).center((H_X0 + H_X1) / 2 - fx, (H_Z0 + H_Z1) / 2 - fz).rect(H_X1 - H_X0 - 5, H_Z1 - H_Z0 - 5).loft())
duct = duct.union(trans.cut(trans_in))
hous = box(H_X0, H_Y0, H_Z0, H_X1, H_Y1, H_Z1).cut(box(H_X0 + 2.5, H_Y0 - 1, H_Z0 + 2.5, H_X1 - 2.5, H_Y1 + 1, H_Z1 - 2.5))
# 귀 받침 (PTC 양끝 귀 아래, 열압입 인서트)
EAR_HOLES = [(ptc_x0 + PTC["ear_len"] / 2, 165), (ptc_x0 + PTC["w"] - PTC["ear_len"] / 2, 165)]
for ex_ in (ptc_x0, ptc_x0 + PTC["w"] - PTC["ear_len"]):
    hous = hous.union(box(ex_, 155, H_Z0 + 2.5, ex_ + PTC["ear_len"], 175, PTC_Z0))
for p in EAR_HOLES:
    hous = hous.cut(cyl("z", p, 2.0, PTC_Z0 - 5, PTC_Z0 + 1))
    count("M3 열압입 인서트 (L4)")
duct = duct.union(hous)
# 바닥 발 2개 (스탠드오프 15)
H_FEET = [(35, H_Y0 - 4), (110, H_Y0 - 4)]
for (x, y_) in H_FEET:
    ft = box(x - 6, y_ - 6, SO_Z + 15, x + 6, H_Y0, H_Z0 + 2.5)
    ft = ft.cut(cyl("z", (x, y_), 1.7, SO_Z + 14, H_Z0 + 4))
    duct = duct.union(ft)
# 95°C 서모스탯: 하우징 오른쪽 벽 구멍으로 캡을 넣어 PTC 핀 끝면에 밀착
TH95_BASE_X = ptc_x0 + PTC["w"] - PTC["ear_len"] + KSD["body_h"] + 0.1   # 캡 끝 = 핀 블록 끝면 (0.1 띄움)
duct = duct.cut(cyl("x", (165, FAN_C[1]), KSD["cap_d"] / 2 + 0.5, H_X1 - 3, H_X1 + 1))
duct = duct.cut(box(TH95_BASE_X - 0.05, 165 - KSD["br_l"] / 2 - 1, FAN_C[1] - 6, H_X1 + 1, 165 + KSD["br_l"] / 2 + 1, FAN_C[1] + 6))  # 브래킷 자리 (벽 1.8 남김)
th95_holes = [(165 + sy * KSD["br_hole_sp"] / 2, FAN_C[1]) for sy in (-1, 1)]
for p in th95_holes:
    duct = duct.cut(cyl("x", p, 1.7, H_X1 - 3, H_X1 + 1))
add("H02_heater_duct_PETG", duct, C_PETG + (0.85,), "PETG", "3D프린트",
    note="안쪽 알루미늄 테이프. PTC 둘레 5mm 틈. PTC 귀는 받침에 M3, 95°C 서모스탯은 오른쪽 벽")
fin = box(ptc_x0 + PTC["ear_len"], PTC_Y0, PTC_Z0, ptc_x0 + PTC["w"] - PTC["ear_len"], PTC_Y0 + PTC["d"], PTC_Z0 + PTC["h"])
for ex_, p in zip((ptc_x0, ptc_x0 + PTC["w"] - PTC["ear_len"]), EAR_HOLES):
    fin = fin.union(box(ex_, PTC_Y0, PTC_Z0, ex_ + PTC["ear_len"], PTC_Y0 + PTC["d"], PTC_Z0 + PTC["ear_t"])
                    .cut(cyl("z", p, PTC["ear_hole_d"] / 2, PTC_Z0 - 1, PTC_Z0 + 2)))
add("H03_PTC_fin_12V_50W", fin, C_HOT, kind="buy", note="디바이스마트 SZH-PTC002 95×31. 귀 모양·구멍은 도착 후 실측")
for i, p in enumerate(EAR_HOLES):
    bolt(f"H_ptc_bolt_{i}", "z", p, PTC_Z0 + PTC["ear_t"], -1, 6, spec="M3×6 냄비머리 볼트 (PTC 귀)")
ksd("H05_thermostat_KSD301_95C", (TH95_BASE_X, 165, FAN_C[1]), -1, note="NC 95°C. 캡이 핀 블록 끝면에 닿게, 브래킷과 벽 사이 와셔로 조정")
for i, p in enumerate(th95_holes):
    bolt(f"H_th95_bolt_{i}", "x", p, TH95_BASE_X + KSD["br_t"], -1, 8, spec="M3×8 냄비머리 볼트 (서모스탯)")
    nut(f"H_th95_nut_{i}", "x", p, H_X1 - 2.5, -1)
for (x, y_) in H_FEET:
    so(f"H_so_{x}", x, y_, 15)
    bolt(f"H_bolt_{x}", "z", (x, y_), H_Z0 + 2.5, -1, 8, spec="M3×8 냄비머리 볼트 (히터 덕트)")
for i, p in enumerate(FAN_HOLES):
    bolt(f"H_fan_bolt_{i}", "y", p, WALL2_Y1, -1, 35, spec="M3×35 냄비머리 볼트 (칸막이+팬+덕트)")
    count("M3 열압입 인서트 (L4)")

# 출구 배플 (Al 1T, 아래 플랜지)
ob = box(fx - 32, 124, BAY_Z0 + T05, fx + 32, 125, FLOOR_Z - 6).union(box(fx - 32, 125, BAY_Z0 + T05, fx + 32, 137, BAY_Z0 + T05 + 1))
OB_HOLES = [(fx - 20, 131), (fx + 20, 131)]
for p in OB_HOLES:
    ob = ob.cut(cyl("z", p, 1.7, 0, 30))
add("A12_outlet_baffle_Al1T_64x56", ob, C_AL, "알루미늄 1T", "재단+절곡", note="플랜지 12 접기")
for i, (x, y_) in enumerate(OB_HOLES):
    so(f"OB_so_{i}", x, y_, 10)
    bolt(f"OB_bolt_{i}", "z", (x, y_), BAY_Z0 + T05 + 1, -1, 6, spec="M3×6 냄비머리 볼트 (배플)")

# 열 격벽 (Al 1T): 히터 출구 쪽(왼쪽 앞) ↔ ESP32(오른쪽 앞). v2.10: y 40~140, 플랜지 왼쪽
hb_x = 127
hb = box(hb_x, 40, BAY_Z0 + T05, hb_x + 1, 140, FLOOR_Z - 6).union(box(hb_x - 11, 40, BAY_Z0 + T05, hb_x, 140, BAY_Z0 + T05 + 1))
HB_HOLES = [(hb_x - 5.5, 50), (hb_x - 5.5, 130)]
for p in HB_HOLES:
    hb = hb.cut(cyl("z", p, 1.7, 0, 30))
add("A13_heat_baffle_Al1T_100x58", hb, C_AL, "알루미늄 1T", "재단+절곡", note="플랜지 11 접기")
for i, (x, y_) in enumerate(HB_HOLES):
    so(f"HB_so_{i}", x, y_, 10)
    bolt(f"HB_bolt_{i}", "z", (x, y_), BAY_Z0 + T05 + 1, -1, 6, spec="M3×6 냄비머리 볼트 (격벽)")

# DS18B20 (배선에 케이블타이, 플레넘 중앙 공기)
add("E06_DS18B20_probe", cyl("z", (165, 195), 3, 35, 65), (0.6, 0.6, 0.6), kind="buy")
# 65°C 서모스탯: 플레넘 오른쪽 뒤, 캡이 +x(오른벽 쪽)를 향해 공기 중에
TH65_C = (222, 47)                              # 캡이 E08 브래킷(z≤38) 위로 지나가게 z 47                              # (y, z)
th65_bx = IN1 - T05 - 4 - KSD["body_h"]         # 캡 끝이 라이너에서 4mm 떨어지게
st_x1 = th65_bx - KSD["br_t"] - 0.05
st = box(st_x1 - 6, TH65_C[0] - 15, SO_TOP, st_x1, TH65_C[0] + 15, TH65_C[1] + 8) \
    .cut(box(st_x1 - 7, TH65_C[0] - 8, TH65_C[1] - 6, st_x1 + 1, TH65_C[0] + 8, TH65_C[1] + 6))   # 단자 통과창
st = st.union(box(st_x1 - 16, TH65_C[0] - 7, SO_TOP, st_x1, TH65_C[0] + 7, SO_TOP + 3))
st_hole = (st_x1 - 11, TH65_C[0])
st = st.cut(cyl("z", st_hole, 1.7, SO_TOP - 1, SO_TOP + 4))
th65_holes = [(TH65_C[0] + sy * KSD["br_hole_sp"] / 2, TH65_C[1]) for sy in (-1, 1)]
for p in th65_holes:
    st = st.cut(cyl("x", p, 1.7, st_x1 - 7, st_x1 + 1))
add("E07_thermostat65_stand_PETG", st, C_PETG, "PETG", "3D프린트")
ksd("E07_thermostat_KSD301_65C", (th65_bx, TH65_C[0], TH65_C[1]), +1, note="NC 65°C, 플레넘 공기")
for i, p in enumerate(th65_holes):
    bolt(f"E07_th_bolt_{i}", "x", p, th65_bx, -1, 10, spec="M3×10 냄비머리 볼트 (서모스탯)")
    nut(f"E07_th_nut_{i}", "x", p, st_x1 - 6, -1)
so("E07_so", st_hole[0], st_hole[1], 20)
bolt("E07_bolt", "z", st_hole, SO_TOP + 3, -1, 8, spec="M3×8 냄비머리 볼트 (서모스탯 받침)")

# 칸막이 고정 L브래킷 2 (PETG)
for x in (25, 275):
    lb = box(x - 6, WALL2_Y0 - 14, SO_Z + 10.5, x + 6, WALL2_Y0, SO_Z + 13.5).union(box(x - 6, WALL2_Y0 - 3, SO_Z + 13.5, x + 6, WALL2_Y0, SO_Z + 33))
    lb = lb.cut(cyl("z", (x, WALL2_Y0 - 8), 1.7, 0, 30))
    add(f"E08_partition_bracket_{x}", lb, C_PETG, "PETG", "3D프린트", note="세운 다리는 칸막이에 PVC본드")
    so(f"E08_so_{x}", x, WALL2_Y0 - 8, 10)
    bolt(f"E08_bolt_{x}", "z", (x, WALL2_Y0 - 8), SO_Z + 13.5, -1, 6, spec="M3×6 냄비머리 볼트 (칸막이 브래킷)")

# 뒷판 부착물 (복귀실 안쪽): 전원 케이블 글랜드, 마이크로USB, 로커 스위치
gl = cyl("y", GLAND_C, 6.0, OUT - WALL - 6, OUT + 3)                                   # 나사부
gl = gl.union(hexprism((0, 0), 19, 0, 3).rotate((0, 0, 0), (1, 0, 0), -90).translate((GLAND_C[0], OUT, GLAND_C[1])))
gl = gl.union(cyl("y", GLAND_C, 7.5, OUT + 3, OUT + 15))                              # 돔 캡
gl = gl.union(cyl("y", GLAND_C, PWR["nut_od"] / 2, OUT - WALL - 5, OUT - WALL))         # 안쪽 너트
gl = gl.cut(cyl("y", GLAND_C, 2.6, OUT - WALL - 7, OUT + 16))
add("E09_cable_gland_PG7", gl, C_BLK, kind="buy", note="어댑터 플러그를 잘라 케이블만 통과, 안에서 퓨즈홀더→WAGO")
add("E09_adapter_cable", cyl("y", GLAND_C, 2.5, OUT - WALL - 25, OUT + 40), (0.1, 0.1, 0.1), kind="buy")
usb = box(USB_C[0] - 12.85, OUT - WALL - 2, USB_C[1] - 4.9, USB_C[0] + 12.85, OUT - WALL, USB_C[1] + 4.9)     # 귀 판 25.7×9.8
for p in USB_HOLES:
    usb = usb.cut(cyl("y", p, 1.5, OUT - WALL - 3, OUT))
usb = usb.union(box(USB_C[0] - 5, OUT - WALL - 29.8, USB_C[1] - 4, USB_C[0] + 5, OUT - WALL - 2, USB_C[1] + 4))
usb = usb.union(box(USB_C[0] - 4.5, OUT - WALL, USB_C[1] - 2.3, USB_C[0] + 4.5, OUT - WALL + 1.0, USB_C[1] + 2.3))
add("E09_microUSB_panel_mount_ada3258", usb, C_BLK, kind="buy", note="Adafruit 3258 STEP 기준 외형")
for i, p in enumerate(USB_HOLES):
    bolt(f"E09_usb_bolt_{i}", "y", p, OUT, -1, 12, spec="M3×12 냄비머리 볼트 (USB)")
    nut(f"E09_usb_nut_{i}", "y", p, OUT - WALL - 2, -1)
add("E09_rocker_switch_KCD1", box(SW_C[0] - 9.5, OUT - 22, SW_C[1] - 6.4, SW_C[0] + 9.5, OUT - 1, SW_C[1] + 6.4)
    .union(box(SW_C[0] - 10.5, OUT, SW_C[1] - 7.5, SW_C[0] + 10.5, OUT + 2, SW_C[1] + 7.5)), C_BLK, kind="buy",
    note="뒷판 안쪽 카운터보어로 판 1mm만 남겨 스냅 고정")

# 바닥판·바닥폼·라이너에 스탠드오프 구멍
for (x, y_, L) in SO_HOLES:
    bottom = bottom.cut(cyl("z", (x, y_), 1.7, -1, WALL + 1))
    bottom = bottom.cut(cq.Workplane("XY").circle(3.0).workplane(offset=1.7).circle(1.7).loft().translate((x, y_, -0.01)))  # 접시 자리
add("P06_bottom_plate_foamex5T", bottom, C_FOAMEX, "포맥스 5T", "재단")
# 폼/라이너 구멍은 이미 add 된 shape 를 갱신
def recut(name, tool):
    for p in PARTS:
        if p["name"] == name:
            p["shape"] = p["shape"].cut(tool)
for (x, y_, L) in SO_HOLES:
    recut("F01_foam_bottom_270x270", cyl("z", (x, y_), 4, 0, 20))
    recut("A01_liner_bay_bottom_270x270", cyl("z", (x, y_), 3.5 if L > 11 else 1.7, 0, 20))
add("P07_top_plate_foamex5T", top_saved, C_FOAMEX, "포맥스 5T", "재단")

# ============================================================
# 12. 2차 펠티어 (참조, phase=2) + 1차 막음 폼
# ============================================================
for n, z0 in ((1, PELT_Z[0]), (2, PELT_Z[1])):
    add(f"F05_phase1_peltier_plug_foam_{n}", box(CH_CX - 20, OUT - IN0, z0, CH_CX + 20, OUT, z0 + 40), C_FOAM, "폼보드 10T+5T", "재단",
        note="1차: 뒷판 펠티어 구멍 막음")
    add(f"X_P2_TEC1-12706_{n}", box(CH_CX - 20, OUT - 4, z0, CH_CX + 20, OUT - 0.2, z0 + 40), C_P2, phase=2, kind="buy")
    add(f"X_P2_Al_spacer_{n}", box(CH_CX - 20, IN1 - T05 - 0.1 - 0.1, z0, CH_CX + 20, OUT - 4, z0 + 40), C_P2, phase=2, kind="buy")
    add(f"X_P2_cold_heatsink_{n}", box(CH_CX - 20, IN1 - 22, z0, CH_CX + 20, IN1 - T05 - 0.2, z0 + 40), C_P2, phase=2, kind="buy")
add("X_P2_hot_heatsink_90x120x25", box(CH_CX - 45, OUT + 0.2, 95, CH_CX + 45, OUT + 25, 215), C_P2, phase=2, kind="buy")
add("X_P2_fan_120mm", box(CH_CX - 60, OUT + 25, 95, CH_CX + 60, OUT + 50, 215), C_P2, phase=2, kind="buy")
add("X_P2_XL4016_buck", box(214, 200 - 0, SO_TOP + 3, 252, 200 + 0.1, SO_TOP + 4), C_P2, phase=2, kind="buy",
    note="자리: 캐리어 판 옆, 2차 때 배치")

# ============================================================
# 13. 저장
# ============================================================
# Fusion 브라우저에서 폴더(하위 컴포넌트)로 보이도록 STEP을 2단 어셈블리로 저장한다.
# 그룹 이름은 STEP 호환을 위해 영문 + 번호(정렬용). 한글 설명은 docs/naming.md.
GROUPS = [   # (그룹, 이 접두어로 시작하는 부품) — 위에서부터 먼저 맞는 것
    ("01_shell_foamex",        ("P01", "P02", "P03", "P06", "P07", "B0")),
    ("02_insulation_foam",     ("F0",)),
    ("03_liner_Al",            ("A01", "A02", "A03", "A04", "A05", "A06", "A07")),
    ("04_partition_floor",     ("P04", "P05", "A10", "A12", "A13")),
    ("05_door",                ("D0",)),
    ("06_heater",              ("H0",)),
    ("07_intake",              ("I0",)),
    ("08_electronics",         ("E",)),
    ("09_loadcell_tray",       ("L0", "A11", "T0")),
    ("10_sensors_ceiling",     ("S0",)),
    ("11_sensors_chamber",     ("C0",)),
]
FASTENER_GROUP = "90_fasteners"
P2_GROUP = "99_phase2_peltier"

def group_of(p):
    if p["phase"] == 2:
        return P2_GROUP
    if p["kind"] == "fastener":
        return FASTENER_GROUP
    for g, prefixes in GROUPS:
        if p["name"].startswith(prefixes):
            return g
    return "98_other"

def build_assembly(include_p2=True):
    asm = cq.Assembly(name="herb_dryer")
    subs = {}
    order = [g for g, _ in GROUPS] + ["98_other", FASTENER_GROUP, P2_GROUP]
    for g in order:
        subs[g] = cq.Assembly(name=g)
    for p in PARTS:
        if p["phase"] == 2 and not include_p2:
            continue
        col = p["color"]
        subs[group_of(p)].add(p["shape"], name=p["name"], color=cq.Color(*col) if len(col) == 4 else cq.Color(*col, 1.0))
    for g in order:
        if subs[g].children:
            asm.add(subs[g], name=g)
    return asm

REPO = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    import json, sys
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "build"
    outdir.mkdir(parents=True, exist_ok=True)
    build_assembly().export(str(outdir / "herb_dryer.step"))
    print("STEP saved, parts:", len(PARTS), "perforation holes:", N_PERF)
    json.dump(FASTENERS, open(outdir / "fasteners.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
