"""외주 발주 패키지: 포맥스 외관판(CNC 라우터) + 알루미늄 1차(레이저·절곡)

python cad/tools/vendor_pack.py <cad.py> [출력폴더]

묶음: foamex/ (포맥스), aluminum/ (알루미늄 1차), aluminum2/ (알루미늄 2차 = 히터 덕트, 1차와 같이 발주 가능)

결과 (출력폴더/foamex/, 출력폴더/aluminum/ 같은 형식):
  dxf/<판>.dxf       판마다 1개, 단위 mm, 1:1, AutoCAD 2000(R2000) 형식
  dxf_R12/           같은 내용, AutoCAD R12 형식 (구버전 CAM용)
  */all_panels.dxf   모든 판을 한 장에 늘어놓은 것 (견적용, 배치는 업체가)
  발주표.xlsx        판·재료·크기·수량·가공·구멍 수, 업체 전달 사항
  확인도면.pdf       판마다 1쪽 (외곽 치수, 구멍 ID·좌표표). 절곡 부품은 펼친 그림 + 접은 뒤 치수
  step/              (알루미늄만) 절곡 부품 3D (1차: A12 + 앵글 대용 L자 9종, 2차: 히터 덕트 4종)
  dxf_laser/         (알루미늄만) 레이저 업체 색 규칙판, 평판만 (v3.2.1)
                     외곽 OUTER_CUT ACI 5 파랑, 구멍·개구 INNER_CUT ACI 2 노랑, 소재크기 MATERIAL ACI 6 자홍
                     글자·접는 선 없음, 빨강(ACI 1 = 업체 규칙상 각인) 안 씀. 절곡 부품은 step/ 만 올린다

레이어 (dxf/, dxf_R12/ — 사람이 보는 용도)
  CUT_OUTER   외곽 절단
  CUT_INNER   안쪽 개구부 절단 (사각 구멍, Ø8 넘는 원)
  DRILL       드릴 구멍 (Ø8 이하 원)
  BEND        접는 선 (알루미늄 절곡 부품)
  NOTE        글자 — 자르지 않음

포켓·접시머리 자리는 넣지 않음 (직접 가공).
면적 1cm² 미만의 외곽 조각(구멍이 판 모서리를 깎고 남은 부스러기)은 뺀다.
"""
import os, re, sys, json, shutil, importlib.util
from collections import Counter
import ezdxf, logging
logging.getLogger("ezdxf").setLevel(logging.ERROR)   # R12 단위 경고 숨김
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("herb_drawings_vp", os.path.join(HERE, "drawings.py"))
DR = importlib.util.module_from_spec(spec); spec.loader.exec_module(DR)

DRILL_MAX_D = 8.0
MIN_OUTER_AREA = 100.0                      # mm², 이보다 작은 외곽은 부스러기
DXF_VERSIONS = (("R2000", "dxf"), ("R12", "dxf_R12"))
FACE_EN = {"바깥(왼쪽)에서 본 면": "OUTSIDE (left side)", "바깥(오른쪽)에서 본 면": "OUTSIDE (right side)",
           "앞에서 본 면": "FRONT (outside)", "뒤(바깥)에서 본 면": "BACK (outside)",
           "위에서 본 면 (아래쪽=앞)": "TOP VIEW (bottom edge = front)", "어느 면이든": "ANY",
           "펼친 그림": "FLAT PATTERN (nominal)"}

# ---------------------------------------------------------------- 포맥스
FOAMEX = dict(
    key="foamex", title="외관 포맥스",
    material="포맥스(발포 PVC) 5T 회색",
    groups=[  # (접두어들, 가공 방식, 묶음 이름)
        (("P01", "P03", "P06", "P07", "K03", "K04", "K05"), "all", "A"),
        (("P02", "D01", "K01", "K02", "K06"), "outer", "B"),
    ],
    spare={"K01": 1, "K02": 1, "D01": 1},
    extra=[dict(name="D02_door_plug_foamex5T_257x166", title="문 플러그 포맥스 조각", W=257.0, H=166.0, qty=1,
                group="B", note="문 플러그용 (앞판 개구부 조각 대신). 외곽만")],
    notes=[
        "재료: 포맥스(발포 PVC) 5T 회색, 모든 판 같은 두께",
        "치수는 완성 치수 (공구 보정은 업체에서). 공차 ±0.5mm, 외곽 직각",
        "DXF: dxf/ = AutoCAD 2000 형식, dxf_R12/ = R12 형식 (같은 내용). 단위 mm, 1:1",
        "CUT_OUTER = 외곽 절단, CUT_INNER = 안쪽 개구부 절단, DRILL = 구멍 가공 (Ø 그대로), NOTE = 글자 — 자르지 마세요",
        "안쪽 모서리는 공구 반경 R1.5 이하 둥글어도 됩니다",
        "B 묶음은 외곽만 (구멍은 저희가 직접 뚫습니다). 앞판 P02는 문 개구부만 잘라 주세요",
        "DXF는 판마다 정해진 면(확인도면에 표시)에서 본 그림입니다. 그 면이 위로 오게 가공하고, 위 면에 연필로 판 이름을 적어 주세요",
        "보호 필름은 붙은 채로 보내 주세요",
        "레이저 가공 불가 재료(PVC)이므로 CNC 라우터 또는 재단기로 가공",
    ],
    footer="여분: K01·K02·D01은 저희가 손으로 구멍을 뚫는 판이라 1장씩 더 주문 (수량에 포함)",
)

