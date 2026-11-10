# herb-dryer 빌드. 실제 작업은 build.py 가 한다 (Windows 등 make 없는 곳은 python build.py).
PY ?= python3

.PHONY: all step check drawings stl render csv bom compare clean help

all:            ## 전부 생성 (STEP → 간섭 → 도면 → STL → 렌더 → CSV → BOM CSV)
	$(PY) build.py all

step check drawings stl render csv bom:
	$(PY) build.py $@

compare:        ## 리팩터링 검증: make compare BASE=옛.step
	$(PY) cad/tools/compare_step.py $(BASE) build/herb_dryer.step

clean:
	rm -rf build

help:
	@$(PY) build.py --help
