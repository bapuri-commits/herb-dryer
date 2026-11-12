"""외주 발주 패키지: 포맥스 외관판 (CNC 라우터 재단)

python cad/tools/vendor_pack.py <cad.py> [출력폴더]

결과 (출력폴더/foamex/):
  dxf/<판>.dxf       판마다 1개, 단위 mm, 1:1, AutoCAD 2000(R2000) 형식
  dxf_R12/           같은 내용, AutoCAD R12 형식 (구버전 CAM용)
  */all_panels.dxf   모든 판을 한 장에 늘어놓은 것 (견적용, 배치는 업체가)
  발주표.xlsx        판·크기·수량·가공 범위·구멍 수, 업체 전달 사항
  확인도면.pdf       판마다 1쪽 (외곽 치수, 구멍 지름별 개수)

레이어
  CUT_OUTER   외곽 절단
  CUT_INNER   안쪽 개구부 절단 (사각 구멍, Ø8 넘는 원)
  DRILL       드릴 구멍 (Ø8 이하 원)
  NOTE        글자·치수 — 자르지 않음

가공 범위
  A 묶음  외곽 + 구멍까지 (구멍 위치가 설계만으로 정해지는 판)
  B 묶음  외곽만 (경첩·손잡이·LCD·USB·로커·보드 실측 후 직접 뚫음). 앞판은 문 개구부만 포함
  포켓·접시머리 자리는 넣지 않음 (직접 가공)
"""
import os, sys, json, importlib.util
from collections import Counter
import ezdxf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("herb_drawings_vp", os.path.join(HERE, "drawings.py"))
DR = importlib.util.module_from_spec(spec); spec.loader.exec_module(DR)

MATERIAL = "포맥스(발포 PVC) 5T 회색"
DRILL_MAX_D = 8.0
GROUP_A = ("P01", "P03", "P06", "P07", "K03", "K04", "K05")
GROUP_B = ("P02", "D01", "K01", "K02", "K06")
SPARE = {"K01": 1, "K02": 1, "D01": 1}          # 손 가공 판 여분
EXTRA = [  # CAD 판이 아닌 추가 조각
    dict(name="D02_door_plug_foamex5T_257x166", title="문 플러그 포맥스 조각", W=257.0, H=166.0, group="B", qty=1,
         note="문 플러그용 (앞판 개구부 조각 대신). 외곽만"),
]
VENDOR_NOTES = [
    f"재료: {MATERIAL}, 모든 판 같은 두께",
    "치수는 완성 치수 (공구 보정은 업체에서). 공차 ±0.5mm, 외곽 직각",
    "DXF: dxf/ = AutoCAD 2000 형식, dxf_R12/ = R12 형식 (같은 내용). 단위 mm, 1:1",
    "CUT_OUTER = 외곽 절단, CUT_INNER = 안쪽 개구부 절단, DRILL = 구멍 가공 (Ø 그대로), NOTE = 글자 — 자르지 마세요",
    "안쪽 모서리는 공구 반경 R1.5 이하 둥글어도 됩니다",
    "B 묶음은 외곽만 (구멍은 저희가 직접 뚫습니다). 앞판 P02는 문 개구부만 잘라 주세요",
    "DXF는 판마다 정해진 면(확인도면에 표시)에서 본 그림입니다. 그 면이 위로 오게 가공하고, 위 면에 연필로 판 이름을 적어 주세요",
    "보호 필름은 붙은 채로 보내 주세요",
    "레이저 가공 불가 재료(PVC)이므로 CNC 라우터 또는 재단기로 가공",
]


def classify(d, group):
    outer = [o for o in d["outline"] if o[0] == "poly"]
    inner, drill = [], []
    if group == "A":
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


FACE_EN = {"바깥(왼쪽)에서 본 면": "OUTSIDE (left side)", "바깥(오른쪽)에서 본 면": "OUTSIDE (right side)",
           "앞에서 본 면": "FRONT (outside)", "뒤(바깥)에서 본 면": "BACK (outside)",
           "위에서 본 면 (아래쪽=앞)": "TOP VIEW (bottom edge = front)", "어느 면이든": "ANY"}
# 업체 요청으로 낮은 버전도 함께: R2000(AutoCAD 2000) 기본 + R12(가장 호환 좋음)
DXF_VERSIONS = (("R2000", "dxf"), ("R12", "dxf_R12"))