# ---------------------------------------------------------------- 알루미늄 1차
ALUMINUM = dict(
    key="aluminum", title="알루미늄 1차",
    material="알루미늄 판 (업체 기본 재질), 0.5T·1T",
    groups=[
        (("A01", "A02", "A03", "A04", "A06", "A07", "D03"), "all", "0.5T 외곽+구멍"),
        (("A10", "A11", "A15", "A16", "T04"), "all", "1T 외곽+구멍"),
    ],
    spare={"A04_liner_ch_L": 1},
    extra=[],          # run_aluminum 에서 CAD 값으로 채움 (T03 띠, 모서리 판)
    notes=[
        "재료: 알루미늄 판 (재질은 업체 기본), 0.5T와 1T. 0.5T는 손으로 접을 수 있는 무른 판이면 좋겠습니다",
        "치수는 완성 치수. 공차 ±0.3mm, 모서리 버(burr) 제거",
        "업체에 올릴 파일 = 발주표 '올릴 파일' 열: 평판은 dxf_laser/ (외부 커팅 파랑 ACI 5, 내부 커팅 노랑 ACI 2, 소재크기 자홍 ACI 6), "
        "접는 부품은 step/ (DXF는 올리지 않음). 단위 mm, 1:1, AutoCAD 2000",
        "dxf/·dxf_R12/·확인도면.pdf는 확인용 (DRILL=빨강, BEND=파랑이라 업체 색 규칙과 다름 — 그대로 올리지 마세요)",
        "0.5T 라이너도 외곽 + 구멍 (M3 Ø4.0, 케이블 Ø12, A03_back 흡기 개구 50×50). 1T 타공판 A10은 Ø4·Ø5 구멍 전부 (레이저)",
        "절곡 부품 A12: 도면 치수는 접은 뒤 바깥 치수입니다. DXF의 펼친 그림은 바깥 치수 합(공제 전)이라 "
        "전개 치수는 업체 기준으로 계산해 주세요. 90° 한 번 접기. 견적은 STEP으로",
        "앵글 대신 1T L자 절곡 13개('1T 절곡 (앵글 대신)', STEP 9종): 견적 비교용입니다. 비싸면 이 묶음만 빼 주세요 (저희가 앵글을 사서 자름). 12.5·20 짧은 조각은 어려우면 제외",
        "L자 2개씩인 부품(A14·A19)은 좌우 대칭이라 1개는 반대 방향으로 접어 주세요",
        "판마다 연필로 판 이름을 적어 주세요",
    ],
    footer="여분: A04_L 라이너 1장. (v3.3.0: 덕트 받침 H08 삭제). T03 띠·모서리 판은 트레이 조립용 (리벳 구멍은 저희가 겹쳐 뚫음). 앵글 대신 절곡 묶음은 견적 비교용",
)


def poly_area(pts):
    return abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))) / 2


def classify(d, mode):
    outer = [o for o in d["outline"] if o[0] == "poly" and poly_area(o[1]) >= MIN_OUTER_AREA]
    inner, drill = [], []
    if mode == "all":
        for g in d["through"]:
            if g[0] == "circle" and 2 * g[2] <= DRILL_MAX_D: drill.append(g)
            else: inner.append(g)
    elif d["name"].startswith("P02"):      # 문 개구부만
        polys = [g for g in d["through"] if g[0] == "poly"]
        def area(g):
            us = [q[0] for q in g[1]]; vs = [q[1] for q in g[1]]
            return (max(us) - min(us)) * (max(vs) - min(vs))
        inner = [g for g in polys if area(g) > 10000]
    return outer, inner, drill


def proc_of(it):
    if it.get("bend"): return "절단+절곡"
    if it["mode"] == "all": return "외곽+구멍"
    if it["name"].startswith("P02"): return "외곽+문 개구부"
    return "외곽만"


def add_part(ms, it, ox=0.0, oy=0.0, label=None):
    def P(pts): return [(x + ox, y + oy) for x, y in pts]
    r12 = ms.doc.dxfversion == "AC1009"
    def poly(pts, layer):
        if r12: ms.add_polyline2d(P(pts), close=True, dxfattribs={"layer": layer})
        else: ms.add_lwpolyline(P(pts), close=True, dxfattribs={"layer": layer})
    for o in it["outer"]: poly(o[1], "CUT_OUTER")
    for g in it["inner"]:
        if g[0] == "circle": ms.add_circle((g[1][0] + ox, g[1][1] + oy), g[2], dxfattribs={"layer": "CUT_INNER"})
        else: poly(g[1], "CUT_INNER")
    for g in it["drill"]: ms.add_circle((g[1][0] + ox, g[1][1] + oy), g[2], dxfattribs={"layer": "DRILL"})
    for (a, b) in it.get("bend", []):
        ms.add_line((a[0] + ox, a[1] + oy), (b[0] + ox, b[1] + oy), dxfattribs={"layer": "BEND"})
    if label:
        ms.add_text(label, height=4 if it["W"] < 120 else 6, dxfattribs={"layer": "NOTE"}).set_placement((ox, oy - 12))


def new_doc(ver="R2000"):
    doc = ezdxf.new(ver)
    if ver != "R12": doc.units = ezdxf.units.MM
    for ln, col in (("CUT_OUTER", 7), ("CUT_INNER", 3), ("DRILL", 1), ("BEND", 5), ("NOTE", 8)):
        doc.layers.add(ln, color=col)
    return doc


def drill_summary(drill):
    c = Counter(round(2 * g[2], 1) for g in drill)
    return ", ".join(f"Ø{k}×{v}" for k, v in sorted(c.items()))


def rect_poly(W, H): return ("poly", [(0, 0), (W, 0), (W, H), (0, H)], None)


