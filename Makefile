# ============================================================
# 自动化入口
# ============================================================

.PHONY: env lock-env skills doctor release-check sync-lit build-paper clean

env:          # 创建 / 更新统一 conda 环境
	conda env create -f environment.yml || conda env update -n math_modeling -f environment.yml --prune

lock-env:     # 从直接依赖生成 win-64 精确锁
	conda run -n math_modeling python scripts/skillctl.py env lock --apply

skills:       # 列出项目级 Skills
	conda run -n math_modeling python scripts/skillctl.py list

doctor:       # 日常依赖与 Skill 漂移检查
	conda run -n math_modeling python scripts/skillctl.py doctor

release-check: # 正式比赛前严格检查
	conda run -n math_modeling python scripts/skillctl.py doctor --release

sync-lit:     # 从 Zotero 同步 bib 到论文目录
	python scripts/sync_zotero.py

build-paper:  # 本地编译 LaTeX
	cd projects/04_paper && xelatex -interaction=nonstopmode main.tex

clean:        # 清理中间产物
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