def add_part(ms, d, outer, inner, drill, ox=0.0, oy=0.0, label=None):
    def P(pts): return [(x + ox, y + oy) for x, y in pts]
    r12 = ms.doc.dxfversion == "AC1009"
    def poly(pts, layer):
        if r12: ms.add_polyline2d(P(pts), close=True, dxfattribs={"layer": layer})
        else: ms.add_lwpolyline(P(pts), close=True, dxfattribs={"layer": layer})
    for o in outer: poly(o[1], "CUT_OUTER")
    for g in inner:
        if g[0] == "circle": ms.add_circle((g[1][0] + ox, g[1][1] + oy), g[2], dxfattribs={"layer": "CUT_INNER"})
        else: poly(g[1], "CUT_INNER")
    for g in drill: ms.add_circle((g[1][0] + ox, g[1][1] + oy), g[2], dxfattribs={"layer": "DRILL"})
    if label:
        ms.add_text(label, height=6, dxfattribs={"layer": "NOTE"}).set_placement((ox, oy - 12))


def new_doc(ver="R2000"):
    doc = ezdxf.new(ver)
    if ver != "R12": doc.units = ezdxf.units.MM
    for ln, col in (("CUT_OUTER", 7), ("CUT_INNER", 3), ("DRILL", 1), ("NOTE", 8)):
        doc.layers.add(ln, color=col)
    return doc


def drill_summary(drill):
    c = Counter(round(2 * g[2], 1) for g in drill)
    return ", ".join(f"Ø{k}×{v}" for k, v in sorted(c.items()))


def rect_poly(W, H): return ("poly", [(0, 0), (W, 0), (W, H), (0, H)], None)