def check_items(items):
    """외곽이 있는지, 구멍·개구부가 외곽 상자 안에 있는지, 원 구멍~모서리 살"""
    bad = []
    for it in items:
        if not it["outer"]:
            bad.append(f"{it['name']}: 외곽 없음"); continue
        xs = [q[0] for o in it["outer"] for q in o[1]]; ys = [q[1] for o in it["outer"] for q in o[1]]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        for g in it["inner"] + it["drill"]:
            if g[0] == "circle":
                (cx, cy), r = g[1], g[2]; gx0, gx1, gy0, gy1 = cx - r, cx + r, cy - r, cy + r
            else:
                gxs = [q[0] for q in g[1]]; gys = [q[1] for q in g[1]]; gx0, gx1, gy0, gy1 = min(gxs), max(gxs), min(gys), max(gys)
            if gx0 < x0 - 0.01 or gx1 > x1 + 0.01 or gy0 < y0 - 0.01 or gy1 > y1 + 0.01:
                bad.append(f"{it['name']}: 구멍이 판 밖 ({gx0:.1f},{gy0:.1f})")
        # 구멍~판 모서리 살 (얇으면 찢어짐). 1.5mm 미만은 실패, 3mm 미만은 경고
        for o in it["outer"]:
            pts = o[1]; segs = list(zip(pts, pts[1:] + pts[:1]))
            for g in it["inner"] + it["drill"]:
                if g[0] != "circle": continue
                (cx, cy), r = g[1], g[2]
                m = min(seg_dist((cx, cy), a, b) for a, b in segs) - r
                if m < 1.5: bad.append(f"{it['name']}: Ø{2 * r:.1f} 구멍이 판 모서리에서 {m:.1f}mm")
                elif m < 3.0: print(f"  [경고] {it['name']}: Ø{2 * r:.1f} 구멍~모서리 {m:.1f}mm")
    if bad:
        raise SystemExit("발주 묶음 검사 실패:\n  " + "\n  ".join(bad))


def seg_dist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5


def items_from_parts(cad_module, pk):
    items = []
    for prefixes, mode, grp in pk["groups"]:
        parts = [p for p in cad_module.PARTS if p["phase"] == 1 and p["name"].startswith(prefixes)]
        for p in sorted(parts, key=lambda p: p["name"]):
            d = DR.analyze(p)
            outer, inner, drill = classify(d, mode)
            qty = 1 + sum(v for k, v in pk["spare"].items() if d["name"].startswith(k))
            items.append(dict(name=d["name"], title=DR.title_of(d["name"]), mat=d["mat"], W=d["W"], H=d["H"],
                              group=grp, mode=mode, face=d["face"], qty=qty, outer=outer, inner=inner, drill=drill,
                              n_pockets=len(d["pockets"]), n_all=len(d["through"])))
    for e in pk["extra"]:
        it = dict(mode="outer", face="어느 면이든", inner=[], drill=[], n_pockets=0, n_all=0, mat=pk["material"]) | e
        it.setdefault("outer", [rect_poly(e["W"], e["H"])])
        items.append(it)
    return items


