#!/usr/bin/env python3
"""herb-dryer 빌드: 한 명령으로 모든 생성물을 build/ 에 만든다.

    python build.py            # 전부 (= make all)
    python build.py step check # 원하는 단계만
    python build.py --no-render

단계 (순서대로):
  step      build/herb_dryer.step
  check     간섭 검사 → build/interference.txt   (1건이라도 있으면 빌드 실패, 1차↔2차 제외)
  drawings  build/drawings/ 구멍표 PDF, 1:1 인쇄 PDF, dxf/
  vendor    build/vendor/foamex/ 외주 발주 패키지 (포맥스 외관판 DXF, 발주표, 확인도면)
  stl       build/stl/ 3D 프린트 부품 STL (파일 이름에 버전)
  render    build/render/ 외관·내부·단면 PNG (실패해도 빌드는 계속)
  csv       build/fasteners.csv, build/print_parts.csv
  bom       build/bom_csv/ BOM 시트별 CSV

버전 문자열: 환경변수 HERB_VERSION → `git describe --tags` → "dev"
"""
import argparse
import csv
import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CAD = ROOT / "cad" / "herb_dryer_cad.py"
TOOLS = ROOT / "cad" / "tools"
BOM = ROOT / "bom" / "herb_dryer_BOM.xlsx"
STEPS = ["step", "check", "drawings", "vendor", "stl", "render", "csv", "bom"]


def version() -> str:
    v = os.environ.get("HERB_VERSION")
    if v:
        return v
    try:
        return subprocess.check_output(["git", "describe", "--tags", "--always", "--dirty"], cwd=ROOT,
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return "dev"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def log(msg):
    print(f"\n=== {msg}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("steps", nargs="*", default=["all"], help=f"all 또는 {' '.join(STEPS)}")
    ap.add_argument("--out", default=str(ROOT / "build"), help="출력 폴더 (기본 build/)")
    ap.add_argument("--no-render", action="store_true", help="렌더 건너뛰기")
    a = ap.parse_args()
    steps = STEPS if "all" in a.steps else a.steps
    bad = [s for s in steps if s not in STEPS]
    if bad:
        ap.error(f"모르는 단계: {bad}")
    if a.no_render and "render" in steps:
        steps = [s for s in steps if s != "render"]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    ver = version()
    (out / "VERSION.txt").write_text(ver + "\n", encoding="utf-8")
    print(f"herb-dryer 빌드 {ver} → {out}  단계: {' '.join(steps)}")

    failed, warned = [], []
    m = None
    if set(steps) & {"step", "check", "drawings", "vendor", "stl", "csv"}:
        log("CAD 실행 (params.yaml 읽기)")
        t = time.time()
        m = load(CAD, "herb_cad")
        print(f"부품 {len(m.PARTS)}개, {time.time() - t:.1f}s")

    if "step" in steps:
        log("1. STEP")
        m.build_assembly().export(str(out / "herb_dryer.step"))
        print(out / "herb_dryer.step")

    if "check" in steps:
        log("2. 간섭 검사")
        ci = load(TOOLS / "check_interf.py", "herb_check_interf")
        res = ci.check(m)
        txt = ci.report(res, len(m.PARTS))
        (out / "interference.txt").write_text(txt, encoding="utf-8")
        print(txt, end="")
        if res:
            failed.append(f"간섭 {len(res)}건 (build/interference.txt)")

    if "drawings" in steps:
        log("3. 도면 (구멍표 PDF, 1:1 인쇄 PDF, DXF)")
        dr = load(TOOLS / "drawings.py", "herb_drawings")
        fails = dr.run(m, out / "drawings", version=ver)
        if fails:
            warned.append(f"도면 실패 판: {fails}")

    if "vendor" in steps:
        log("3b. 외주 발주 패키지 (포맥스 외관판)")
        vp = load(TOOLS / "vendor_pack.py", "herb_vendor_pack")
        vp.run(m, out / "vendor", version=ver)

    if "stl" in steps:
        log("4. 3D 프린트 STL")
        import cadquery as cq
        d = out / "stl"; d.mkdir(exist_ok=True)
        for old in d.glob("*.stl"):
            old.unlink()
        n = 0
        for p in print_parts(m):
            cq.exporters.export(p["shape"], str(d / f"{p['name']}_{ver}.stl"), tolerance=0.05, angularTolerance=0.1)
            n += 1
        print(f"STL {n}개 → {d}")

    if "render" in steps:
        log("5. 렌더 (실패해도 빌드는 계속)")
        r = subprocess.run([sys.executable, str(TOOLS / "render.py"), str(CAD), str(out / "render"), "all"],
                           env={**os.environ, "HERB_VERSION": ver})
        if r.returncode != 0:
            warned.append(f"렌더 실패 (exit {r.returncode}) — 오프스크린 환경 확인 (xvfb-run)")

    if "csv" in steps:
        log("6. 체결부품·3D 프린트 목록 CSV")
        with open(out / "fasteners.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, lineterminator="\n"); w.writerow(["No", "품목 (용도)", "수량"])
            for i, (k, v) in enumerate(sorted(m.FASTENERS.items()), 1):
                w.writerow([i, k, v])
            w.writerow(["", "합계 (개)", sum(m.FASTENERS.values())])
        with open(out / "print_parts.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["No", "부품", "STL 파일", "X", "Y", "Z", "부피 cm³(100%)", "비고"])
            tot = 0
            for i, p in enumerate(print_parts(m), 1):
                s = p["shape"].val(); bb = s.BoundingBox(); vol = s.Volume() / 1000; tot += vol
                w.writerow([i, p["name"], f"{p['name']}_{ver}.stl", round(bb.xlen, 1), round(bb.ylen, 1),
                            round(bb.zlen, 1), round(vol, 1), p["note"]])
            w.writerow(["", "부피 합계 cm³", "", "", "", "", round(tot, 1), ""])
            w.writerow(["", "예상 필라멘트 g (PETG 1.27g/cm³ × 채움 50%)", "", "", "", "", round(tot * 1.27 * 0.5), ""])
        print(out / "fasteners.csv", out / "print_parts.csv")

    if "bom" in steps:
        log("7. BOM 시트별 CSV")
        bt = load(ROOT / "scripts" / "bom_to_csv.py", "herb_bom_to_csv")
        for fpath in bt.export(BOM, out / "bom_csv"):
            print(fpath)

    log("결과")
    for w_ in warned:
        print("경고:", w_)
    if failed:
        for f_ in failed:
            print("실패:", f_)
        sys.exit(1)
    print(f"성공 ({ver})")


def print_parts(m):
    return [p for p in m.PARTS if p["phase"] == 1 and p["proc"] == "3D프린트"]


if __name__ == "__main__":
    main()
