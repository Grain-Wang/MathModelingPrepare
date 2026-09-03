"""批量文献结构化提取：遍历 zotero_library.bib，逐条调用 AI 提取四要素。

用法：python .agents/scripts/run_literature_extract.py [citekey ...]
"""
import sys
from pathlib import Path

import bibtexparser
import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_config():
    with open(ROOT / "tools_config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main(citekeys):
    cfg = load_config()
    bib_path = ROOT / cfg["bib"]["zotero_export"]
    if not bib_path.exists():
        print(f"[跳过] 未找到 {bib_path}，请先从 Zotero 导出。")
        return

    with open(bib_path, encoding="utf-8") as f:
        lib = bibtexparser.load(f)

    targets = (
        lib.entries
        if not citekeys
        else [e for e in lib.entries if e.get("ID") in citekeys]
    )
    # TODO: 在此调用已配置的 AI 对每个 entry 执行 literature-extract Skill
    for e in targets:
        print(f"[提取] {e.get('ID')} -> reading_notes/{e.get('ID')}.md")


if __name__ == "__main__":
    main(sys.argv[1:])
