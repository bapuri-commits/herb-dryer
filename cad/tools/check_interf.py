"""부품 간섭 검사

python cad/tools/check_interf.py cad/herb_dryer_cad.py [출력 txt]

겹치는 부피가 0.05 mm³ 넘는 부품 쌍을 출력한다. 1건이라도 있으면 종료 코드 1.
1차 부품과 2차 부품(phase=2) 사이는 대체 관계라 검사하지 않는다.
"""
import sys, importlib.util
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

THRESH = 0.05   # mm³


def load_cad(path):
    spec = importlib.util.spec_from_file_location("herb_cad", path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def check(m):
    P = []
    for p in m.PARTS:
        s = p["shape"].val().wrapped if hasattr(p["shape"], "val") else p["shape"]
        b = Bnd_Box(); BRepBndLib.Add_s(s, b); b.SetGap(0.0)
        P.append((p["name"], p["kind"], p["phase"], s, b))
    res = []
    for i in range(len(P)):
        for j in range(i + 1, len(P)):
            a, b = P[i], P[j]
            if a[4].IsOut(b[4]): continue
            if a[2] != b[2]: continue   # 1차-2차 대체 관계
            c = BRepAlgoAPI_Common(a[3], b[3]).Shape(); g = GProp_GProps(); BRepGProp.VolumeProperties_s(c, g); v = g.Mass()
            if v > THRESH: res.append((v, a[0], b[0], a[1], b[1]))
    res.sort(reverse=True)
    return res


def report(res, n_parts):
    lines = [f"{v:9.2f}  {a}  <->  {b}   [{ka}/{kb}]" for v, a, b, ka, kb in res]
    lines.append(f"TOTAL {len(res)}  (부품 {n_parts}개, 기준 {THRESH} mm³, 1차↔2차 제외)")
    return "\n".join(lines) + "\n"


def main():
    m = load_cad(sys.argv[1])
    txt = report(check(m), len(m.PARTS))
    print(txt, end="")
    if len(sys.argv) > 2:
        open(sys.argv[2], "w", encoding="utf-8").write(txt)
    sys.exit(0 if txt.startswith("TOTAL 0") else 1)


if __name__ == "__main__":
    main()
