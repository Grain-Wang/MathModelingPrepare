"""BibTeX 完整性校验：检查必要字段、重复条目，生成 citation_checklist.md。

用法：python .agents/scripts/run_citation_check.py
"""
from pathlib import Path

import bibtexparser
import yaml

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = {"author", "title", "year"}


def main():
    with open(ROOT / "tools_config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    bib_path = ROOT / cfg["bib"]["zotero_export"]

    if not bib_path.exists():
        print(f"[跳过] 未找到 {bib_path}，请先从 Zotero 导出。")
        return

    with open(bib_path, encoding="utf-8") as f:
        lib = bibtexparser.load(f)

    seen = {}
    lines = ["# 引用校验清单\n\n", "| cite key | 必要字段 | 状态 |\n", "|---|---|---|\n"]
    for e in lib.entries:
        key = e.get("ID", "?")
        missing = REQUIRED - set(e.keys())
        status = "✅" if not missing else f"⚠️ 缺 {', '.join(sorted(missing))}"
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            status += " ❌ 重复"
        lines.append(f"| {key} | {', '.join(REQUIRED)} | {status} |\n")

    out = ROOT / "reference/literature/citation_checklist.md"
    out.write_text("".join(lines), encoding="utf-8")
    print(f"[完成] 已写入 {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