def run(cad_module, outdir, version=""):
    out = os.path.join(str(outdir), "foamex")
    for _, sub in DXF_VERSIONS:
        os.makedirs(f"{out}/{sub}", exist_ok=True)
        for f in os.listdir(f"{out}/{sub}"): os.remove(os.path.join(out, sub, f))
    parts = [p for p in cad_module.PARTS if p["phase"] == 1 and p["name"].startswith(GROUP_A + GROUP_B)]
    items = []
    for p in sorted(parts, key=lambda p: (0 if p["name"].startswith(GROUP_A) else 1, p["name"])):
        d = DR.analyze(p)
        grp = "A" if p["name"].startswith(GROUP_A) else "B"
        outer, inner, drill = classify(d, grp)
        items.append(dict(name=d["name"], title=DR.title_of(d["name"]), W=d["W"], H=d["H"], group=grp, face=d["face"],
                          qty=1 + SPARE.get(d["name"][:3], 0), outer=outer, inner=inner, drill=drill,
                          n_pockets=len(d["pockets"]), n_all=len(d["through"])))
    for e in EXTRA:
        items.append(dict(e, face="어느 면이든", outer=[rect_poly(e["W"], e["H"])], inner=[], drill=[], n_pockets=0, n_all=0))
    for ver, sub in DXF_VERSIONS:
        for it in items:
            doc = new_doc(ver); ms = doc.modelspace()
            add_part(ms, None, it["outer"], it["inner"], it["drill"],
                     label=f"{it['name']}  {it['W']}x{it['H']}  qty {it['qty']}  {version}  VIEW: {FACE_EN.get(it['face'], it['face'])}")
            doc.saveas(os.path.join(out, sub, f"{it['name']}.dxf"))
        # 한 장 배치 (견적용)
        doc = new_doc(ver); ms = doc.modelspace(); x = y = 0.0; rowh = 0.0
        for it in items:
            if x + it["W"] > 1300: x = 0.0; y -= rowh + 40; rowh = 0.0
            add_part(ms, None, it["outer"], it["inner"], it["drill"], ox=x, oy=y - it["H"], label=f"{it['name']} x{it['qty']}")
            x += it["W"] + 30; rowh = max(rowh, it["H"])
        doc.saveas(os.path.join(out, sub, "all_panels.dxf"))
    if os.path.exists(os.path.join(out, "all_panels.dxf")): os.remove(os.path.join(out, "all_panels.dxf"))
    write_pdf(items, os.path.join(out, "확인도면.pdf"), version)
    write_xlsx(items, os.path.join(out, "발주표.xlsx"), version)
    json.dump([{k: it[k] for k in ("name", "title", "W", "H", "group", "qty")} | {"drill": drill_summary(it["drill"]), "inner": len(it["inner"])}
               for it in items], open(os.path.join(out, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for it in items:
        print(f"{it['group']} {it['name']:40s} {it['W']}x{it['H']} x{it['qty']}  inner {len(it['inner'])}  drill {drill_summary(it['drill'])}")
    return items


def feat_xy(g):
    if g[0] == "circle": return g[1]
    xs = [q[0] for q in g[1]]; ys = [q[1] for q in g[1]]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)


def write_pdf(items, fn, version):
    with PdfPages(fn) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69)); fig.text(0.08, 0.95, f"허브 건조기 외관 포맥스 발주 {version}", fontsize=14)
        y = 0.91
        for s in VENDOR_NOTES:
            fig.text(0.08, y, "· " + s, fontsize=8.5); y -= 0.022
        y -= 0.02
        fig.text(0.08, y, "판 | 크기(mm) | 수량 | 가공 | 구멍", fontsize=9); y -= 0.022
        for it in items:
            proc = "외곽+구멍" if it["group"] == "A" else ("외곽+문 개구부" if it["name"].startswith("P02") else "외곽만")
            fig.text(0.08, y, f"{it['name']} ({it['title']}) | {it['W']}×{it['H']} | {it['qty']} | {proc} | {drill_summary(it['drill']) or '-'}"
                     + (f" + 개구부 {len(it['inner'])}" if it["inner"] else ""), fontsize=7.5); y -= 0.02
        pdf.savefig(fig); plt.close(fig)
        for it in items:
            fig = plt.figure(figsize=(11.69, 8.27)); ax = fig.add_axes([0.06, 0.10, 0.60, 0.76]); ax.set_aspect("equal")
            W, H = it["W"], it["H"]
            for o in it["outer"]:
                xs = [q[0] for q in o[1]] + [o[1][0][0]]; ys = [q[1] for q in o[1]] + [o[1][0][1]]; ax.plot(xs, ys, "k-", lw=1)
            rows = []
            feats = [("C", g, "g") for g in it["inner"]] + [("D", g, "r") for g in it["drill"]]
            feats.sort(key=lambda t: (t[0], round(feat_xy(t[1])[1]), feat_xy(t[1])[0]))
            n = {"C": 0, "D": 0}
            for kind, g, col in feats:
                n[kind] += 1; fid = f"{kind}{n[kind]}"
                x, y = feat_xy(g)
                if g[0] == "circle":
                    ax.add_patch(plt.Circle(g[1], g[2], fill=False, color=col, lw=0.9)); size = f"Ø{2 * g[2]:.1f}"
                else:
                    xs = [q[0] for q in g[1]] + [g[1][0][0]]; ys = [q[1] for q in g[1]] + [g[1][0][1]]; ax.plot(xs, ys, "-", color=col, lw=0.9)
                    size = f"{max(xs) - min(xs):.1f}×{max(ys) - min(ys):.1f}"
                ax.plot([x], [y], "+", color=col, ms=5, mew=0.6)
                ax.annotate(fid, (x, y), fontsize=6.5, color=col, xytext=(4, 3), textcoords="offset points")
                rows.append((fid, "드릴" if kind == "D" else "개구부", size, f"{x:.1f}", f"{y:.1f}"))
            ax.annotate("", (0, -10), (W, -10), arrowprops=dict(arrowstyle="<->", lw=0.6)); ax.text(W / 2, -20, f"{W}", ha="center", fontsize=9)
            ax.annotate("", (-10, 0), (-10, H), arrowprops=dict(arrowstyle="<->", lw=0.6)); ax.text(-14, H / 2, f"{H}", ha="right", va="center", fontsize=9)
            ax.plot([0], [0], "ko", ms=4); ax.text(2, 3, "원점 (0,0)", fontsize=7)
            ax.set_xticks(range(0, int(W) + 1, 50)); ax.set_yticks(range(0, int(H) + 1, 50)); ax.tick_params(labelsize=6)
            ax.grid(True, lw=0.3, color="0.85"); ax.set_xlim(-45, W + 15); ax.set_ylim(-32, H + 15)
            for sp in ax.spines.values(): sp.set_visible(False)
            proc = "외곽 + 구멍" if it["group"] == "A" else ("외곽 + 문 개구부만" if it["name"].startswith("P02") else "외곽만 (구멍은 직접)")
            fig.text(0.06, 0.94, f"{it['name']}  {it['title']}   {W}×{H}  수량 {it['qty']}   [{it['group']} 묶음: {proc}]   {version}", fontsize=11)
            fig.text(0.06, 0.91, f"그림 = {it['face']} (이 면이 위로 오게 가공).  좌표 원점 = 그림의 왼쪽 아래 모서리, X 오른쪽 +, Y 위쪽 +, 단위 mm", fontsize=8.5, color="b")
            tx = 0.69; ty = 0.86
            fig.text(tx, ty, "ID   종류    크기          X        Y", fontsize=8); ty -= 0.025
            if not rows:
                fig.text(tx, ty, "업체 가공 구멍 없음" + ("" if it["group"] == "A" else "\n(구멍 위치는 구멍표 PDF, 부품 실측 후 직접)"), fontsize=8)
            for r_ in rows:
                fig.text(tx, ty, f"{r_[0]:<4} {r_[1]:<4} {r_[2]:<12} {r_[3]:>7} {r_[4]:>7}", fontsize=7.5); ty -= 0.021
            fig.text(tx, 0.06, "원 = 중심 좌표, 사각 = 중심 좌표 (크기는 가로×세로)\nDXF에도 같은 좌표가 그대로 들어 있음", fontsize=7)
            fig.text(0.06, 0.04, f"검정 = 외곽, 초록 = 안쪽 개구부, 빨강 = 드릴"
                     + (f"   (CAD 구멍 {it['n_all']}개 중 업체 가공 {len(it['inner']) + len(it['drill'])}개, 포켓 {it['n_pockets']}개는 직접)" if it['n_all'] or it['n_pockets'] else ""), fontsize=8)
            pdf.savefig(fig); plt.close(fig)


