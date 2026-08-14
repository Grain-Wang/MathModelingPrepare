# ============================================================
# 自动化入口
# ============================================================

.PHONY: env sync-lit build-paper clean

env:          # 创建 / 更新 conda 环境
	conda env create -f environment.yml || conda env update -f environment.yml --prune

sync-lit:     # 从 Zotero 同步 bib 到论文目录
	python scripts/sync_zotero.py

build-paper:  # 本地编译 LaTeX
	cd projects/04_paper && xelatex -interaction=nonstopmode main.tex

clean:        # 清理中间产物
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