def write_package(items, pk, out, version):
    if os.path.isdir(out): shutil.rmtree(out)
    for _, sub in DXF_VERSIONS: os.makedirs(f"{out}/{sub}")
    check_items(items)
    for ver, sub in DXF_VERSIONS:
        for it in items:
            doc = new_doc(ver); ms = doc.modelspace()
            add_part(ms, it, label=f"{it['name']}  {it['W']}x{it['H']}  qty {it['qty']}  {version}  VIEW: {FACE_EN.get(it['face'], it['face'])}")
            if it.get("bend_note"):
                ms.add_text(it["bend_note"], height=2.5, dxfattribs={"layer": "NOTE"}).set_placement((0, -20))
            doc.saveas(os.path.join(out, sub, f"{it['name']}.dxf"))
        doc = new_doc(ver); ms = doc.modelspace(); x = y = 0.0; rowh = 0.0
        for it in items:
            if x + it["W"] > 1300: x = 0.0; y -= rowh + 40; rowh = 0.0
            add_part(ms, it, ox=x, oy=y - it["H"], label=f"{it['name']} x{it['qty']}")
            x += it["W"] + 30; rowh = max(rowh, it["H"])
        doc.saveas(os.path.join(out, sub, "all_panels.dxf"))
    write_pdf(items, pk, os.path.join(out, "확인도면.pdf"), version)
    write_xlsx(items, pk, os.path.join(out, "발주표.xlsx"), version)
    json.dump([{k: it[k] for k in ("name", "title", "mat", "W", "H", "group", "qty")}
               | {"proc": proc_of(it), "drill": drill_summary(it["drill"]), "inner": len(it["inner"]), "outer": len(it["outer"])}
               for it in items], open(os.path.join(out, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for it in items:
        print(f"{it['group']:12s} {it['name']:42s} {it['W']}x{it['H']} x{it['qty']}  {proc_of(it)}  outer {len(it['outer'])}"
              f"  inner {len(it['inner'])}  drill {drill_summary(it['drill'])}")


# ---------------------------------------------------------------- 레이저 업체 색 규칙 (v3.2.1, 알루미늄)
LASER_LAYERS = (("OUTER_CUT", 5), ("INNER_CUT", 2), ("MATERIAL", 6))   # 외부 커팅 / 내부 커팅 / 소재크기
LASER_COLORS = {c for _, c in LASER_LAYERS}
MATERIAL_MARGIN = 5.0


def thick_of(it):
    m = re.search(r"([0-9.]+)\s*T", it["mat"])
    if not m: raise SystemExit(f"{it['name']}: 재료에서 두께를 못 읽음 ({it['mat']})")
    return float(m.group(1))


def write_laser(items, out):
    """평판만 dxf_laser/<판>.dxf. 엔티티 색도 직접 지정 (BYLAYER 안 씀)"""
    if all(it.get("bend") for it in items): return       # 전부 절곡이면 STEP만
    os.makedirs(os.path.join(out, "dxf_laser"))
    for it in items:
        if it.get("bend"): continue
        doc = ezdxf.new("R2000"); doc.units = ezdxf.units.MM
        for ln, col in LASER_LAYERS: doc.layers.add(ln, color=col)
        ms = doc.modelspace()
        A = lambda ln, col: {"layer": ln, "color": col}
        for o in it["outer"]: ms.add_lwpolyline(o[1], close=True, dxfattribs=A("OUTER_CUT", 5))
        for g in it["inner"] + it["drill"]:
            if g[0] == "circle": ms.add_circle(g[1], g[2], dxfattribs=A("INNER_CUT", 2))
            else: ms.add_lwpolyline(g[1], close=True, dxfattribs=A("INNER_CUT", 2))
        xs = [q[0] for o in it["outer"] for q in o[1]]; ys = [q[1] for o in it["outer"] for q in o[1]]
        m = MATERIAL_MARGIN
        ms.add_lwpolyline([(min(xs) - m, min(ys) - m), (max(xs) + m, min(ys) - m), (max(xs) + m, max(ys) + m), (min(xs) - m, max(ys) + m)],
                          close=True, dxfattribs=A("MATERIAL", 6))
        doc.saveas(os.path.join(out, "dxf_laser", f"{it['name']}.dxf"))


def check_laser(items, out):
    """업체 규칙: 색 {2,5,6}만, 구멍 지름 ≥ 두께, 구멍 사이·구멍~모서리 간격 ≥ 두께"""
    bad = []
    for it in items:
        t = thick_of(it)
        if not it.get("bend"):
            fn = os.path.join(out, "dxf_laser", f"{it['name']}.dxf")
            doc = ezdxf.readfile(fn)
            if doc.dxfversion != "AC1015": bad.append(f"{it['name']}: DXF 버전 {doc.dxfversion}")
            for e in doc.modelspace():
                col = e.dxf.color if e.dxf.hasattr("color") else 256
                if col not in LASER_COLORS: bad.append(f"{it['name']}: {e.dxftype()} 색 {col} (레이어 {e.dxf.layer})")
                if e.dxftype() not in ("LWPOLYLINE", "CIRCLE"): bad.append(f"{it['name']}: 엔티티 {e.dxftype()}")
        circles = [g for g in it["inner"] + it["drill"] if g[0] == "circle"]
        polys = [g for g in it["inner"] if g[0] == "poly"]
        segs = [s for o in it["outer"] for s in zip(o[1], o[1][1:] + o[1][:1])] + \
               [s for g in polys for s in zip(g[1], g[1][1:] + g[1][:1])]
        for i, g in enumerate(circles):
            (cx, cy), r = g[1], g[2]
            if 2 * r < max(t, 1.0) - 1e-6: bad.append(f"{it['name']}: 구멍 Ø{2 * r:.1f} < 두께 {t}")
            if segs:
                m = min(seg_dist((cx, cy), a, b) for a, b in segs) - r
                if m < t - 1e-6: bad.append(f"{it['name']}: Ø{2 * r:.1f} ({cx:.1f},{cy:.1f}) 모서리·개구까지 {m:.2f} < {t}")
            for h in circles[i + 1:]:
                gap = ((cx - h[1][0]) ** 2 + (cy - h[1][1]) ** 2) ** 0.5 - r - h[2]
                if gap < t - 1e-6: bad.append(f"{it['name']}: 구멍 ({cx:.1f},{cy:.1f})~({h[1][0]:.1f},{h[1][1]:.1f}) 간격 {gap:.2f} < {t}")
        for g in polys:   # 사각 개구~외곽 상자
            ox = [q[0] for o in it["outer"] for q in o[1]]; oy = [q[1] for o in it["outer"] for q in o[1]]
            gx = [q[0] for q in g[1]]; gy = [q[1] for q in g[1]]
            m = min(min(gx) - min(ox), max(ox) - max(gx), min(gy) - min(oy), max(oy) - max(gy))
            if m < t - 1e-6: bad.append(f"{it['name']}: 개구~모서리 {m:.2f} < {t}")
    if bad:
        raise SystemExit("레이저 업체 규칙 검사 실패:\n  " + "\n  ".join(bad))
    n = sum(1 for it in items if not it.get("bend"))
    print(f"레이저 규칙 검사 통과: dxf_laser {n}장 (색 {{2,5,6}}, 구멍 ≥ 두께, 간격 ≥ 두께), 절곡 {len(items) - n}종은 step/")


def upload_file(it):
    return f"step/{it['name']}.step" if it.get("bend") else f"dxf_laser/{it['name']}.dxf"


def l_angle_step(it, fn):
    """L 10×10 t1 (바깥 치수). 펼친 그림 y 0~10 = 바닥 다리, 10~20 = 세운 다리.
    구멍 위치: 접는 선까지 거리 = 바깥 모서리에서 거리"""
    import cadquery as cq
    L = it["W"]
    s = cq.Workplane("XY").box(L, 10, 1, centered=False).union(cq.Workplane("XY").box(L, 1, 10, centered=False))
    for g in it["drill"]:
        (x, y), r = g[1], g[2]
        if y <= 10:   # 바닥 다리 (Z 방향 구멍), 모서리(y=0)에서 10 - y
            s = s.cut(cq.Workplane("XY").circle(r).extrude(1).translate((x, 10 - y, 0)))
        else:         # 세운 다리 (Y 방향 구멍), 모서리(z=0)에서 y - 10
            s = s.cut(cq.Workplane("XZ").circle(r).extrude(-1).translate((x, 0, y - 10)))
    cq.exporters.export(s, fn)
    return s


def run_foamex(cad_module, outdir, version=""):
    items = items_from_parts(cad_module, FOAMEX)
    write_package(items, FOAMEX, os.path.join(str(outdir), "foamex"), version)
    return items


def bent_item(name, title, W, H, bend_at, holes, finished, qty, note):
    """펼친 그림(바깥 치수 합, 공제 전). bend_at = 아래 변에서 접는 선까지, holes = [(x, y, d)]"""
    return dict(name=name, title=title, mat="알루미늄 1T", W=round(W, 2), H=round(H, 2), qty=qty, group="1T 절곡", mode="all",
                face="펼친 그림", outer=[rect_poly(W, H)], inner=[], drill=[("circle", (x, y), d / 2, None) for x, y, d in holes],
                bend=[((0, bend_at), (W, bend_at))], finished=finished, n_pockets=0, n_all=len(holes),
                bend_note=f"BEND 90 deg at BEND line. FINISHED OUTSIDE: {finished}. FLAT = SUM OF OUTSIDE DIMS - APPLY BEND DEDUCTION",
                note=note)


def run_aluminum(cad_module, outdir, version=""):
    H = cad_module
    pk = dict(ALUMINUM)
    tx, ty = H.TRAY_X, H.TRAY_Y
    pk["extra"] = [
        dict(name=f"T03_tray_cross_strip_X_Al1T_10x{tx - 2:g}", title="트레이 십자 띠 (가로)", W=float(tx - 2), H=10.0, qty=1,
             group="1T 띠·조각", mat="알루미늄 1T", mode="all", note="T03 프레임 세운 다리 사이, 바닥 다리 위에 리벳. 받침 핀 구멍 Ø5.6 ×2",
             drill=[("circle", (px - (H.CH_CX - tx / 2 + 1), 5.0), 2.8, None) for px in H.PIN_X]),
        dict(name=f"T03_tray_cross_strip_Y_Al1T_10x{ty - 2:g}", title="트레이 십자 띠 (세로)", W=round(ty - 2, 2), H=10.0, qty=1,
             group="1T 띠·조각", mat="알루미늄 1T", note="가로 띠 위로 교차"),
        dict(name="T03_tray_corner_plate_Al1T_20x20", title="트레이 모서리 판", W=20.0, H=20.0, qty=4,
             group="1T 띠·조각", mat="알루미늄 1T", note="앵글 맞대기 모서리 바닥 다리 아래에 리벳"),
    ]
    items = items_from_parts(H, pk)
    hv = (H.FLOOR_Z - 12) - (H.BAY_Z0 + H.T05)               # A12 세운 판 바깥 높이
    fl = 13.0                                              # A12 플랜지 바깥 (y124 ~ y137)
    items.append(bent_item("A12_outlet_baffle_Al1T_bent", "출구 배플", 64.0, fl + hv, fl,
                           [(12.0, 6.0, 3.4), (52.0, 6.0, 3.4)], f"plate {hv:.1f} x flange {fl} x W64", 1,
                           f"플랜지 {fl} (구멍 Ø3.4 ×2, 플랜지 끝에서 6, 옆 끝에서 12) + 세운 판 {hv:.1f}, 폭 64"))
    # v3.2.0: 앵글 13조각을 1T L자 절곡으로도 (견적 비교용). 펼침 폭 20 = 바깥 10 + 10, 아래 다리 0~10 / 위 다리 10~20
    d0 = (H.FLOOR_Z + 1)                                  # A19 아래 끝
    strip0 = H.IN0 + H.T05 + 2 + 5                        # A14 앞 끝 (ty0 + 5)
    ang = [  # (이름, 제목, 길이, 수량, 구멍[(x, 다리)], 메모)
        ("A17_floor_angle_F", "바닥 받침 앞", 269.0, 1, [], "라이너에 중성 실리콘"),
        ("A17_floor_angle_LR", "바닥 받침 좌·우", 214.5, 2, [], "라이너에 중성 실리콘"),
        ("A17_floor_angle_LB_RB", "바닥 받침 뒤 조각", 12.5, 2, [], "짧아서 어려우면 제외"),
        ("A20_duct_floor_angle", "덕트 벽 아래 받침", 247.0, 1, [], "A16에 리벳 (겹쳐 뚫기)"),
        ("T03_frame_long", "트레이 프레임 긴 변", float(H.TRAY_X), 2, [], "맞대기 + 모서리 판 리벳"),
        ("T03_frame_short", "트레이 프레임 짧은 변", round(H.TRAY_Y - 20, 2), 2, [], "긴 변 사이 맞대기"),
        ("A14_tray_gap_strip", "트레이 옆 틈막이", 229.0, 2, [(y - strip0, "wall") for y in H.STRIP_BOLTS_Y],
         "벽 다리 구멍 = 앞 끝에서. 2개는 서로 반대 방향으로 접기 (좌우)"),
        ("A19_duct_wall_angle", "덕트 벽 세로 받침", round(H.DUCT_TOP - d0, 2), 2, [(z - d0, "wall") for z in H.DUCTANG_Z],
         "벽 다리 구멍 = 아래 끝에서. 2개는 서로 반대 방향으로 접기 (좌우)"),
        ("A18_partition_angle", "칸막이 받침", 20.0, 2, [(10.0, "floor")], "바닥 다리 가운데. 짧아서 어려우면 제외"),
    ]
    for nm, title, L, q, holes, note in ang:
        hs = [(x, 15.0 if leg == "wall" else 5.0, 3.4) for x, leg in holes]
        it = bent_item(f"{nm}_Al1T_L10x10_{L:g}", title, L, 20.0, 10.0, hs, f"L 10x10 (outside) x {L:g}", q,
                       f"앵글 10×10×1 대신 1T 절곡. {note}. 구멍 다리: 아래 반쪽(0~10) = 바닥/첫 다리, 위 반쪽(10~20) = 벽 다리")
        it["group"] = "1T 절곡 (앵글 대신)"
        items.append(it)
    out = os.path.join(str(outdir), "aluminum")
    write_package(items, pk, out, version)
    write_laser(items, out)
    os.makedirs(os.path.join(out, "step"))
    import cadquery as cq
    src = {"A12_outlet_baffle_Al1T_bent": "A12_outlet_baffle_Al1T_64x56"}
    shapes = {p["name"]: p["shape"] for p in H.PARTS}
    for it in items:
        if not it.get("bend"): continue
        fn = os.path.join(out, "step", it["name"] + ".step")
        if it["name"] in src: cq.exporters.export(shapes[src[it["name"]]], fn)
        else: l_angle_step(it, fn)
    check_laser(items, out)
    a10 = next(it for it in items if it["name"].startswith("A10"))
    print("A10 구멍:", drill_summary(a10["drill"]))
    return items


# ---------------------------------------------------------------- 알루미늄 2차 (v3.3.0: 상자형 히터 덕트)
ALUMINUM2 = dict(
    key="aluminum", title="알루미늄 2차 (히터 덕트)",
    material="알루미늄 판 (업체 기본 재질), 0.5T·1T",
    groups=[], spare={}, extra=[],
    notes=[
        "히터 덕트 4종, 전부 절곡 부품 → 업체에는 step/ 만 올림 (발주표 '올릴 파일' 열). dxf/는 펼친 그림 확인용",
        "치수는 접은 뒤 바깥 치수. 펼친 그림은 바깥 치수 합(굽힘 공제 전) — 전개는 업체 기준. 모두 90° 접기",
        "H06 몸통 0.5T ㄷ자(2번), H10 뚜껑 0.5T(2번), H09 PTC 창판 1T(2번), H11 끝판 1T(2번)",
        "리벳 구멍은 없음 (조립 때 겹쳐 뚫음). 공차 ±0.3mm, 버 제거, 부품 이름 표시",
        "1차 묶음과 같이 발주해도 됨 (v3.3.1). H09 창판은 장착 구멍 없이 개구만 — 구멍 4개는 PTC를 받아 대고 직접 뚫음",
        "H09 개구 56×28은 PTC 핀 면 [가정]: 크면 알루미늄 테이프로 막고, 작으면 줄로 넓힘",
    ],
    footer="H09 장착 구멍(Ø3.4 ×4, 피치 86×24 가정)은 업체 가공에서 뺌 → 확인도면에 안 나옴. PTC 실물에 대고 표시 후 직접",
)


def bent_multi(name, title, mat, W, H, bends, holes, inner, finished, note):
    """여러 번 접는 펼친 그림. bends = [((x0,y0),(x1,y1))], holes = [(x, y, d)], inner = [g]"""
    t = re.search(r"([0-9.]+)\s*T", mat).group(1)
    return dict(name=name, title=title, mat=mat, W=round(W, 2), H=round(H, 2), qty=1, group=f"{t}T 절곡", mode="all",
                face="펼친 그림", outer=[rect_poly(W, H)], inner=inner, drill=[("circle", (x, y), d / 2, None) for x, y, d in holes],
                bend=bends, finished=finished, n_pockets=0, n_all=len(holes) + len(inner),
                bend_note=f"BEND 90 deg at each BEND line. FINISHED OUTSIDE: {finished}. FLAT = SUM OF OUTSIDE DIMS - APPLY BEND DEDUCTION",
                note=note)


def run_aluminum2(cad_module, outdir, version=""):
    H = cad_module
    L = H.BX_Y1 - H.BX_Y0                                  # 덕트 길이 (y)
    side = H.IZ1 - H.BX_Z0                                 # 몸통 옆벽 바깥 높이
    bot = H.BX_X1 - H.BX_X0                                # 몸통 바닥 바깥 폭
    items = []
    # H06 몸통: X = y - BX_Y0, Y: 왼벽(위→아래) | 바닥(왼→오) | 오른벽(아래→위)
    hs = [(y - H.BX_Y0, side + (x - H.BX_X0), 3.4) for x, y in H.DUCT_SO]
    hs += [(y - H.BX_Y0, side + bot + (z - H.BX_Z0), 3.4) for y, z in H.th95_holes]
    hs += [(165 - H.BX_Y0, side + bot + (H.FAN_C[1] - H.BX_Z0), H.KSD["cap_d"] + 1)]
    W, Ht = L, 2 * side + bot
    items.append(bent_multi("H06_heater_duct_Al05", "히터 덕트 몸통 ㄷ자", "알루미늄 0.5T", W, Ht,
                            [((0, side), (W, side)), ((0, side + bot), (W, side + bot))], hs, [],
                            f"U {bot:.1f} x {side:.1f} x L{L:g}", f"바닥 {bot:.1f} + 양옆 {side:.1f}, 길이 {L:g}. 오른벽 = 서모스탯 캡 Ø17 + Ø3.4 ×2"))
    # H10 뚜껑
    top = bot + 2 * H.HT; f = H.FLG
    items.append(bent_multi("H10_heater_duct_lid_Al05", "히터 덕트 뚜껑", "알루미늄 0.5T", L, top + 2 * f,
                            [((0, f), (L, f)), ((0, f + top), (L, f + top))], [], [],
                            f"top {top:.1f} x flange {f} x L{L:g}", f"위판 {top:.1f} + 날개 {f} ×2 (아래로 접기)"))
    # H09 창판 / H11 끝판: X = 날개 | 판(x - IX0) | 날개, Y = z - IZ0
    pw, ph = H.IX1 - H.IX0, H.IZ1 - H.IZ0
    def plate(name, title, holes_xz, inner_xz, finished, note):
        hs = [(f + (x - H.IX0), z - H.IZ0, d) for x, z, d in holes_xz]
        inn = []
        for g in inner_xz:
            if g[0] == "circle": inn.append(("circle", (f + g[1][0] - H.IX0, g[1][1] - H.IZ0), g[2], None))
            else: inn.append(("poly", [(f + x - H.IX0, z - H.IZ0) for x, z in g[1]], None))
        Wp = pw + 2 * f
        return bent_multi(name, title, "알루미늄 1T", Wp, ph, [((f, 0), (f, ph)), ((f + pw, 0), (f + pw, ph))], hs, inn, finished, note)
    x0, z0, x1, z1 = H.WIN
    items.append(plate("H09_ptc_window_plate_Al1T", "PTC 창판", [],      # v3.3.1: 장착 구멍은 직접
                       [("poly", [(x0, z0), (x1, z0), (x1, z1), (x0, z1)])],
                       f"plate {pw:.1f} x {ph:.1f}, flange {f} x2",
                       f"개구 {x1 - x0:g}×{z1 - z0:g} [PTC 핀 면 가정]. 장착 구멍 없음 (PTC 대고 직접). 날개 {f} 2개 같은 쪽으로"))
    items.append(plate("H11_heater_duct_end_Al1T", "히터 덕트 끝판 (팬 쪽)", [(x, z, 3.4) for x, z in H.FAN_HOLES],
                       [("circle", H.FAN_C, 28.5)], f"plate {pw:.1f} x {ph:.1f}, flange {f} x2",
                       f"팬 Ø57 + Ø3.4 ×4. 날개 {f} 2개 같은 쪽으로"))
    out = os.path.join(str(outdir), "aluminum2")
    write_package(items, ALUMINUM2, out, version)
    os.makedirs(os.path.join(out, "step"))
    import cadquery as cq
    shapes = {p["name"]: p["shape"] for p in H.PARTS}
    shapes["H09_ptc_window_plate_Al1T"] = H.H09_VENDOR
    for it in items:
        cq.exporters.export(shapes[it["name"]], os.path.join(out, "step", it["name"] + ".step"))
    check_laser(items, out)
    return items


def run(cad_module, outdir, version=""):
    return run_foamex(cad_module, outdir, version) + run_aluminum(cad_module, outdir, version) + run_aluminum2(cad_module, outdir, version)


def feat_xy(g):
    if g[0] == "circle": return g[1]
    xs = [q[0] for q in g[1]]; ys = [q[1] for q in g[1]]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)


def write_pdf(items, pk, fn, version):
    with PdfPages(fn) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69)); fig.text(0.08, 0.95, f"허브 건조기 {pk['title']} 발주 {version}", fontsize=14)
        y = 0.91
        for s in pk["notes"]:
            for j, ln in enumerate([s[i:i + 68] for i in range(0, len(s), 68)]):
                fig.text(0.08, y, ("· " if j == 0 else "  ") + ln, fontsize=8.5); y -= 0.02
        y -= 0.02
        fig.text(0.08, y, "판 | 재료 | 크기(mm) | 수량 | 가공 | 구멍", fontsize=9); y -= 0.022
        for it in items:
            fig.text(0.08, y, f"{it['name']} ({it['title']}) | {it['mat']} | {it['W']}×{it['H']} | {it['qty']} | {proc_of(it)} | {drill_summary(it['drill']) or '-'}"
                     + (f" + 개구부 {len(it['inner'])}" if it["inner"] else ""), fontsize=6.6); y -= 0.019
        pdf.savefig(fig); plt.close(fig)
        for it in items:
            fig = plt.figure(figsize=(11.69, 8.27)); ax = fig.add_axes([0.06, 0.10, 0.60, 0.76]); ax.set_aspect("equal")
            W, H = it["W"], it["H"]
            for o in it["outer"]:
                xs = [q[0] for q in o[1]] + [o[1][0][0]]; ys = [q[1] for q in o[1]] + [o[1][0][1]]; ax.plot(xs, ys, "k-", lw=1)
            for (a, b) in it.get("bend", []):
                ax.plot([a[0], b[0]], [a[1], b[1]], "b--", lw=1); ax.text(b[0] + 1, b[1], "접는 선 90°", color="b", fontsize=8, va="center")
            rows = []
            feats = [("C", g, "g") for g in it["inner"]] + [("D", g, "r") for g in it["drill"]]
            feats.sort(key=lambda t: (t[0], round(feat_xy(t[1])[1]), feat_xy(t[1])[0]))
            many = len(feats) > 40
            n = {"C": 0, "D": 0}
            for kind, g, col in feats:
                n[kind] += 1; fid = f"{kind}{n[kind]}"
                x, y = feat_xy(g)
                if g[0] == "circle":
                    ax.add_patch(plt.Circle(g[1], g[2], fill=False, color=col, lw=0.4 if many else 0.9)); size = f"Ø{2 * g[2]:.1f}"
                else:
                    xs = [q[0] for q in g[1]] + [g[1][0][0]]; ys = [q[1] for q in g[1]] + [g[1][0][1]]; ax.plot(xs, ys, "-", color=col, lw=0.9)
                    size = f"{max(xs) - min(xs):.1f}×{max(ys) - min(ys):.1f}"
                if not many:
                    ax.plot([x], [y], "+", color=col, ms=5, mew=0.6)
                    ax.annotate(fid, (x, y), fontsize=6.5, color=col, xytext=(4, 3), textcoords="offset points")
                rows.append((fid, "드릴" if kind == "D" else "개구부", size, f"{x:.1f}", f"{y:.1f}"))
            off = max(5.0, max(W, H) * 0.035)
            ax.annotate("", (0, -off), (W, -off), arrowprops=dict(arrowstyle="<->", lw=0.6)); ax.text(W / 2, -off * 2, f"{W}", ha="center", va="top", fontsize=9)
            ax.annotate("", (-off, 0), (-off, H), arrowprops=dict(arrowstyle="<->", lw=0.6)); ax.text(-off * 1.4, H / 2, f"{H}", ha="right", va="center", fontsize=9)
            ax.plot([0], [0], "ko", ms=4)
            step = 50 if max(W, H) > 120 else 10
            ax.set_xticks(range(0, int(W) + 1, step)); ax.set_yticks(range(0, int(H) + 1, step)); ax.tick_params(labelsize=6)
            ax.grid(True, lw=0.3, color="0.85"); ax.set_xlim(-off * 5, W + off * 2); ax.set_ylim(-off * 4, H + off * 2)
            for sp in ax.spines.values(): sp.set_visible(False)
            fig.text(0.06, 0.94, f"{it['name']}  {it['title']}   {it['mat']}   {W}×{H}  수량 {it['qty']}   [{it['group']}: {proc_of(it)}]   {version}", fontsize=10.5)
            if it.get("bend"):
                fig.text(0.06, 0.91, f"펼친 그림 (바깥 치수 합, 굽힘 공제 전 — 전개는 업체 기준).  접은 뒤 바깥 치수: {it['finished']}", fontsize=8.5, color="b")
                fig.text(0.06, 0.885, it.get("note", ""), fontsize=8.5, color="b")
            else:
                fig.text(0.06, 0.91, f"그림 = {it['face']} (이 면이 위로 오게 가공).  좌표 원점 = 그림의 왼쪽 아래 모서리(검은 점), X 오른쪽 +, Y 위쪽 +, 단위 mm", fontsize=8.5, color="b")
                if it.get("note"): fig.text(0.06, 0.885, it["note"], fontsize=8.5, color="b")
            tx = 0.69; ty = 0.86
            if many:
                fig.text(tx, ty, "구멍이 많아 좌표표 대신 개수 (좌표는 DXF 그대로):", fontsize=8); ty -= 0.025
                for k, v in sorted(Counter(r_[2] for r_ in rows).items()):
                    fig.text(tx, ty, f"{k} × {v}", fontsize=8); ty -= 0.022
            else:
                fig.text(tx, ty, "ID   종류    크기          X        Y", fontsize=8); ty -= 0.025
                if not rows:
                    fig.text(tx, ty, "업체 가공 구멍 없음" + ("" if it["mode"] == "all" else "\n(구멍은 받은 뒤 직접)"), fontsize=8)
                for r_ in rows:
                    fig.text(tx, ty, f"{r_[0]:<4} {r_[1]:<4} {r_[2]:<12} {r_[3]:>7} {r_[4]:>7}", fontsize=7.5); ty -= 0.021
            fig.text(tx, 0.06, "원 = 중심 좌표, 사각 = 중심 좌표 (크기는 가로×세로)\nDXF에도 같은 좌표가 그대로 들어 있음", fontsize=7)
            fig.text(0.06, 0.04, "검정 = 외곽, 초록 = 안쪽 개구부, 빨강 = 드릴, 파랑 점선 = 접는 선"
                     + (f"   (CAD 구멍 {it['n_all']}개 중 업체 가공 {len(it['inner']) + len(it['drill'])}개, 포켓 {it['n_pockets']}개는 직접)" if it['n_all'] or it['n_pockets'] else ""), fontsize=8)
            pdf.savefig(fig); plt.close(fig)