def write_xlsx(items, fn, version):
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "발주표"
    F = Font(name="Arial"); B = Font(name="Arial", bold=True)
    ws["A1"] = f"허브 건조기 외관 포맥스 발주표 {version}"; ws["A1"].font = Font(name="Arial", bold=True, size=13)
    r = 2
    for s in VENDOR_NOTES:
        ws.cell(r, 1, "· " + s).font = F; r += 1
    r += 1
    hdr = ["No", "판 (DXF 파일)", "이름", "가로 mm", "세로 mm", "수량", "가공", "안쪽 개구부", "드릴 구멍", "면적 ㎡(수량 포함)", "그림의 면"]
    for c, h in enumerate(hdr, 1):
        ws.cell(r, c, h).font = B; ws.cell(r, c).fill = PatternFill("solid", fgColor="FFD9D9D9")
    h0 = r + 1
    for i, it in enumerate(items, 1):
        r += 1
        proc = "외곽+구멍" if it["group"] == "A" else ("외곽+문 개구부" if it["name"].startswith("P02") else "외곽만")
        vals = [i, it["name"] + ".dxf", it["title"], it["W"], it["H"], it["qty"], proc, len(it["inner"]), drill_summary(it["drill"]) or "-"]
        for c, v in enumerate(vals, 1): ws.cell(r, c, v).font = F
        ws.cell(r, 10, f"=D{r}*E{r}*F{r}/1000000").font = F; ws.cell(r, 10).number_format = "0.000"
        ws.cell(r, 11, it["face"]).font = F
    r += 1
    ws.cell(r, 5, "합계").font = B; ws.cell(r, 6, f"=SUM(F{h0}:F{r-1})").font = B
    ws.cell(r, 10, f"=SUM(J{h0}:J{r-1})").font = B; ws.cell(r, 10).number_format = "0.000"
    r += 2
    ws.cell(r, 1, "여분: K01·K02·D01은 저희가 손으로 구멍을 뚫는 판이라 1장씩 더 주문 (수량에 포함)").font = F
    for col, w in zip("ABCDEFGHIJK", (5, 40, 18, 9, 9, 6, 14, 11, 26, 16, 26)): ws.column_dimensions[col].width = w
    wb.save(fn)


if __name__ == "__main__":
    spec2 = importlib.util.spec_from_file_location("herb_cad", sys.argv[1]); mod = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(mod)
    run(mod, sys.argv[2] if len(sys.argv) > 2 else "build/vendor", os.environ.get("HERB_VERSION", ""))
