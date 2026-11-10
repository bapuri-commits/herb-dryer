"""BOM xlsx → 시트별 CSV (git diff·PR 리뷰용)

python scripts/bom_to_csv.py [bom/herb_dryer_BOM.xlsx] [build/bom_csv]

- 시트마다 `NN_<시트이름>.csv` 하나 (UTF-8 BOM, 엑셀에서 한글 안 깨짐)
- 수식은 계산값이 아니라 수식 그대로 (=E5*F5) 내보낸다 → 무엇이 바뀌었는지 보이게
- 끝쪽 빈 행·빈 열은 자른다
"""
import csv
import re
import sys
from pathlib import Path

import openpyxl


def safe(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", name).strip("_")


def export(xlsx: Path, outdir: Path) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("*.csv"):
        old.unlink()
    wb = openpyxl.load_workbook(xlsx, data_only=False)
    files = []
    for i, ws in enumerate(wb.worksheets, 1):
        rows = [["" if c is None else str(c) for c in r] for r in ws.iter_rows(values_only=True)]
        while rows and not any(rows[-1]):
            rows.pop()
        width = max((max((j + 1 for j, c in enumerate(r) if c), default=0) for r in rows), default=0)
        rows = [r[:width] for r in rows]
        fn = outdir / f"{i:02d}_{safe(ws.title)}.csv"
        with open(fn, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["행"] + [openpyxl.utils.get_column_letter(j + 1) for j in range(width)])
            for n, r in enumerate(rows, 1):
                w.writerow([n] + r)
        files.append(fn)
    return files


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    xlsx = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "bom" / "herb_dryer_BOM.xlsx"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "build" / "bom_csv"
    for f in export(xlsx, out):
        print(f)