def write_xlsx(items, pk, fn, version):
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "발주표"
    F = Font(name="Arial"); B = Font(name="Arial", bold=True)
    ws["A1"] = f"허브 건조기 {pk['title']} 발주표 {version}"; ws["A1"].font = Font(name="Arial", bold=True, size=13)
    r = 2
    for s in pk["notes"]:
        ws.cell(r, 1, "· " + s).font = F; r += 1
    r += 1
    hdr = ["No", "판 (DXF 파일)", "이름", "재료", "가로 mm", "세로 mm", "수량", "가공", "안쪽 개구부", "드릴 구멍", "면적 ㎡(수량 포함)", "그림의 면 / 접은 뒤 치수"] + (["올릴 파일"] if pk["key"] == "aluminum" else [])
    for c, h in enumerate(hdr, 1):
        ws.cell(r, c, h).font = B; ws.cell(r, c).fill = PatternFill("solid", fgColor="FFD9D9D9")
    h0 = r + 1
    for i, it in enumerate(items, 1):
        r += 1
        vals = [i, it["name"] + ".dxf", it["title"], it["mat"], it["W"], it["H"], it["qty"], proc_of(it), len(it["inner"]), drill_summary(it["drill"]) or "-"]
        for c, v in enumerate(vals, 1): ws.cell(r, c, v).font = F
        ws.cell(r, 11, f"=E{r}*F{r}*G{r}/1000000").font = F; ws.cell(r, 11).number_format = "0.000"
        ws.cell(r, 12, it.get("finished") or it["face"]).font = F
        if pk["key"] == "aluminum": ws.cell(r, 13, upload_file(it)).font = F
    r += 1
    ws.cell(r, 6, "합계").font = B; ws.cell(r, 7, f"=SUM(G{h0}:G{r-1})").font = B
    ws.cell(r, 11, f"=SUM(K{h0}:K{r-1})").font = B; ws.cell(r, 11).number_format = "0.000"
    r += 2
    ws.cell(r, 1, pk["footer"]).font = F
    for col, w in zip("ABCDEFGHIJKLM", (5, 42, 20, 22, 9, 9, 6, 14, 11, 22, 16, 30, 46)): ws.column_dimensions[col].width = w
    wb.save(fn)


if __name__ == "__main__":
    spec2 = importlib.util.spec_from_file_location("herb_cad", sys.argv[1]); mod = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(mod)
    run(mod, sys.argv[2] if len(sys.argv) > 2 else "build/vendor", os.environ.get("HERB_VERSION", ""))
