"""두 STEP 파일의 부품별 형상 비교 (리팩터링 검증용)

python cad/tools/compare_step.py A.step B.step [--tol 1e-6] [--md report.md]

STEP 안의 이름 붙은 부품(바디)마다 부피, 바운딩박스, 무게중심을 구해
부품 수, 이름 집합, 부피(상대오차), 바운딩박스·무게중심(절대오차 mm)을 비교한다.
무게중심은 같은 크기의 구멍이 옮겨진 판처럼 부피·bbox가 그대로인 변경을 잡는다.
다르면 종료 코드 1.
"""
import argparse, sys
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TDF import TDF_LabelSequence
from OCP.TDataStd import TDataStd_Name
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.IFSelect import IFSelect_RetDone


def read_parts(path):
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    r = STEPCAFControl_Reader(); r.SetNameMode(True)
    if r.ReadFile(path) != IFSelect_RetDone:
        raise SystemExit(f"STEP 읽기 실패: {path}")
    r.Transfer(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    parts = {}

    def name_of(lab):
        a = TDataStd_Name()
        return a.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), a) else "?"

    def walk(lab):
        if st.IsAssembly_s(lab):
            ch = TDF_LabelSequence(); st.GetComponents_s(lab, ch)
            for i in range(1, ch.Length() + 1):
                walk(ch.Value(i))
            return
        if st.IsReference_s(lab):
            ref = lab.__class__(); st.GetReferredShape_s(lab, ref)
            if st.IsAssembly_s(ref):
                walk(ref); return
            nm = name_of(lab)
            if nm in ("?", ""):
                nm = name_of(ref)
            shp = st.GetShape_s(lab)          # 위치 포함
            g = GProp_GProps(); BRepGProp.VolumeProperties_s(shp, g)
            b = Bnd_Box(); BRepBndLib.Add_s(shp, b, False); b.SetGap(0.0)
            key = nm; k = 2
            while key in parts:
                key = f"{nm}#{k}"; k += 1
            cm = g.CentreOfMass()
            parts[key] = (g.Mass(), b.Get(), (cm.X(), cm.Y(), cm.Z()))
    roots = TDF_LabelSequence(); st.GetFreeShapes(roots)
    for i in range(1, roots.Length() + 1):
        walk(roots.Value(i))
    return parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a"); ap.add_argument("b")
    ap.add_argument("--tol", type=float, default=1e-6, help="부피 상대오차·bbox 절대오차 허용치")
    ap.add_argument("--md", help="마크다운 결과 파일")
    o = ap.parse_args()
    A, B = read_parts(o.a), read_parts(o.b)
    lines = [f"| 항목 | A | B | 결과 |", "|---|---|---|---|"]
    ok = True
    lines.append(f"| 부품 수 | {len(A)} | {len(B)} | {'같음' if len(A) == len(B) else '다름'} |")
    ok &= len(A) == len(B)
    onlyA, onlyB = sorted(set(A) - set(B)), sorted(set(B) - set(A))
    ok &= not onlyA and not onlyB
    lines.append(f"| 이름 집합 | A에만 {len(onlyA)} | B에만 {len(onlyB)} | {'같음' if not onlyA and not onlyB else '다름'} |")
    maxv = maxb = maxc = 0.0; bad = []
    totA = totB = 0.0
    for n in sorted(set(A) & set(B)):
        va, ba, ca = A[n]; vb, bb, cb = B[n]
        totA += va; totB += vb
        dv = abs(va - vb) / max(abs(va), 1e-9)
        db = max(abs(x - y) for x, y in zip(ba, bb))
        dc = max(abs(x - y) for x, y in zip(ca, cb))
        maxv, maxb, maxc = max(maxv, dv), max(maxb, db), max(maxc, dc)
        if dv > o.tol or db > o.tol or dc > o.tol:
            bad.append((n, va, vb, db, dc))
    ok &= not bad
    lines.append(f"| 부피 최대 상대오차 | | | {maxv:.2e} |")
    lines.append(f"| 바운딩박스 최대 오차 (mm) | | | {maxb:.2e} |")
    lines.append(f"| 무게중심 최대 오차 (mm) | | | {maxc:.2e} |")
    lines.append(f"| 전체 부피 (cm³) | {totA/1000:.3f} | {totB/1000:.3f} | |")
    lines.append(f"| 허용치({o.tol:g}) 넘는 부품 | | | {len(bad)} |")
    res = "\n".join(lines)
    for n in onlyA[:60]: res += f"\n- A에만: {n}"
    for n in onlyB[:60]: res += f"\n- B에만: {n}"
    shown = [x for x in bad if not any(k in x[0] for k in ("_bolt", "_nut", "_so_", "screw", "insert"))]
    for n, va, vb, db, dc in shown[:60]: res += f"\n- 다름: {n} 부피 {va:.1f} → {vb:.1f}, bbox 차 {db:.2f}, 무게중심 차 {dc:.3f}"
    if len(bad) > len(shown): res += f"\n- (체결부품 {len(bad) - len(shown)}개 다름, 생략)"
    res += "\n\n결론: " + ("**형상 동일**" if ok else "**형상 다름**")
    print(res)
    if o.md:
        open(o.md, "w", encoding="utf-8").write(res + "\n")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
