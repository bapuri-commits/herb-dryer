# 작업 흐름: 역할, 변경 요청, 버전 규칙

## 역할

| 역할 | 사람 | 하는 일 |
|---|---|---|
| 통합 담당 | 1명 (`.github/CODEOWNERS`) | **CAD(`cad/`)와 BOM(`bom/`)을 고치는 유일한 사람.** 이슈를 보고 PR을 만들고, CI 확인 후 태그를 붙인다 |
| 팀원 | 나머지 | 이슈로 요청·보고한다. 파일은 **Release**에서 받는다 (레포를 실행할 필요 없음) |

팀원도 `docs/`, `firmware/`는 직접 PR 할 수 있다. `cad/`·`bom/`을 바꾸는 PR은 통합 담당의 리뷰가 있어야 병합된다.

## 변경 요청 절차

```
이슈 ──▶ 통합 담당이 브랜치·PR ──▶ CI (빌드 + 간섭 검사) ──▶ 병합 ──▶ CHANGELOG ──▶ 태그 ──▶ Release
```

1. **이슈 열기** (New issue에서 양식 선택)
   - `CAD 변경 요청`: 무엇을 왜, 영향받는 CAD 바디 이름 ([naming.md](naming.md)), 급한 정도
   - `실측 결과`: 부품, BOM No, 잰 값, 사진, `params.yaml`의 키
   - `부품 구매·확정`: BOM No, 링크, 가격, 상태
2. **통합 담당이 PR**
   - 실측 반영: `cad/params.yaml`의 `value`, `status: 실측`, `source: 측정자 YYYY-MM-DD` **세 개만** 바꾼다
   - 사진은 `docs/measurements/`에 ([README](measurements/README.md))
   - PR 설명에 `Closes #이슈번호`
   - BOM을 바꾸면 **어느 시트의 몇 행을 바꿨는지** PR 설명에 적는다 (xlsx는 diff가 안 보임. CI 요약에 시트별 CSV diff가 붙음)
3. **CI**: `cad-build`(STEP, 간섭 검사, 도면, STL, 렌더)와 `firmware-build`가 초록이어야 병합 가능.
   PR이면 CI 요약에 **기준 브랜치 대비 부품별 형상 비교**가 나온다 → 의도한 부품만 바뀌었는지 확인
4. **병합 후 버전 올리기** (통합 담당)
   - `CHANGELOG.md` 맨 위에 새 버전 항목 (바뀐 것 + 다시 만들어야 하는 것) → main에 PR
   - 태그: `git tag v2.9.1 && git push origin v2.9.1`
   - Release 워크플로가 파일을 만들어 붙인다. CHANGELOG에 그 버전 항목이 없으면 Release가 실패한다
5. **팀원**은 Release의 새 파일로 작업한다

## 버전 규칙

태그 형식: `vMAJOR.MINOR.PATCH` (예: `v2.9.0`)

| 올리는 자리 | 언제 | 예 |
|---|---|---|
| **패치** | `cad/params.yaml` 값만 바뀜 (실측 반영) | `v2.9.0 → v2.9.1` |
| **마이너** | 형상·구조가 바뀜 (CAD 스크립트 수정, 부품 추가·삭제) | `v2.9.3 → v2.10.0` |
| 메이저 | 설계를 갈아엎음 (v3) | `v2.x → v3.0.0` |

문서·펌웨어·CI만 바뀌면 버전을 올리지 않아도 된다 (실물에 영향 없음).

## 만든 실물에 버전 기록

**옛 버전으로 만든 부품을 나중에 추적하려고** 반드시 기록한다.

- **3D 프린트 부품**: Release의 STL zip 안 파일 이름에 버전이 들어 있다 (`H02_heater_duct_PETG_v2.9.0.stl`).
  슬라이서 파일 이름도 그대로 두고, 출력물 안쪽에 네임펜으로 `v2.9.0`
- **재단한 판** (포맥스, 폼, 알루미늄): **뒷면에 연필로 버전**과 바디 이름 (`P02 v2.9.0`)
- 새 버전 CHANGELOG의 **"이미 만든 부품 중 다시 만들어야 하는 것"** 칸을 보고, 해당 버전이 적힌 실물을 다시 만든다

## main 브랜치 보호 설정 (레포 관리자가 한 번)

Settings → Branches → **Add branch ruleset** (또는 Add rule) → Branch name pattern `main`

- [x] Require a pull request before merging
  - [x] Require review from Code Owners
- [x] Require status checks to pass → `cad-build`, `firmware-build` 추가
- [x] Block force pushes

개인 계정의 비공개 레포는 무료 플랜에서 브랜치 보호가 안 될 수 있다 (공개 레포는 됨).
