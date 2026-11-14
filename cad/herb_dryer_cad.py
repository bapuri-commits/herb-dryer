"""
허브 건조기 v3.1 — 제작용 CadQuery 모델 (버전별 변경은 CHANGELOG.md)
좌표: X=폭(좌→우), Y=깊이(앞=0 → 뒤=300), Z=높이(바닥=0). 단위 mm.

v3.0 (메이저): 회로를 본체 오른쪽 측면 박스(K)로 분리, 공기 경로는 알루미늄·스테인리스·팬·PTC·센서만.
펠티어(2차) 완전 제외, 덕트 깊이 20, 칸막이·덕트 벽·히터 덕트 알루미늄화, 흡기를 뒷판(복귀실)으로.
v3.1: TCS34725·LED·천장 센서 인서트·부저 삭제, 전장부 관통구를 PG9 전력/신호 2개로 분리,
흡기: 활성탄을 뒷판 바깥 커버(차가운 쪽)로, BME688 #2를 관 옆벽 홈(흐름과 나란히), 출구-칸막이 20mm.

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
PTC = PARAMS["PTC"]                            # [실측] PTC 핀 (w=귀 포함 길이 x, d=공기 방향 y, h=높이 z). 100W 도착 후 실측
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
# v3.0 배치 상수
PART_Y0, PART_Y1 = 240, 241                    # 전장부 칸막이 (알루미늄 1T)
DUCT_W0, DUCT_W1 = 263.5, 264.5                # 덕트 벽 (알루미늄 1T, 바닥판 위). 덕트 깊이 20
CH_CY = (IN0 + T05 + DUCT_W0) / 2              # 챔버 중심 y (139.5)
SB_X0, SB_X1 = OUT, OUT + 95                   # 측면 박스 (본체 오른쪽, 폭 95)
BP_X0, BP_X1 = OUT, OUT + WALL                 # 측면 박스 세로 장착판 (본체 옆판 바깥면에 접착)

# 오른쪽 옆판 관통구 (y, z) — 본체 ↔ 측면 박스
PT1P = (22, 33)           # 전장부 전력: PTC 2, 팬 전원 4 (PG9)
PT1S = (42, 57)           # 전장부 신호: 팬 PWM·타코 4, DS18B20 3, 로드셀 4, BME688 #2 4 (PG9)
PG9 = PARAMS["PG9"]                       # PG9 글랜드: 장착 구멍, 너트 외경 (params.yaml)
PT3 = (215, 237)          # 전실: BME688 #1 (PG7)
PT4 = (165, 170)          # 챔버: SHT31 (PG7)
PTS = (PT1P, PT1S, PT3, PT4)
def gl_d(p): return PG9["d"] if p in (PT1P, PT1S) else PWR["gland_d"]
def gl_nut(p): return PG9["nut_od"] if p in (PT1P, PT1S) else PWR["nut_od"]
SHT_P = (CH_CY, 170)      # SHT31 홀더 관통 볼트 (오른벽)
BME1_P = (250, 237)       # BME688 #1 홀더 관통 볼트 (오른벽, 덕트 위 전실)
LC_TOP = FLOOR_TOP + 15 + PARAMS["LC"]["s"] + 20 + 1 + 4    # 트레이 받침판 윗면 (로드셀 블록·차폐판 포함)
TRAY_TOP = LC_TOP + 10                         # 트레이 프레임 윗면
STRIP_Z = TRAY_TOP                             # 트레이 옆 틈막이 높이
STRIP_BOLTS_Y = (70, 200)
DUCTANG_Z = (120, 190)                         # 덕트 벽 옆 앵글 관통 볼트
DUCTANG_Y = DUCT_W0 - 5

SIDE_BOLTS_Y = (30, OUT - 30)
def side_wall(x0, right):
    w = box(x0, 0, 0, x0 + WALL, OUT, WALL_H)
    for y in SIDE_BOLTS_Y:
        w = w.cut(cyl("x", (y, 10), 1.7, x0 - 1, x0 + WALL + 1))
    for y in STRIP_BOLTS_Y:
        w = w.cut(cyl("x", (y, STRIP_Z - 5), 1.7, x0 - 1, x0 + WALL + 1))
    for z in DUCTANG_Z:
        w = w.cut(cyl("x", (DUCTANG_Y, z), 1.7, x0 - 1, x0 + WALL + 1))
    if right:
        for p in PTS:
            w = w.cut(cyl("x", p, gl_d(p) / 2, x0 - 1, x0 + WALL + 1))
        for p in (SHT_P, BME1_P):
            w = w.cut(cyl("x", p, 1.7, x0 - 1, x0 + WALL + 1))
    return w
side_L = add("P01_side_L_foamex5T", side_wall(0, False), C_FOAMEX, "포맥스 5T", "재단")
side_R = add("P01_side_R_foamex5T", side_wall(OUT - WALL, True), C_FOAMEX, "포맥스 5T", "재단",
             note="관통구 4(PG9 2 + PG7 2, 측면 박스), 센서 홀더 볼트 2")

# 앞판: 290 × 265 — v3.0: 문 개구부·경첩·자석만 (흡기·LCD·버튼 없음)
front = box(WALL, 0, 0, OUT - WALL, WALL, WALL_H)
door_cut = box(DOOR_X0, -1, DOOR_Z0, DOOR_X1, SKIN + 1, DOOR_Z1)
front = front.cut(door_cut)
HINGE_Z = (DOOR_Z0 + 25, DOOR_Z1 - 50)   # 경첩 하단 z
def hinge_hole_pts(z0):
    zc = z0 + HINGE["L"] / 2
    return [(HINGE["pin_x"] + HINGE["hole_off"], zc - HINGE["hole_sp"] / 2),
            (HINGE["pin_x"] + HINGE["hole_off"], zc + HINGE["hole_sp"] / 2)]
for z0 in HINGE_Z:
    for p in hinge_hole_pts(z0):
        front = front.cut(cyl("y", p, 1.7, -1, WALL + 1))
MAG = PARAMS["MAG"]
MAG_X = 290.0; MAG_Z = (110, 166, 222); MAG_D = MAG["d"]   # 8×3 네오디뮴 (params.yaml)
for mz in MAG_Z:
    front = front.cut(cyl("y", (MAG_X, mz), MAG_D / 2, -1, MAG["t"]))
add("P02_front_foamex5T", front, C_FOAMEX, "포맥스 5T", "재단")

# 뒷판: 290 × 265 — v3.0: 흡기 입구만 (복귀실 직결)
back = box(WALL, OUT - WALL, 0, OUT - WALL, OUT, WALL_H)
INTAKE_C = (220, 45)                                # 흡기팬 중심 (x, z), 복귀실 높이
back = back.cut(cyl("y", INTAKE_C, 19, OUT - WALL - 1, OUT + 1))
INTAKE_HOLES = [(INTAKE_C[0] + sx * FAN40["hole"] / 2, INTAKE_C[1] + sz * FAN40["hole"] / 2) for sx in (-1, 1) for sz in (-1, 1)]
COVER_PTS = [(INTAKE_C[0] - 25, INTAKE_C[1] + 25), (INTAKE_C[0] + 25, INTAKE_C[1] - 25)]   # 활성탄 커버 볼트
for p in INTAKE_HOLES + COVER_PTS:
    back = back.cut(cyl("y", p, 1.7, OUT - WALL - 1, OUT + 1))
add("P03_back_foamex5T", back, C_FOAMEX, "포맥스 5T", "재단")

# 바닥판: 289 × 289
bottom = box(WALL + 0.5, WALL + 0.5, 0, OUT - WALL - 0.5, OUT - WALL - 0.5, WALL)
DRAIN = (CH_CX, 275)
bottom = bottom.cut(cyl("z", DRAIN, 4, -1, WALL + 1))

# 천장판: 300 × 300
top = box(0, 0, WALL_H, OUT, OUT, OZ)
EXH = (CH_CX - 20, 245, CH_CX + 20, 285)           # 배기 개구 40×40 (덕트 위 전실)
top = top.cut(box(EXH[0], EXH[1], WALL_H - 1, EXH[2], EXH[3], OZ + 1))
TOP_SCREWS = [(10, 10), (OUT - 10, 10), (10, OUT - 10), (OUT - 10, OUT - 10)]
for p in TOP_SCREWS:
    top = top.cut(cyl("z", p, 1.7, WALL_H - 1, OZ + 1))
top_saved = top

# ============================================================
# 3. 단열 폼 10T + 링 영역 블록
# ============================================================
foam_bot = box(IN0, IN0, WALL, IN1, IN1, IN0).cut(cyl("z", DRAIN, 4, 0, 20))
foam_top = box(IN0, IN0, LID_Z, IN1, IN1, LID_Z + INS)
foam_top = foam_top.cut(box(EXH[0], EXH[1], LID_Z - 1, EXH[2], EXH[3], LID_Z + INS + 1))

foam_L = box(WALL, WALL, IN0, IN0, OUT - WALL, LID_Z)
foam_R = box(IN1, WALL, IN0, OUT - WALL, OUT - WALL, LID_Z)
foam_F = box(IN0, WALL, IN0, IN1, IN0, LID_Z).cut(door_cut)
foam_B = box(IN0, OUT - IN0, IN0, IN1, OUT - WALL, LID_Z)
foam_B = foam_B.cut(box(INTAKE_C[0] - 29, OUT - IN0 - 1, INTAKE_C[1] - 29, INTAKE_C[0] + 29, OUT - WALL + 1, INTAKE_C[1] + 29))
def side_foam_cuts(fm, xa, xb, right):
    for y in STRIP_BOLTS_Y:
        fm = fm.cut(cyl("x", (y, STRIP_Z - 5), 4, xa - 1, xb + 1))
    for z in DUCTANG_Z:
        fm = fm.cut(cyl("x", (DUCTANG_Y, z), 4, xa - 1, xb + 1))
    if right:
        for p in PTS:
            fm = fm.cut(cyl("x", p, gl_nut(p) / 2 + 2, xa - 1, xb + 1))
        for p in (SHT_P, BME1_P):
            fm = fm.cut(cyl("x", p, 4, xa - 1, xb + 1))
    return fm
foam_L = side_foam_cuts(foam_L, WALL, IN0, False)
foam_R = side_foam_cuts(foam_R, IN1, OUT - WALL, True)
for z0 in HINGE_Z:
    for p in hinge_hole_pts(z0):
        foam_L = foam_L.cut(cyl("y", p, 4, WALL - 1, WALL + 4))

add("F01_foam_bottom_270x270", foam_bot, C_FOAM, "폼보드 10T", "재단")
add("F02_foam_lid_270x270", foam_top, C_FOAM, "폼보드 10T", "재단")
add("F03_foam_side_L_290x240", foam_L, C_FOAM, "폼보드 10T", "재단")
add("F03_foam_side_R_290x240", foam_R, C_FOAM, "폼보드 10T", "재단")
add("F04_foam_front_270x240", foam_F, C_FOAM, "폼보드 10T", "재단")
add("F04_foam_back_270x240", foam_B, C_FOAM, "폼보드 10T", "재단")

for i, x0 in enumerate((WALL + 0.5, OUT - IN0)):
    for y in SIDE_BOLTS_Y:
        blk = box(x0, y - 15, WALL, x0 + 9.5, y + 15, IN0).cut(cyl("x", (y, 10), 2.0, x0 - 1, x0 + 10.5))
        add(f"B01_nut_block_bottom_{'L' if i == 0 else 'R'}_{y}", blk, C_PETG, "PETG", "3D프린트",
            note="M3 열압입 인서트 Ø4.0 구멍")
        count("M3 열압입 인서트 (L4)")
        xh = 0 if i == 0 else OUT
        bolt(f"B01_bolt_{i}_{y}", "x", (y, 10), xh, +1 if i == 0 else -1, 10)
for (x, y) in TOP_SCREWS:
    blk = box(x - 5, y - 5, LID_Z, x + 5, y + 5, WALL_H).cut(cyl("z", (x, y), 2.0, LID_Z + 2, WALL_H + 1))
    add(f"B02_corner_block_top_{x}_{y}", blk, C_PETG, "PETG", "3D프린트", note="M3 인서트, 옆판에 PVC본드")
    count("M3 열압입 인서트 (L4)")
    bolt(f"B02_bolt_{x}_{y}", "z", (x, y), OZ, -1, 10)

# ============================================================
# 4. 알루미늄 라이너 0.5T
# ============================================================
z_ch0 = FLOOR_TOP + LINER_GAP          # 83
liners = {}
liners["A01_liner_bay_bottom_270x270"] = box(IN0, IN0, IN0, IN1, IN1, IN0 + T05).cut(cyl("z", DRAIN, 4, 0, 20))
liners["A02_liner_bay_L_270x64.5"] = box(IN0, IN0, IN0 + T05, IN0 + T05, IN1, FLOOR_Z)
liners["A02_liner_bay_R_270x64.5"] = box(IN1 - T05, IN0, IN0 + T05, IN1, IN1, FLOOR_Z).cut(cyl("x", PT1P, 5, IN1 - 2, IN1 + 1)).cut(cyl("x", PT1S, 5, IN1 - 2, IN1 + 1))
liners["A03_liner_bay_front_269x64.5"] = box(IN0 + T05, IN0, IN0 + T05, IN1 - T05, IN0 + T05, FLOOR_Z)   # v3.0 복구
liners["A03_liner_bay_back_269x64.5"] = box(IN0 + T05, IN1 - T05, IN0 + T05, IN1 - T05, IN1, FLOOR_Z) \
    .cut(box(INTAKE_C[0] - 25, IN1 - 2, INTAKE_C[1] - 25, INTAKE_C[0] + 25, IN1 + 1, INTAKE_C[1] + 25))
def ch_side(x0, x1, right):
    l = box(x0, IN0, z_ch0, x1, IN1, LID_Z - T05)
    for y in STRIP_BOLTS_Y:
        l = l.cut(cyl("x", (y, STRIP_Z - 5), 1.7, x0 - 1, x1 + 1))
    for z in DUCTANG_Z:
        l = l.cut(cyl("x", (DUCTANG_Y, z), 1.7, x0 - 1, x1 + 1))
    if right:
        for p in (PT3, PT4):
            l = l.cut(cyl("x", p, 5, x0 - 1, x1 + 1))
        for p in (SHT_P, BME1_P):
            l = l.cut(cyl("x", p, 1.7, x0 - 1, x1 + 1))
    return l
liners["A04_liner_ch_L_270x171.5"] = ch_side(IN0, IN0 + T05, False)
liners["A04_liner_ch_R_270x171.5"] = ch_side(IN1 - T05, IN1, True)
liners["A06_liner_duct_back_269x174.5"] = box(IN0 + T05, IN1 - T05, FLOOR_Z, IN1 - T05, IN1, LID_Z - T05)
ceil = box(IN0, IN0, LID_Z - T05, IN1, IN1, LID_Z)
ceil = ceil.cut(box(EXH[0], EXH[1], LID_Z - 2, EXH[2], EXH[3], LID_Z + 1))
liners["A07_liner_ceiling_270x270"] = ceil
for n, s_ in liners.items():
    add(n, s_, C_AL + (0.65,), "알루미늄 0.5T", "재단")

# ============================================================
# 5. 칸막이(전장부)·덕트 벽(챔버 뒤) — v3.0: 알루미늄 1T, 두 장으로 분리
# ============================================================
SO_HOLES = []
def so(name, x, y, L):
    SO_HOLES.append((x, y, L))
    return standoff(name, x, y, L)

FAN_C = (65, 48)
FAN_HOLES = [(FAN_C[0] + sx * FAN60["hole"] / 2, FAN_C[1] + sz * FAN60["hole"] / 2) for sx in (-1, 1) for sz in (-1, 1)]
part = box(IN0 + T05, PART_Y0, IN0 + T05, IN1 - T05, PART_Y1, FLOOR_Z)
part = part.cut(cyl("y", FAN_C, 28.5, PART_Y0 - 1, PART_Y1 + 1))
for p in FAN_HOLES:
    part = part.cut(cyl("y", p, 1.7, PART_Y0 - 1, PART_Y1 + 1))
WIRE_PASS = (250, 30)                         # 복귀실(흡기팬·BME688 #2) → 플레넘 배선 (그로밋)
part = part.cut(cyl("y", WIRE_PASS, 6, PART_Y0 - 1, PART_Y1 + 1))
add("A15_bay_partition_Al1T_269x64.5", part, C_AL, "알루미늄 1T", "재단",
    note="플레넘/복귀실 칸막이. 아래 앵글 2개로 스탠드오프에 고정, 둘레는 중성 실리콘")
PANG_X = (110, 220)
for i, x in enumerate(PANG_X):
    a = box(x - 10, PART_Y0 - 10, IN0 + T05, x + 10, PART_Y0, IN0 + T05 + 1) \
        .union(box(x - 10, PART_Y0 - 1, IN0 + T05 + 1, x + 10, PART_Y0, IN0 + T05 + 10))
    a = a.cut(cyl("z", (x, PART_Y0 - 5), 1.7, 0, 30))
    add(f"A18_partition_angle_{i+1}", a, C_AL, "알루미늄 앵글 10×10×1", "재단", note="길이 20, 세운 다리는 칸막이에 리벳 또는 실리콘")
    so(f"A18_so_{i}", x, PART_Y0 - 5, 10)
    bolt(f"A18_bolt_{i}", "z", (x, PART_Y0 - 5), IN0 + T05 + 1, -1, 6, spec="M3×6 냄비머리 볼트 (칸막이 앵글)")

DUCT_TOP = LID_Z - 35                         # 220
dwall = box(IN0 + T05 + 1, DUCT_W0, FLOOR_Z - 1, IN1 - T05 - 1, DUCT_W1, DUCT_TOP)
add("A16_duct_wall_Al1T_267x141", dwall, C_AL, "알루미늄 1T", "재단",
    note="챔버 뒤 덕트 벽(덕트 깊이 20). 양옆 세로 앵글에 리벳, 아래 앵글은 타공판 뒤쪽 받침")
for side, xa in (("L", IN0 + T05), ("R", IN1 - T05 - 10)):
    # 세로 앵글: 한 다리는 옆 라이너, 한 다리는 덕트 벽 앞면
    xin = xa if side == "L" else xa + 9
    va = box(xin, DUCT_W0 - 10, FLOOR_Z + 1, xin + 1, DUCT_W0, DUCT_TOP) \
        .union(box(xa, DUCT_W0 - 1, FLOOR_Z + 1, xa + 10, DUCT_W0, DUCT_TOP))
    for z in DUCTANG_Z:
        va = va.cut(cyl("x", (DUCTANG_Y, z), 1.7, xin - 1, xin + 2))
    add(f"A19_duct_wall_angle_{side}", va, C_AL, "알루미늄 앵글 10×10×1", "재단", note="길이 139")
    for j, z in enumerate(DUCTANG_Z):
        if side == "L":
            bolt(f"A19_bolt_L_{j}", "x", (DUCTANG_Y, z), 0, +1, 20)
            nut(f"A19_nut_L_{j}", "x", (DUCTANG_Y, z), xin + 1, +1)
        else:
            bolt(f"A19_bolt_R_{j}", "x", (DUCTANG_Y, z), OUT, -1, 20)
            nut(f"A19_nut_R_{j}", "x", (DUCTANG_Y, z), xin, -1)
ba = box(IN0 + T05 + 11, DUCT_W0 - 10, FLOOR_Z - 1, IN1 - T05 - 11, DUCT_W0, FLOOR_Z) \
    .union(box(IN0 + T05 + 11, DUCT_W0 - 1, FLOOR_Z - 10, IN1 - T05 - 11, DUCT_W0, FLOOR_Z - 1))
add("A20_duct_floor_angle", ba, C_AL, "알루미늄 앵글 10×10×1", "재단", note="길이 247, 덕트 벽 아래 앞면에 리벳. 타공판 뒤쪽 받침")

# 타공판 받침 앵글 (앞·왼·오) — v3.0: 포맥스 띠 → 알루미늄 앵글
def ledge_angle(name, x0, y0, x1, y1, leg_side):
    hz = box(x0, y0, FLOOR_Z - 1, x1, y1, FLOOR_Z)
    if leg_side == "F":
        v = box(x0, y0, FLOOR_Z - 10, x1, y0 + 1, FLOOR_Z - 1)
    elif leg_side == "L":
        v = box(x0, y0, FLOOR_Z - 10, x0 + 1, y1, FLOOR_Z - 1)
    else:
        v = box(x1 - 1, y0, FLOOR_Z - 10, x1, y1, FLOOR_Z - 1)
    add(name, hz.union(v), C_AL, "알루미늄 앵글 10×10×1", "재단", note="라이너에 중성 실리콘")
ledge_angle("A17_floor_angle_F", IN0 + T05, IN0 + T05, IN1 - T05, IN0 + T05 + 10, "F")
ledge_angle("A17_floor_angle_L", IN0 + T05, IN0 + T05 + 10, IN0 + T05 + 10, PART_Y0, "L")
ledge_angle("A17_floor_angle_R", IN1 - T05 - 10, IN0 + T05 + 10, IN1 - T05, PART_Y0, "R")
ledge_angle("A17_floor_angle_LB", IN0 + T05, PART_Y1, IN0 + T05 + 10, DUCT_W0 - 10, "L")
ledge_angle("A17_floor_angle_RB", IN1 - T05 - 10, PART_Y1, IN1 - T05, DUCT_W0 - 10, "R")

# ============================================================
# 6. 타공판 + 로드셀 + 트레이 (스테인리스 메시 + 알루미늄 앵글 프레임)
# ============================================================
fl_x0, fl_x1 = IN0 + T05 + 0.5, IN1 - T05 - 0.5
fl_y0, fl_y1 = IN0 + T05 + 0.5, DUCT_W0 - 0.5
floor = box(fl_x0, fl_y0, FLOOR_Z, fl_x1, fl_y1, FLOOR_TOP)
LC_X0 = CH_CX - LC["L"] / 2
LZ_X, LZ_Y = 62, 32                                    # 로드셀 자리(막힘) 반폭
pts, pts5 = [], []
for x in range(int(fl_x0) + 15, int(fl_x1) - 12, 10):
    for y in range(int(fl_y0) + 15, PART_Y0 - 4, 10):  # 복귀실 위(칸막이 뒤)는 막힘
        dx, dy = abs(x - CH_CX), abs(y - CH_CY)
        if dx < LZ_X and dy < LZ_Y:
            continue
        (pts5 if (dx < LZ_X + 10 and dy < LZ_Y + 10) else pts).append((x, y))
N_PERF = len(pts) + len(pts5)
floor = floor.cut(cq.Workplane("XY").workplane(offset=FLOOR_Z - 1).pushPoints(pts).circle(2).extrude(FLOOR_T + 2))
floor = floor.cut(cq.Workplane("XY").workplane(offset=FLOOR_Z - 1).pushPoints(pts5).circle(2.5).extrude(FLOOR_T + 2))
LC_CABLE = (LC_X0 - 8, CH_CY)
floor = floor.cut(cyl("z", LC_CABLE, 3, FLOOR_Z - 1, FLOOR_TOP + 1))
lc_base_holes = [(LC_X0 + LC["hole_end"], CH_CY), (LC_X0 + LC["hole_end"] + LC["hole_sp"], CH_CY)]
lc_tray_holes = [(LC_X0 + LC["L"] - LC["hole_end"], CH_CY), (LC_X0 + LC["L"] - LC["hole_end"] - LC["hole_sp"], CH_CY)]
for p in lc_base_holes:
    floor = floor.cut(cyl("z", p, 2.25, FLOOR_Z - 1, FLOOR_TOP + 1))
add("A10_perforated_floor_Al1T", floor, C_AL, "알루미늄 1T", "재단+타공",
    note=f"Ø4 {len(pts)}개 + 로드셀 자리 둘레 Ø5 {len(pts5)}개, 10mm 피치. 칸막이 뒤(y>236)는 막힘")

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
    tray_blk = tray_blk.cut(cyl("z", p, 3.75, tz0 + blk_h2 - 4, tz0 + blk_h2 + 1))
add("L03_loadcell_tray_block", tray_blk, C_PETG, "PETG", "3D프린트")
for i, p in enumerate(lc_base_holes):
    bolt(f"L_bolt_base_{i}", "z", p, FLOOR_Z, +1, 25, d=4, spec="M4×25 냄비머리 볼트 (로드셀) [실측: M4/M5]")
for i, p in enumerate(lc_tray_holes):
    bolt(f"L_bolt_tray_{i}", "z", p, tz0 + blk_h2 - 4, -1, 30, d=4, head="flat",
         spec="M4×30 볼트 (로드셀, 머리 묻힘) [실측: M4/M5]")
sz0 = tz0 + blk_h2
add("A11_loadcell_shield_Al1T_100x40", box(CH_CX - 50, CH_CY - 20, sz0, CH_CX + 50, CH_CY + 20, sz0 + 1), C_AL, "알루미늄 1T", "재단")
hub_z0 = sz0 + 1
PIN_X = (CH_CX - 40, CH_CX + 40)
hub = box(CH_CX - 50, CH_CY - 20, hub_z0, CH_CX + 50, CH_CY + 20, hub_z0 + 4)
for x in PIN_X:
    hub = hub.union(cyl("z", (x, CH_CY), 2.5, hub_z0 + 4, hub_z0 + 8))
add("L04_tray_platform_PETG_100x40", hub, C_PETG, "PETG", "3D프린트",
    note="차폐판과 함께 트레이 블록 윗면에 접착. 위치 핀 Ø5 2개")
assert abs(hub_z0 + 4 - LC_TOP) < 1e-6

TRAY_X = 245                                   # 문 개구부 260 때문에 고정
TRAY_Y = DUCT_W0 - (IN0 + T05) - 4             # 앞뒤 틈 2mm
tx0, ty0 = CH_CX - TRAY_X / 2, IN0 + T05 + 2
tz = LC_TOP
outer = box(tx0, ty0, tz, tx0 + TRAY_X, ty0 + TRAY_Y, tz + 10)
frame = outer.cut(box(tx0 + 1, ty0 + 1, tz + 1, tx0 + TRAY_X - 1, ty0 + TRAY_Y - 1, tz + 11)) \
    .cut(box(tx0 + 10, ty0 + 10, tz - 1, tx0 + TRAY_X - 10, ty0 + TRAY_Y - 10, tz + 2))
frame = frame.union(box(tx0, CH_CY - 5, tz, tx0 + TRAY_X, CH_CY + 5, tz + 1)) \
    .union(box(CH_CX - 5, ty0, tz, CH_CX + 5, ty0 + TRAY_Y, tz + 1))
for x in PIN_X:
    frame = frame.cut(cyl("z", (x, CH_CY), 2.8, tz - 1, tz + 2))
add("T03_tray_frame_Al_angle", frame, C_AL, "알루미늄 앵글 10×10×1 + 1T 띠 10폭", "재단+리벳",
    note=f"외곽 {TRAY_X}×{TRAY_Y:.0f}. 앵글: 긴 변 {TRAY_X} ×2, 짧은 변 {TRAY_Y - 20:.0f} ×2 (긴 변 사이 맞대기, 45° 맞춤 아님) + 모서리 판 1T 20×20 ×4 리벳. "
         f"십자 띠(1T 10폭, 업체 절단): {TRAY_X - 2} ×1, {TRAY_Y - 2:.0f} ×1 — 세운 다리 사이, 바닥 다리 위에 리벳. 교차점은 한 띠가 위로")
cp = box(CH_CX - 55, CH_CY - 25, tz + 1, CH_CX + 55, CH_CY + 25, tz + 2)
for x in PIN_X:
    cp = cp.cut(cyl("z", (x, CH_CY), 2.8, tz, tz + 3))
add("T04_tray_center_plate_Al1T_110x50", cp, C_AL, "알루미늄 1T", "재단", note="십자 평철 위에 리벳, 받침판 핀 구멍 Ø5.6")
add("T02_tray_mesh_SS", box(tx0 + 1, ty0 + 1, tz + 10, tx0 + TRAY_X - 1, ty0 + TRAY_Y - 1, tz + 10.6),
    (0.8, 0.8, 0.82, 0.5), "스테인리스 메시", "재단", note="식품용 SUS304, 프레임 윗면에 리벳 Ø3.2 + 와셔, 약 50mm 간격 (위치는 조립 때 겹쳐 뚫기)")

# 트레이 옆 틈막이 (좌우 12mm 틈 → 2mm)
for side in ("L", "R"):
    if side == "L":
        xa = IN0 + T05
        st_ = box(xa, ty0 + 5, STRIP_Z - 10, xa + 1, DUCT_W0 - 12, STRIP_Z) \
            .union(box(xa, ty0 + 5, STRIP_Z - 1, tx0 - 2, DUCT_W0 - 12, STRIP_Z))
    else:
        xa = IN1 - T05
        st_ = box(xa - 1, ty0 + 5, STRIP_Z - 10, xa, DUCT_W0 - 12, STRIP_Z) \
            .union(box(tx0 + TRAY_X + 2, ty0 + 5, STRIP_Z - 1, xa, DUCT_W0 - 12, STRIP_Z))
    for y in STRIP_BOLTS_Y:
        st_ = st_.cut(cyl("x", (y, STRIP_Z - 5), 1.7, xa - 2, xa + 2))
    add(f"A14_tray_gap_strip_{side}", st_, C_AL, "알루미늄 앵글 10×10×1", "재단",
        note="트레이 옆 틈막이. 트레이에 닿지 않게(2mm)")
    for j, y in enumerate(STRIP_BOLTS_Y):
        if side == "L":
            bolt(f"A14_bolt_L_{j}", "x", (y, STRIP_Z - 5), 0, +1, 20)
            nut(f"A14_nut_L_{j}", "x", (y, STRIP_Z - 5), xa + 1, +1)
        else:
            bolt(f"A14_bolt_R_{j}", "x", (y, STRIP_Z - 5), OUT, -1, 20)
            nut(f"A14_nut_R_{j}", "x", (y, STRIP_Z - 5), xa - 1, -1)

# ============================================================
# 7. 천장: 배기 플랩 (v3.1: TCS34725·LED·센서 인서트 삭제)
# ============================================================
flap_frame = box(EXH[0] - 10, EXH[1] - 5, OZ, EXH[2] + 10, EXH[3] + 5, OZ + 3) \
    .cut(box(EXH[0], EXH[1], OZ - 1, EXH[2], EXH[3], OZ + 4))
add("S04_exhaust_flap_frame_PETG", flap_frame, C_PETG, "PETG", "3D프린트", note="천장판에 PVC본드")
add("S05_exhaust_flap_PET0.3", box(EXH[0] - 4, EXH[1] - 2, OZ + 3, EXH[2] + 4, EXH[3] + 2, OZ + 3.3), (0.9, 0.9, 0.6, 0.6),
    "PET 0.3", "재단", note="뒤쪽 변만 테이프 힌지")

# ============================================================
# 8. 챔버 센서 — v3.0: 둘 다 오른벽 (관통 볼트·케이블이 측면 박스로 바로)
# ============================================================
def wall_holder_right(prefix, P, bw, bh, bt, board_name, note_board, screw_holes=None):
    x1 = IN1 - T05
    face = x1 - 6
    h = box(face, P[0] - bw / 2 - 3, P[1] - bh / 2 - 3, x1, P[0] + bw / 2 + 3, P[1] + bh / 2 + 3).cut(cyl("x", P, 1.7, face - 1, x1 + 1))
    h = h.cut(cq.Workplane("YZ").polygon(6, 5.7 / math.cos(math.pi / 6)).extrude(4.1).translate((face - 0.05, P[0], P[1])))   # 너트 포켓
    for p in (screw_holes or []):
        h = h.cut(cyl("x", p, 0.8, face - 1, face + 6))
    b = box(face - bt, P[0] - bw / 2, P[1] - bh / 2, face, P[0] + bw / 2, P[1] + bh / 2)
    for p in (screw_holes or []):
        b = b.cut(cyl("x", p, 1.0, face - bt - 1, face + 1))
    add(f"{prefix}_holder_PETG", h, C_PETG, "PETG", "3D프린트", note="벽 관통 M3×20 1개(측면 박스 쪽 머리, 너트는 포켓)")
    add(board_name, b, C_SENS, kind="buy", note=note_board)
    bolt(f"{prefix}_bolt", "x", P, OUT, -1, 20)
    nut(f"{prefix}_nut", "x", P, OUT - 20 + 2.45, -1)          # 볼트 끝(x=280)까지 2.4 물림
    return face
SHT_HOLES = [(SHT_P[0] + sy * SHT["hole_sp"] / 2, SHT_P[1] + SHT["h"] / 2 - SHT["hole_edge"]) for sy in (-1, 1)]
sh_face = wall_holder_right("C01_SHT31", SHT_P, SHT["w"], SHT["h"], SHT["t"], "C02_SHT31_SEN0331", "오른벽, 트레이 위", SHT_HOLES)
for i, p in enumerate(SHT_HOLES):
    s_ = cyl("x", p, 0.8, sh_face - SHT["t"], sh_face + 4.6).union(cyl("x", p, 1.9, sh_face - SHT["t"] - 1.3, sh_face - SHT["t"]))
    add(f"C_screw_SHT31_{i}", s_, C_BOLT, kind="fastener")
    count("M2×6 셀프태핑 나사 (SHT31)")
wall_holder_right("C03_BME688_1", BME1_P, BME["w"], BME["h"], BME["t"], "C04_BME688_1_SEN0617", "덕트 위 전실(배기 직전), 보드는 VHB")

# ============================================================
# 9. 앞문 — v3.0: 손잡이 턱 삭제 → 문 앞면 손잡이
# ============================================================
door_x0, door_x1 = 2, OUT - 2
door_z0, door_z1 = DOOR_Z0 - 10, DOOR_Z1 + 10
door = box(door_x0, -(WALL + GAP), door_z0, door_x1, -GAP, door_z1)
for mz in MAG_Z:
    door = door.cut(cyl("y", (MAG_X, mz), MAG_D / 2, -GAP - MAG["t"], -GAP + 1))
for z0 in HINGE_Z:
    for p in hinge_hole_pts(z0):
        door = door.cut(cyl("y", p, 1.7, -(WALL + GAP) - 1, -GAP + 1))
HANDLE_X = 268
HANDLE = PARAMS["HANDLE"]
HANDLE_Z = tuple((DOOR_Z0 + DOOR_Z1) / 2 + s * HANDLE["hole_sp"] / 2 for s in (-1, 1))   # 구멍 간격 (params.yaml)
for z in HANDLE_Z:
    door = door.cut(cyl("y", (HANDLE_X, z), HANDLE["hole_d"] / 2, -(WALL + GAP) - 1, -GAP + 1))
add("D01_door_outer_foamex5T", door, C_FOAMEX, "포맥스 5T", "재단", note="296 폭 (v3.0 손잡이 턱 삭제)")
plug = box(DOOR_X0 + 1.5, -GAP, DOOR_Z0 + 1.5, DOOR_X1 - 1.5, IN0 - 2, DOOR_Z1 - 1.5)
for z in HANDLE_Z:
    plug = plug.cut(cyl("y", (HANDLE_X, z), 4.5, -GAP - 1, -GAP + 4))
add("D02_door_plug_foam_257x166", plug, C_FOAM, "폼보드 10T + 포맥스 5T", "재단", note="손잡이 나사 머리 포켓 Ø9 깊이 4")
add("D03_door_plug_liner_Al0.5", box(DOOR_X0 + 1.5, IN0 - 2, DOOR_Z0 + 1.5, DOOR_X1 - 1.5, IN0 - 1.5, DOOR_Z1 - 1.5),
    C_AL + (0.65,), "알루미늄 0.5T", "재단")
gk_in = (DOOR_X0 - 1, DOOR_Z0 - 1, DOOR_X1 + 1, DOOR_Z1 + 1)
gk = box(DOOR_X0 - 6, -GAP, DOOR_Z0 - 6, DOOR_X1 + 6, 0, DOOR_Z1 + 6).cut(box(gk_in[0], -GAP - 1, gk_in[1], gk_in[2], 1, gk_in[3]))
add("D04_door_gasket_5mm", gk, (0.2, 0.2, 0.2, 0.7), "실리콘 폼 테이프", "재단", note="앞판 바깥면에 부착")
for i, mz in enumerate(MAG_Z):
    add(f"D05_magnet_wall_{i+1}_8x3", cyl("y", (MAG_X, mz), 4, 0, 3), C_BLK, kind="buy")
    add(f"D05_magnet_door_{i+1}_8x3", cyl("y", (MAG_X, mz), 4, -GAP - 3, -GAP), C_BLK, kind="buy")
for i, z0 in enumerate(HINGE_Z):
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
hy0 = -(WALL + GAP)
hd = cyl("y", (HANDLE_X, HANDLE_Z[0]), 5, hy0 - 22, hy0).union(cyl("y", (HANDLE_X, HANDLE_Z[1]), 5, hy0 - 22, hy0)) \
    .union(box(HANDLE_X - 5, hy0 - 30, HANDLE_Z[0] - 5, HANDLE_X + 5, hy0 - 22, HANDLE_Z[1] + 5))
for z in HANDLE_Z:
    hd = hd.cut(cyl("y", (HANDLE_X, z), 2.0, hy0 - 10, hy0 + 1))
add("D07_door_pull_handle_96", hd, C_BOLT, kind="buy", note="가구 손잡이 구멍 간격 96, M4")
for j, z in enumerate(HANDLE_Z):
    bolt(f"D_handle_bolt_{j}", "y", (HANDLE_X, z), -GAP, -1, 12, d=4, spec="M4×12 냄비머리 볼트 (문 손잡이)")

# ============================================================
# 10. 흡기 박스 — v3.0: 뒷판 안쪽, 복귀실로 직결
# ============================================================
ix, iz = INTAKE_C
ib_fl = OUT - WALL                       # 뒷판 안쪽 면 295
FL_T = 6                                 # 플랜지 두께 (커버 볼트용 인서트)
ib_end = PART_Y1 + 20                    # 출구: 칸막이에서 20mm (v3.0은 9mm)
fan_y1 = ib_fl - FL_T; fan_y0 = fan_y1 - FAN40["t"]
ibox = box(ix - 28, fan_y1, iz - 28, ix + 28, ib_fl, iz + 28)
ibox = ibox.union(box(ix - 24, ib_end, iz - 24, ix + 24, fan_y1, iz + 24))
ibox = ibox.cut(box(ix - 21.5, ib_end - 1, iz - 21.5, ix + 21.5, fan_y1 + 0.01, iz + 21.5))
ibox = ibox.cut(cyl("y", INTAKE_C, 19, fan_y1 - 1, ib_fl + 1))
for p in INTAKE_HOLES:
    ibox = ibox.cut(cyl("y", p, 1.7, fan_y1 - 1, ib_fl + 1))
for p in COVER_PTS:
    ibox = ibox.cut(cyl("y", p, 2.0, ib_fl - 5, ib_fl + 1))
    count("M3 열압입 인서트 (L4)")
BME_Y0 = ib_end + 0.5                    # BME688 #2: +x 옆벽 홈, 흐름과 나란히 (막지 않음)
ibox = ibox.cut(box(ix + 21.3, ib_end - 1, iz - BME["w"] / 2 - 0.3, ix + 23.2, BME_Y0 + BME["h"] + 0.3, iz + BME["w"] / 2 + 0.3))
add("I01_intake_box_PETG", ibox, C_PETG, "PETG", "3D프린트",
    note="v3.1 뒷판 안쪽. 플랜지 6T(커버용 인서트 2), BME688 #2는 +x 옆벽 홈에 출구 쪽에서 밀어 넣고 실리콘 한 점")
fan40 = box(ix - FAN40["s"] / 2, fan_y0, iz - FAN40["s"] / 2, ix + FAN40["s"] / 2, fan_y1, iz + FAN40["s"] / 2).cut(cyl("y", INTAKE_C, 18.5, fan_y0 - 1, fan_y1 + 1))
for p in INTAKE_HOLES:
    fan40 = fan40.cut(cyl("y", p, FAN40["hd"] / 2, fan_y0 - 1, fan_y1 + 1))
add("I02_fan_40mm_intake_PWM", fan40, C_BLK, kind="buy")
add("I04_BME688_2_SEN0617", box(ix + 21.5, BME_Y0, iz - BME["w"] / 2, ix + 21.5 + BME["t"], BME_Y0 + BME["h"], iz + BME["w"] / 2), C_SENS, kind="buy",
    note="센서 면이 관 안쪽을 봄")
add("I05_intake_flap_PET", box(ix - 23, ib_end - 0.3, iz - 23, ix + 23, ib_end, iz + 23), (0.9, 0.9, 0.6, 0.6), "PET 0.3", "재단",
    note="출구 윗변 테이프 힌지 (역류 방지). 칸막이까지 20mm")
for i, p in enumerate(INTAKE_HOLES):
    bolt(f"I_bolt_{i}", "y", p, OUT, -1, 25, spec="M3×25 냄비머리 볼트 (흡기팬)")
    nut(f"I_nut_{i}", "y", p, fan_y0, -1)
# 뒷판 바깥 활성탄 커버 (차가운 쪽: 데워진 활성탄이 흡착물을 다시 내놓는 것 방지, 바깥에서 교체)
cv0 = OUT
cover = box(ix - 29, cv0, iz - 29, ix + 29, cv0 + 11, iz + 29)
cover = cover.cut(box(ix - 20, cv0 - 1, iz - 20, ix + 20, cv0 + 3, iz + 20))            # 테두리: 팬 볼트 머리 자리
cover = cover.cut(box(ix - 22.2, cv0 + 3, iz - 22.2, ix + 22.2, cv0 + 8, iz + 22.2))     # 활성탄 포켓
for dz in (-16, -8, 0, 8, 16):
    cover = cover.cut(box(ix - 18, cv0 + 7, iz + dz - 2, ix + 18, cv0 + 12, iz + dz + 2))  # 그릴
for p in COVER_PTS:
    cover = cover.cut(cyl("y", p, 1.7, cv0 - 1, cv0 + 12))
add("I06_intake_carbon_cover_PETG", cover, C_PETG, "PETG", "3D프린트", note="뒷판 바깥, M3×20 2개로 흡기 박스 플랜지 인서트에 고정")
add("I03_carbon_pad", box(ix - 21.5, cv0 + 3.5, iz - 21.5, ix + 21.5, cv0 + 7.5, iz + 21.5), (0.1, 0.1, 0.1, 0.8), "활성탄 패드", "재단",
    note="몇 회차마다 교체 (커버 볼트 2개)")
for i, p in enumerate(COVER_PTS):
    bolt(f"I_cover_bolt_{i}", "y", p, cv0 + 11, -1, 20, spec="M3×20 냄비머리 볼트 (활성탄 커버)")

# ============================================================
# 11. 전장부(본체) — 히터·팬·배플·65°C 서모스탯·DS18B20만
# ============================================================
def ksd(name, base, axis_dir, color=(0.85, 0.1, 0.1), note=""):
    bx, by, bz = base
    cap = cyl("x", (by, bz), KSD["cap_d"] / 2, *sorted((bx, bx + axis_dir * KSD["body_h"])))
    x0, x1 = sorted((bx, bx - axis_dir * KSD["br_t"]))
    br = box(x0, by - KSD["br_l"] / 2, bz - 5, x1, by + KSD["br_l"] / 2, bz + 5)
    for sy in (-1, 1):
        br = br.cut(cyl("x", (by + sy * KSD["br_hole_sp"] / 2, bz), 1.7, x0 - 1, x1 + 1))
    tail = KSD["total_h"] - KSD["body_h"] - KSD["br_t"]
    t0, t1 = sorted((bx - axis_dir * KSD["br_t"], bx - axis_dir * (KSD["br_t"] + tail)))
    add(name, cap.union(br).union(box(t0, by - 6, bz - 3, t1, by + 6, bz + 3)), color, kind="buy", note=note)

fx, fz = FAN_C
fan_y1h = PART_Y0
fan_y0h = fan_y1h - FAN60["t"]
fan60 = box(fx - FAN60["s"] / 2, fan_y0h, fz - FAN60["s"] / 2, fx + FAN60["s"] / 2, fan_y1h, fz + FAN60["s"] / 2).cut(cyl("y", FAN_C, 28.5, fan_y0h - 1, fan_y1h + 1))
for p in FAN_HOLES:
    fan60 = fan60.cut(cyl("y", p, FAN60["hd"] / 2, fan_y0h - 1, fan_y1h + 1))
add("H01_fan_60mm_4pin_PWM", fan60, C_BLK, kind="buy", note="Evercool EC6025TH12BP")

# 알루미늄 히터 덕트 (H06): PTC 핀 블록에 1mm 이하로 붙게 접음
GAP_PTC = 1.0
ptc_x0 = 27
PTC_Y0 = 165 - PTC["d"] / 2
PTC_Z0 = FAN_C[1] - PTC["h"] / 2
H_X0, H_X1 = ptc_x0 - GAP_PTC - 0.5, ptc_x0 + PTC["w"] + GAP_PTC + 0.5
H_Z0, H_Z1 = PTC_Z0 - GAP_PTC - 0.5, PTC_Z0 + PTC["h"] + GAP_PTC + 0.5
H_Y0, H_Y1 = 145, 187
fl_y = fan_y0h - 1                              # 팬 앞 플랜지 (알루미늄 1T)
flange = box(fx - 30, fl_y, fz - 30, fx + 30, fan_y0h, fz + 30).cut(cyl("y", FAN_C, 28.5, fl_y - 1, fan_y0h + 1))
for p in FAN_HOLES:
    flange = flange.cut(cyl("y", p, 1.7, fl_y - 1, fan_y0h + 1))
trans = (cq.Workplane("XZ", origin=(0, fl_y, 0)).center(fx, fz).rect(60, 60)
         .workplane(offset=fl_y - H_Y1).center((H_X0 + H_X1) / 2 - fx, (H_Z0 + H_Z1) / 2 - fz).rect(H_X1 - H_X0, H_Z1 - H_Z0).loft())
trans_in = (cq.Workplane("XZ", origin=(0, fl_y + 0.01, 0)).center(fx, fz).rect(59, 59)
            .workplane(offset=fl_y - H_Y1 + 0.02).center((H_X0 + H_X1) / 2 - fx, (H_Z0 + H_Z1) / 2 - fz).rect(H_X1 - H_X0 - 1, H_Z1 - H_Z0 - 1).loft())
hous = box(H_X0, H_Y0, H_Z0, H_X1, H_Y1, H_Z1).cut(box(H_X0 + 0.5, H_Y0 - 1, H_Z0 + 0.5, H_X1 - 0.5, H_Y1 + 1, H_Z1 - 0.5))
EAR_HOLES = [(ptc_x0 + PTC["ear_len"] / 2, 165), (ptc_x0 + PTC["w"] - PTC["ear_len"] / 2, 165)]
for p in EAR_HOLES:
    hous = hous.cut(cyl("z", p, 1.7, H_Z0 - 1, H_Z0 + 1))
TH95_BASE_X = ptc_x0 + PTC["w"] - PTC["ear_len"] + KSD["body_h"] + 0.1
hous = hous.cut(cyl("x", (165, FAN_C[1]), KSD["cap_d"] / 2 + 0.5, H_X1 - 1, H_X1 + 1))
th95_holes = [(165 + sy * KSD["br_hole_sp"] / 2, FAN_C[1]) for sy in (-1, 1)]
for p in th95_holes:
    hous = hous.cut(cyl("x", p, 1.7, H_X1 - 1, H_X1 + 1))
hduct = flange.union(trans.cut(trans_in)).union(hous)
add("H06_heater_duct_Al05", hduct, C_AL, "알루미늄 0.5T + 1T 플랜지", "재단+절곡",
    note="v3.0 PETG 대신. 핀 블록에 1mm 이하, 이음매 알루미늄 테이프. 팬 쪽 플랜지만 1T")
# 귀 자리 막음 (PTC 양끝 귀 위 빈 공간 → 공기 우회 차단), 오른쪽은 서모스탯 캡·너트 자리
fills = [box(H_X0 + 0.5, PTC_Y0, PTC_Z0 + PTC["ear_t"], ptc_x0 + PTC["ear_len"], PTC_Y0 + PTC["d"], H_Z1 - 0.5),
         box(ptc_x0 + PTC["w"] - PTC["ear_len"], PTC_Y0, PTC_Z0 + PTC["ear_t"], H_X1 - 0.5, PTC_Y0 + PTC["d"], H_Z1 - 0.5)]
fills[1] = fills[1].cut(cyl("x", (165, FAN_C[1]), KSD["cap_d"] / 2 + 0.5, ptc_x0 + PTC["w"] - PTC["ear_len"] - 1, H_X1))
for p in th95_holes:
    fills[1] = fills[1].cut(cyl("x", p, 3.4, H_X1 - 9, H_X1))
for p in EAR_HOLES:
    fills = [f_.cut(cyl("z", p, 3.0, PTC_Z0, PTC_Z0 + 4)) for f_ in fills]
add("H07_ear_baffle_L_Al", fills[0], C_AL, "알루미늄 1T 접기", "재단+절곡", note="귀 위 우회 통로 막음")
add("H07_ear_baffle_R_Al", fills[1], C_AL, "알루미늄 1T 접기", "재단+절곡", note="귀 위 우회 통로 막음, 서모스탯 캡 구멍")
fin = box(ptc_x0 + PTC["ear_len"], PTC_Y0, PTC_Z0, ptc_x0 + PTC["w"] - PTC["ear_len"], PTC_Y0 + PTC["d"], PTC_Z0 + PTC["h"])
for ex_, p in zip((ptc_x0, ptc_x0 + PTC["w"] - PTC["ear_len"]), EAR_HOLES):
    fin = fin.union(box(ex_, PTC_Y0, PTC_Z0, ex_ + PTC["ear_len"], PTC_Y0 + PTC["d"], PTC_Z0 + PTC["ear_t"])
                    .cut(cyl("z", p, PTC["ear_hole_d"] / 2, PTC_Z0 - 1, PTC_Z0 + 2)))
add("H03_PTC_fin_12V", fin, C_HOT, kind="buy", note="100W(PWM 80% 제한) 또는 50W, 95×31. 귀·두께 도착 후 실측. 설치 전 밖에서 30분 태움")
for i, p in enumerate(EAR_HOLES):
    bolt(f"H_ptc_bolt_{i}", "z", p, PTC_Z0 + PTC["ear_t"], -1, 6, spec="M3×6 냄비머리 볼트 (PTC 귀)")
    nut(f"H_ptc_nut_{i}", "z", p, H_Z0, -1)
ksd("H05_thermostat_KSD301_95C", (TH95_BASE_X, 165, FAN_C[1]), -1, note="NC 95°C. 캡이 핀 블록 끝면에 닿게, 브래킷과 벽 사이 와셔")
for i, p in enumerate(th95_holes):
    bolt(f"H_th95_bolt_{i}", "x", p, TH95_BASE_X + KSD["br_t"], -1, 8, spec="M3×8 냄비머리 볼트 (서모스탯)")
    nut(f"H_th95_nut_{i}", "x", p, H_X1 - 0.5, -1)
for i, p in enumerate(FAN_HOLES):
    bolt(f"H_fan_bolt_{i}", "y", p, PART_Y1, -1, 30, spec="M3×30 냄비머리 볼트 (칸막이+팬+덕트 플랜지)")
    nut(f"H_fan_nut_{i}", "y", p, fl_y, -1)
# 덕트 받침 (알루미늄 1T L자 접기 2개, 스탠드오프 10)
SAD_X = (45, 105)
for i, x in enumerate(SAD_X):
    sd = box(x - 0.5, 150, IN0 + T05, x + 0.5, 180, H_Z0).union(box(x - 0.5, 150, IN0 + T05, x + 10, 180, IN0 + T05 + 1))
    sd = sd.cut(cyl("z", (x + 5, 165), 1.7, 0, 30))
    add(f"H08_duct_saddle_{i+1}_Al", sd, C_AL, "알루미늄 1T 판 L자 접기", "재단+절곡",
        note=f"세운 다리 {H_Z0 - IN0 - T05:.1f} × 바닥 다리 10.5 (바깥 치수), 길이 30. 10×10 앵글로는 안 됨. 덕트 바닥에 리벳")
    so(f"H08_so_{i}", x + 5, 165, 10)
    bolt(f"H08_bolt_{i}", "z", (x + 5, 165), IN0 + T05 + 1, -1, 6, spec="M3×6 냄비머리 볼트 (덕트 받침)")

ob = box(fx - 32, 124, BAY_Z0 + T05, fx + 32, 125, FLOOR_Z - 12).union(box(fx - 32, 125, BAY_Z0 + T05, fx + 32, 137, BAY_Z0 + T05 + 1))
OB_HOLES = [(fx - 20, 131), (fx + 20, 131)]
for p in OB_HOLES:
    ob = ob.cut(cyl("z", p, 1.7, 0, 30))
add("A12_outlet_baffle_Al1T_64x56", ob, C_AL, "알루미늄 1T", "재단+절곡", note="플랜지 12 접기")
for i, (x, y_) in enumerate(OB_HOLES):
    so(f"OB_so_{i}", x, y_, 10)
    bolt(f"OB_bolt_{i}", "z", (x, y_), BAY_Z0 + T05 + 1, -1, 6, spec="M3×6 냄비머리 볼트 (배플)")

add("E06_DS18B20_probe", cyl("z", (165, 195), 3, 35, 65), (0.6, 0.6, 0.6), kind="buy", note="플레넘 공기, 실리콘 케이블을 칸막이 앵글에 케이블타이")
# 65°C 서모스탯 (알루미늄 받침으로 변경: 공기 경로에 PETG 줄이기)
TH65_C = (222, 47)
th65_bx = IN1 - T05 - 4 - KSD["body_h"]
st_x1 = th65_bx - KSD["br_t"] - 0.05
st = box(st_x1 - 1, TH65_C[0] - 15, IN0 + T05 + 1, st_x1, TH65_C[0] + 15, TH65_C[1] + 8) \
    .cut(box(st_x1 - 2, TH65_C[0] - 8, TH65_C[1] - 6, st_x1 + 1, TH65_C[0] + 8, TH65_C[1] + 6))
st = st.union(box(st_x1 - 12, TH65_C[0] - 15, IN0 + T05, st_x1, TH65_C[0] + 15, IN0 + T05 + 1))
st_hole = (st_x1 - 7, TH65_C[0])
st = st.cut(cyl("z", st_hole, 1.7, 0, 30))
th65_holes = [(TH65_C[0] + sy * KSD["br_hole_sp"] / 2, TH65_C[1]) for sy in (-1, 1)]
for p in th65_holes:
    st = st.cut(cyl("x", p, 1.7, st_x1 - 2, st_x1 + 1))
add("E07_thermostat65_bracket_Al", st, C_AL, "알루미늄 앵글 30 폭", "재단+절곡", note="v3.0 PETG 받침 → 알루미늄 앵글")
ksd("E07_thermostat_KSD301_65C", (th65_bx, TH65_C[0], TH65_C[1]), +1, note="NC 65°C, 플레넘 공기")
for i, p in enumerate(th65_holes):
    bolt(f"E07_th_bolt_{i}", "x", p, th65_bx, -1, 8, spec="M3×8 냄비머리 볼트 (서모스탯)")
    nut(f"E07_th_nut_{i}", "x", p, st_x1 - 1, -1)
so("E07_so", st_hole[0], st_hole[1], 10)
bolt("E07_bolt", "z", st_hole, IN0 + T05 + 1, -1, 6, spec="M3×6 냄비머리 볼트 (서모스탯 받침)")

# 관통 글랜드 (본체 오른쪽 옆판, 돔은 측면 박스 쪽)
def gland_x(name, P, note):
    big = P in (PT1P, PT1S)
    rb, af, rd, ri = (7.5, 22, 9.5, 4.0) if big else (6.0, 19, 7.5, 2.6)
    g = cyl("x", P, rb, OUT - WALL - 6, OUT + 3)
    g = g.union(cq.Workplane("YZ").polygon(6, af / math.cos(math.pi / 6)).extrude(3).translate((OUT, P[0], P[1])))
    g = g.union(cyl("x", P, rd, OUT + 3, OUT + 15))
    g = g.union(cyl("x", P, gl_nut(P) / 2, OUT - WALL - 5, OUT - WALL))
    g = g.cut(cyl("x", P, ri, OUT - WALL - 7, OUT + 16))
    add(name, g, C_BLK, kind="buy", note=note)
gland_x("K20_gland_PG9_bay_power", PT1P, "전장부 전력: PTC 2, 순환·흡기팬 전원 4 (케이블 4~8)")
gland_x("K20_gland_PG9_bay_signal", PT1S, "전장부 신호: 팬 PWM·타코, DS18B20, 로드셀, BME688 #2 (다공 실 또는 실리콘 충전)")
gland_x("K20_gland_PG7_duct", PT3, "BME688 #1")
gland_x("K20_gland_PG7_chamber", PT4, "SHT31")

# ============================================================
# 12. 측면 박스 (K) — 전자레인지 조작부처럼 본체 오른쪽
# ============================================================
SBI_X0, SBI_X1 = BP_X1, SB_X1 - WALL           # 안쪽 x 305..390
K_LCD_C = (SB_X0 + (SB_X1 - WALL - SB_X0) / 2, 225)      # 앞면 LCD 중심 (x, z)
K_BTN_Z = (180, 155, 130)
K_GLAND = (325, 40)                             # 뒷면 전원 글랜드 (x, z)
K_SW = (362, 40)                                # 뒷면 로커
K_USB = (345, 120)                              # 뒷면 USB

kf = box(SB_X0, 0, WALL, SB_X1 - WALL, WALL, WALL_H)
kf = kf.cut(box(K_LCD_C[0] - 36, -1, K_LCD_C[1] - 12.5, K_LCD_C[0] + 36, WALL + 1, K_LCD_C[1] + 12.5))
K_LCD_HOLES = [(K_LCD_C[0] + sx * LCD["hx"] / 2, K_LCD_C[1] + sz * LCD["hz"] / 2) for sx in (-1, 1) for sz in (-1, 1)]
for p in K_LCD_HOLES:
    kf = kf.cut(cyl("y", p, 1.7, -1, WALL + 1))
for bz in K_BTN_Z:
    kf = kf.cut(cyl("y", (K_LCD_C[0], bz), 6.1, -1, WALL + 1))
add("K01_sidebox_front_foamex5T", kf, C_FOAMEX, "포맥스 5T", "재단", note="LCD 창 72×25, 버튼 Ø12.2 ×3")

kb = box(SB_X0, OUT - WALL, WALL, SB_X1 - WALL, OUT, WALL_H)
kb = kb.cut(cyl("y", K_GLAND, PWR["gland_d"] / 2, OUT - WALL - 1, OUT + 1))
kb = kb.cut(box(K_USB[0] - USBP["cut_w"] / 2, OUT - WALL - 1, K_USB[1] - USBP["cut_h"] / 2, K_USB[0] + USBP["cut_w"] / 2, OUT + 1, K_USB[1] + USBP["cut_h"] / 2))
kb = kb.cut(box(K_USB[0] - USBP["plug_w"] / 2, OUT - WALL + 1, K_USB[1] - USBP["plug_h"] / 2, K_USB[0] + USBP["plug_w"] / 2, OUT + 1, K_USB[1] + USBP["plug_h"] / 2))
K_USB_HOLES = [(K_USB[0] - USB_HOLE_SP / 2, K_USB[1]), (K_USB[0] + USB_HOLE_SP / 2, K_USB[1])]
for p in K_USB_HOLES:
    kb = kb.cut(cyl("y", p, 1.6, OUT - WALL - 1, OUT + 1))
RK = PARAMS["ROCKER"]
kb = kb.cut(box(K_SW[0] - RK["cut_w"] / 2, OUT - WALL - 1, K_SW[1] - RK["cut_h"] / 2, K_SW[0] + RK["cut_w"] / 2, OUT + 1, K_SW[1] + RK["cut_h"] / 2))
kb = kb.cut(box(K_SW[0] - RK["bezel_w"] / 2, OUT - WALL - 1, K_SW[1] - RK["bezel_h"] / 2, K_SW[0] + RK["bezel_w"] / 2, OUT - 1, K_SW[1] + RK["bezel_h"] / 2))
add("K02_sidebox_back_foamex5T", kb, C_FOAMEX, "포맥스 5T", "재단", note="전원 PG7, 로커(안쪽 카운터보어), USB")

def vents(p_, z0, z1):
    for y in (60, 120, 180, 240):
        for dy in (-12, 0, 12):
            p_ = p_.cut(box(SB_X0 + 25, y + dy - 3, z0 - 1, SB_X1 - 25, y + dy + 3, z1 + 1))
    return p_
kbot = vents(box(SB_X0, 0, 0, SB_X1, OUT, WALL), 0, WALL)
ktop = vents(box(SB_X0, 0, WALL_H, SB_X1, OUT, OZ), WALL_H, OZ)
K_LID_PTS = [(y, z) for y in (10, OUT - 10) for z in (10, (WALL_H) / 2, WALL_H - 10)]
klid = box(SB_X1 - WALL, 0, WALL, SB_X1, OUT, WALL_H)
for p in K_LID_PTS:
    klid = klid.cut(cyl("x", p, 1.7, SB_X1 - WALL - 1, SB_X1 + 1))
add("K03_sidebox_bottom_foamex5T", kbot, C_FOAMEX, "포맥스 5T", "재단", note="통풍 슬롯 45×6 ×12")
add("K04_sidebox_top_foamex5T", ktop, C_FOAMEX, "포맥스 5T", "재단", note="통풍 슬롯 45×6 ×12")
add("K05_sidebox_lid_foamex5T", klid, C_FOAMEX, "포맥스 5T", "재단", note="정비 뚜껑, M3×10 6개")
for i, (y, z) in enumerate(K_LID_PTS):
    y0 = WALL if y < 150 else OUT - WALL - 10
    z0 = max(WALL, min(WALL_H - 10, z - 5))
    blk = box(SB_X1 - WALL - 10, y0, z0, SB_X1 - WALL, y0 + 10, z0 + 10).cut(cyl("x", (y, z), 2.0, SB_X1 - WALL - 8, SB_X1))
    add(f"K07_corner_block_{i+1}", blk, C_PETG, "PETG", "3D프린트", note="M3 인서트, 앞·뒤판에 PVC본드")
    count("M3 열압입 인서트 (L4)")
    bolt(f"K_lid_bolt_{i}", "x", (y, z), SB_X1, -1, 10)

# 세로 장착판 (본체 옆판 바깥면에 접착) — 구멍: 관통구·볼트 머리
BP_Y0, BP_Y1, BP_Z0, BP_Z1 = 13, OUT - 6, 20, WALL_H - 1
bp = box(BP_X0, BP_Y0, BP_Z0, BP_X1, BP_Y1, BP_Z1)
for p in PTS:
    bp = bp.cut(cyl("x", p, gl_nut(p) / 2 + 1, BP_X0 - 1, BP_X1 + 1))
for p in [SHT_P, BME1_P] + [(y, STRIP_Z - 5) for y in STRIP_BOLTS_Y] + [(DUCTANG_Y, z) for z in DUCTANG_Z]:
    bp = bp.cut(cyl("x", p, 4, BP_X0 - 1, BP_X1 + 1))

def so_x(name, y, z, L):
    s_ = cq.Workplane("YZ").polygon(6, 5.5 / math.cos(math.pi / 6)).extrude(L).translate((BP_X1, y, z)).cut(cyl("x", (y, z), 1.5, BP_X1 - 1, BP_X1 + L + 1))
    add(name, s_, C_BRASS, kind="fastener")
    count(f"M3×{L} 암-암 황동 스탠드오프")
    bolt(name + "_screw", "x", (y, z), BP_X0, +1, 8, head="flat", spec="M3×8 접시머리 볼트 (장착판→스탠드오프)")
    return (y, z)
BP_HOLES = []
def so_bp(name, y, z, L):
    BP_HOLES.append((y, z))
    so_x(name, y, z, L)

def board_x(name, y0, z0, w, d, x0, t=1.6, holes=(), color=C_PCB, note="", kind="buy", parts=()):
    b = box(x0, y0, z0, x0 + t, y0 + w, z0 + d)
    for p in holes:
        b = b.cut(cyl("x", p, 1.6, x0 - 1, x0 + t + 1))
    for (py0, pz0, pw, pd, ph) in parts:
        b = b.union(box(x0 + t, py0, pz0, x0 + t + ph, py0 + pw, pz0 + pd))
    add(name, b, color, kind=kind, note=note)

# 아래: DFR0457 ×2 (#1 히터 / #3 흡기팬 전원 차단). v3.1: #2(LED) 삭제, 번호는 그대로
MOS_Z0 = 24
for i, y0 in ((0, 50), (2, 150)):
    w, d, h = MOD["MOS_1"]
    hy1 = y0 + w - MOS["hole_edge"]
    hs = [(hy1 - sy * MOS["hole_sp_x"], MOS_Z0 + MOS["hole_edge"] + sz * MOS["hole_sp_y"]) for sy in (0, 1) for sz in (0, 1)]
    for j, p in enumerate(hs):
        so_bp(f"E04_MOS_{i+1}_so_{j}", p[0], p[1], 10)
        bolt(f"E04_MOS_{i+1}_bolt_{j}", "x", p, BP_X1 + 10 + 1.6, -1, 6, spec="M3×6 냄비머리 볼트 (보드→스탠드오프)")
    board_x(f"E04_MOS_{i+1}_DFR0457", y0, MOS_Z0, w, d, BP_X1 + 10, holes=hs, parts=[(y0 + 2, MOS_Z0 + 2, 12, d - 4, h - 1.6)],
            note=["#1 히터 PTC", "#2 LED 스트립", "#3 흡기팬 전원 차단 (GPIO2)"][i])

# 아래: 12V/GND 분배 WAGO ×4 홀더
def wago_holder(name, y0, z0, n, so_L):
    pitch = WAGO["w"] + 2.2
    wdt = 2 * 8 + n * pitch
    dpt = WAGO["d"] + 4
    x0 = BP_X1 + so_L
    h = box(x0, y0, z0, x0 + 3, y0 + wdt, z0 + dpt)
    for k in range(int(n) + 1):
        yw = y0 + 8 + k * pitch - 1.1
        h = h.union(box(x0 + 3, yw, z0 + 2, x0 + 12, yw + 1.1, z0 + dpt - 2))
    hs = [(y0 + 4, z0 + dpt / 2), (y0 + wdt - 4, z0 + dpt / 2)]
    for p in hs:
        h = h.cut(cyl("x", p, 1.7, x0 - 1, x0 + 4))
    add(f"{name}_holder_PETG", h, C_PETG, "PETG", "3D프린트", note=f"WAGO 221-415 {int(n)}칸")
    for k in range(int(n)):
        yw = y0 + 8 + k * pitch + 0.05
        add(f"{name}_WAGO_{k+1}", box(x0 + 3, yw, z0 + 2, x0 + 3 + WAGO["h"], yw + WAGO["w"] - 0.1, z0 + 2 + WAGO["d"]), (0.85, 0.85, 0.85), kind="buy")
    for j, p in enumerate(hs):
        so_bp(f"{name}_so_{j}", p[0], p[1], so_L)
        bolt(f"{name}_bolt_{j}", "x", p, x0 + 3, -1, 8, spec="M3×8 냄비머리 볼트 (WAGO 홀더)")
wago_holder("E05_power", 200, 22, 4, 10)
wago_holder("E05_i2c", 30, 178, 4, 10)

# 가운데: ESP32 확장보드 + DevKitC
EXP_Y0, EXP_Z0 = 30, 66
exp_holes = [(EXP_Y0 + EXP["inset"], EXP_Z0 + EXP["inset"]), (EXP_Y0 + EXP["w"] - EXP["inset"], EXP_Z0 + EXP["inset"]),
             (EXP_Y0 + EXP["inset"], EXP_Z0 + EXP["d"] - EXP["inset"]), (EXP_Y0 + EXP["w"] - EXP["inset"], EXP_Z0 + EXP["d"] - EXP["inset"])]
ex_x0 = BP_X1 + 20
board_x("E01_ESP32_38pin_expansion_board", EXP_Y0, EXP_Z0, EXP["w"], EXP["d"], ex_x0, holes=exp_holes,
        parts=[(EXP_Y0 + 9, EXP_Z0 + 2, EXP["w"] - 18, 7, 10), (EXP_Y0 + 9, EXP_Z0 + EXP["d"] - 9, EXP["w"] - 18, 7, 10)],
        note="CMODULE-47 78×52.5. 구멍 위치는 도착 후 실측")
dk_z0 = EXP_Z0 + EXP["d"] / 2 - DEVKIT["w"] / 2
dk_x0 = ex_x0 + EXP["t"] + 8.5
board_x("E02_ESP32_DevKitC_V4_WROOM32D", EXP_Y0 + 12, dk_z0, DEVKIT["d"], DEVKIT["w"], dk_x0, color=(0.15, 0.15, 0.3),
        parts=[(EXP_Y0 + 12, dk_z0 + 4, 25.5, DEVKIT["w"] - 8, 3.2)], note="USB는 뒤쪽(+y)")
for i, p in enumerate(exp_holes):
    so_bp(f"E01_so_{i}", p[0], p[1], 20)
    bolt(f"E01_bolt_{i}", "x", p, ex_x0 + EXP["t"], -1, 6, spec="M3×6 냄비머리 볼트 (보드→스탠드오프)")

# 가운데: 소형 모듈 캐리어 (SD·HX711·MP1584·부저), 모듈은 y 방향으로 나란히
CR_Y0, CR_Y1, CR_Z0, CR_Z1 = 116, 246, 68, 112   # v3.1 부저 삭제로 짧아짐
cr_x0 = BP_X1 + 20
carrier = box(cr_x0, CR_Y0, CR_Z0, cr_x0 + 3, CR_Y1, CR_Z1)
cr_holes = [(CR_Y0 + 4, CR_Z0 + 4), (CR_Y1 - 4, CR_Z0 + 4), (CR_Y0 + 4, CR_Z1 - 4), (CR_Y1 - 4, CR_Z1 - 4)]
for p in cr_holes:
    carrier = carrier.cut(cyl("x", p, 1.7, cr_x0 - 1, cr_x0 + 4))
yy = CR_Y0 + 8
for k in ("SD", "HX711", "MP1584"):
    w, d, h = MOD[k]
    mz0 = (CR_Z0 + CR_Z1) / 2 - d / 2
    rim = box(cr_x0 + 3, yy - 2, mz0 - 2, cr_x0 + 5, yy + w + 2, mz0 + d + 2).cut(box(cr_x0 + 2, yy - 0.3, mz0 - 0.3, cr_x0 + 6, yy + w + 0.3, mz0 + d + 0.3))
    carrier = carrier.union(rim)
    for sz in (mz0 - 5.5, mz0 + d + 2.5):
        carrier = carrier.cut(box(cr_x0 - 1, yy + w / 2 - 2, sz, cr_x0 + 4, yy + w / 2 + 2, sz + 3))
    add(f"E04_{k}", box(cr_x0 + 3, yy, mz0, cr_x0 + 3 + h, yy + w, mz0 + d), C_PCB if k != "BUZZER" else C_BLK, kind="buy")
    yy += w + 6
assert yy - 6 <= CR_Y1 - 4, yy
add("E03_module_carrier_PETG", carrier, C_PETG, "PETG", "3D프린트", note="측면 박스 안, SD·HX711·MP1584 포켓 + 케이블타이")
for i, p in enumerate(cr_holes):
    so_bp(f"E03_so_{i}", p[0], p[1], 20)
    bolt(f"E03_bolt_{i}", "x", p, cr_x0 + 3, -1, 8, spec="M3×8 냄비머리 볼트 (캐리어)")

for (y, z) in BP_HOLES:
    bp = bp.cut(cyl("x", (y, z), 1.7, BP_X0 - 1, BP_X1 + 1))
    bp = bp.cut(cq.Workplane("YZ").circle(3.0).workplane(offset=1.7).circle(1.7).loft().translate((BP_X0 - 0.01, y, z)))   # 접시 자리(뒷면)
add("K06_sidebox_mount_plate_foamex5T", bp, C_FOAMEX, "포맥스 5T", "재단",
    note="본체 오른쪽 옆판 바깥면에 PVC본드. 스탠드오프는 접착 전에 뒤에서 접시머리로 고정")

# 앞면: LCD + 버튼
lcd_y0 = WALL + 3
lcd = box(K_LCD_C[0] - LCD["w"] / 2, lcd_y0, K_LCD_C[1] - LCD["h"] / 2, K_LCD_C[0] + LCD["w"] / 2, lcd_y0 + 1.6, K_LCD_C[1] + LCD["h"] / 2)
for p in K_LCD_HOLES:
    lcd = lcd.cut(cyl("y", p, 1.6, lcd_y0 - 1, lcd_y0 + 3))
lcd = lcd.union(box(K_LCD_C[0] - LCD["bez_w"] / 2, lcd_y0 - LCD["bez_t"] + 0.6, K_LCD_C[1] - LCD["bez_h"] / 2,
                    K_LCD_C[0] + LCD["bez_w"] / 2, lcd_y0, K_LCD_C[1] + LCD["bez_h"] / 2))
lcd = lcd.union(box(K_LCD_C[0] - 21, lcd_y0 + 1.6, K_LCD_C[1] - 10, K_LCD_C[0] + 21, lcd_y0 + 13, K_LCD_C[1] + 10))
add("E10_LCD1602_I2C", lcd, (0.1, 0.4, 0.2), kind="buy", note="측면 박스 앞면. 백팩 5V 풀업 확인 (S2)")
for i, p in enumerate(K_LCD_HOLES):
    add(f"E10_spacer_{i}", cyl("y", p, 3, WALL, lcd_y0).cut(cyl("y", p, 1.6, WALL - 1, lcd_y0 + 1)), (0.9, 0.9, 0.9), kind="fastener")
    count("M3 나일론 스페이서 3mm")
    bolt(f"E10_bolt_{i}", "y", p, 0, +1, 12, spec="M3×12 냄비머리 볼트 (LCD)")
    nut(f"E10_nut_{i}", "y", p, lcd_y0 + 1.6, +1)
for i, bz in enumerate(K_BTN_Z):
    b = cyl("y", (K_LCD_C[0], bz), 7.5, -2, 0).union(cyl("y", (K_LCD_C[0], bz), 6, 0, 28))
    add(f"E11_pushbutton_12mm_{i+1}", b, C_BOLT, kind="buy", note=["▲", "▼", "선택"][i])
    add(f"E11_pushbutton_nut_{i+1}", cyl("y", (K_LCD_C[0], bz), 8, WALL, WALL + 2).cut(cyl("y", (K_LCD_C[0], bz), 6.1, WALL - 1, WALL + 3)), C_BOLT, kind="fastener")

# 뒷면: 전원 글랜드, USB, 로커, 퓨즈
gl = cyl("y", K_GLAND, 6.0, OUT - WALL - 6, OUT + 3)
gl = gl.union(hexprism((0, 0), 19, 0, 3).rotate((0, 0, 0), (1, 0, 0), -90).translate((K_GLAND[0], OUT, K_GLAND[1])))
gl = gl.union(cyl("y", K_GLAND, 7.5, OUT + 3, OUT + 15))
gl = gl.union(cyl("y", K_GLAND, PWR["nut_od"] / 2, OUT - WALL - 5, OUT - WALL))
gl = gl.cut(cyl("y", K_GLAND, 2.6, OUT - WALL - 7, OUT + 16))
add("E09_cable_gland_PG7", gl, C_BLK, kind="buy", note="어댑터 플러그를 잘라 케이블만 통과 → 퓨즈 → WAGO")
add("E09_adapter_cable", cyl("y", K_GLAND, 2.5, OUT - WALL - 25, OUT + 40), (0.1, 0.1, 0.1), kind="buy")
add("E12_inline_fuse_holder", box(K_GLAND[0] - 6, 250, 128, K_GLAND[0] + 6, 280, 140), (0.9, 0.2, 0.2), kind="buy", note="10A(100W) 블레이드, 케이블타이")
usb = box(K_USB[0] - 12.85, OUT - WALL - 2, K_USB[1] - 4.9, K_USB[0] + 12.85, OUT - WALL, K_USB[1] + 4.9)
for p in K_USB_HOLES:
    usb = usb.cut(cyl("y", p, 1.5, OUT - WALL - 3, OUT))
usb = usb.union(box(K_USB[0] - 5, OUT - WALL - 29.8, K_USB[1] - 4, K_USB[0] + 5, OUT - WALL - 2, K_USB[1] + 4))
usb = usb.union(box(K_USB[0] - 4.5, OUT - WALL, K_USB[1] - 2.3, K_USB[0] + 4.5, OUT - WALL + 1.0, K_USB[1] + 2.3))
add("E09_microUSB_panel_mount_ada3258", usb, C_BLK, kind="buy", note="측면 박스 뒷면")
for i, p in enumerate(K_USB_HOLES):
    bolt(f"E09_usb_bolt_{i}", "y", p, OUT, -1, 12, spec="M3×12 냄비머리 볼트 (USB)")
    nut(f"E09_usb_nut_{i}", "y", p, OUT - WALL - 2, -1)
add("E09_rocker_switch_KCD1", box(K_SW[0] - 9.5, OUT - 22, K_SW[1] - 6.4, K_SW[0] + 9.5, OUT - 1, K_SW[1] + 6.4)
    .union(box(K_SW[0] - 10.5, OUT, K_SW[1] - 7.5, K_SW[0] + 10.5, OUT + 2, K_SW[1] + 7.5)), C_BLK, kind="buy",
    note="측면 박스 뒷면, 안쪽 카운터보어로 판 1mm")

# 바닥판·바닥폼·라이너에 스탠드오프 구멍
for (x, y_, L) in SO_HOLES:
    bottom = bottom.cut(cyl("z", (x, y_), 1.7, -1, WALL + 1))
    bottom = bottom.cut(cq.Workplane("XY").circle(3.0).workplane(offset=1.7).circle(1.7).loft().translate((x, y_, -0.01)))
add("P06_bottom_plate_foamex5T", bottom, C_FOAMEX, "포맥스 5T", "재단")
def recut(name, tool):
    for p in PARTS:
        if p["name"] == name:
            p["shape"] = p["shape"].cut(tool)
for (x, y_, L) in SO_HOLES:
    recut("F01_foam_bottom_270x270", cyl("z", (x, y_), 4, 0, 20))
    recut("A01_liner_bay_bottom_270x270", cyl("z", (x, y_), 3.5 if L > 11 else 1.7, 0, 20))
add("P07_top_plate_foamex5T", top_saved, C_FOAMEX, "포맥스 5T", "재단")
SO_TOP = SO_Z + 20

# ============================================================
# 13. 저장
# ============================================================
# Fusion 브라우저에서 폴더(하위 컴포넌트)로 보이도록 STEP을 2단 어셈블리로 저장한다.
# 그룹 이름은 STEP 호환을 위해 영문 + 번호(정렬용). 한글 설명은 docs/naming.md.
GROUPS = [   # (그룹, 이 접두어로 시작하는 부품) — 위에서부터 먼저 맞는 것
    ("01_shell_foamex",        ("P01", "P02", "P03", "P06", "P07", "B0")),
    ("02_insulation_foam",     ("F0",)),
    ("03_liner_Al",            ("A01", "A02", "A03", "A04", "A06", "A07")),
    ("04_partition_floor",     ("A10", "A12", "A14", "A15", "A16", "A17", "A18", "A19", "A20")),
    ("05_door",                ("D0",)),
    ("06_heater",              ("H0",)),
    ("07_intake",              ("I0",)),
    ("08_electronics",         ("E",)),
    ("09_loadcell_tray",       ("L0", "A11", "T0")),
    ("10_exhaust_ceiling",     ("S0",)),
    ("11_sensors_chamber",     ("C0",)),
    ("12_side_box",            ("K",)),
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
