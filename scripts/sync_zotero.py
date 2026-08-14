"""从 Zotero 导出的 bib 同步到论文目录。

用法：python scripts/sync_zotero.py
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def main():
    with open(ROOT / "tools_config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    src = ROOT / cfg["bib"]["zotero_export"]
    dst = ROOT / "projects/04_paper/bibliography.bib"

    if not src.exists():
        print(f"[跳过] 未找到 {src}，请先从 Zotero 导出。")
        return

    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[完成] {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
