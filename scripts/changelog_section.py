"""CHANGELOG.md 에서 한 버전의 내용만 꺼낸다 (Release 노트용)

python scripts/changelog_section.py v2.9.0
`## [v2.9.0]` 줄부터 다음 `## [` 줄 전까지. 없으면 종료 코드 1 (태그 전에 CHANGELOG를 쓰게).
"""
import re
import sys
from pathlib import Path

tag = sys.argv[1]
text = Path(__file__).resolve().parent.parent.joinpath("CHANGELOG.md").read_text(encoding="utf-8")
m = re.search(rf"^## \[{re.escape(tag)}\][^\n]*\n(.*?)(?=^## \[|\Z)", text, flags=re.S | re.M)
if not m:
    sys.exit(f"CHANGELOG.md 에 '## [{tag}]' 항목이 없습니다. 태그 전에 CHANGELOG를 먼저 쓰세요.")
body = m.group(1).strip()
print(body)
print("\n---\n팀원은 아래 첨부 파일을 받아서 작업합니다. 3D 프린트·재단한 부품에는 이 버전(" + tag + ")을 기록하세요.")
