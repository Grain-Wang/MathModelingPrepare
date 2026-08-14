"""L3 门禁回执校验：校验 qa/M1.json 符合 gate-receipt schema，输入哈希一致，状态自洽。

用法：
    python .agent/skills/modeling/scripts/validate_gate_receipt.py \
        --receipt projects/02_modeling/qa/M1.json

校验项：
    1. 回执符合 schemas/gate-receipt.schema.json。
    2. 每个 input 的 sha256 与磁盘实际文件一致（输入快照未被篡改）。
    3. status 语义：PASS 必须无未解决 P0/P1，且双 reviewer 齐备。

依赖：jsonschema。
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = (
    REPO_ROOT / ".agent" / "skills" / "modeling" / "schemas" / "gate-receipt.schema.json"
)


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", required=True, help="M1.json 回执路径（相对 REPO_ROOT 或绝对）")
    args = parser.parse_args()

    try:
        import jsonschema
    except ImportError:
        print("[错误] 缺少 jsonschema，请先安装：pip install jsonschema", file=sys.stderr)
        sys.exit(2)

    receipt_path = Path(args.receipt)
    if not receipt_path.is_absolute():
        receipt_path = REPO_ROOT / receipt_path
    if not receipt_path.exists():
        print(f"[错误] 回执不存在：{receipt_path}", file=sys.stderr)
        sys.exit(1)
    if not SCHEMA_PATH.exists():
        print(f"[错误] 回执 schema 不存在：{SCHEMA_PATH}", file=sys.stderr)
        sys.exit(1)

    receipt = load_json(receipt_path)
    schema = load_json(SCHEMA_PATH)
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(receipt), key=lambda e: list(e.path))
    if errors:
        print(f"[L3 FAIL] 回执 schema 错误 {len(errors)} 个：")
        for i, e in enumerate(errors, 1):
            loc = "/".join(str(p) for p in e.path) or "(root)"
            print(f"  {i}. {loc}: {e.message}")
        sys.exit(1)

    # 输入快照哈希一致性
    for inp in receipt["inputs"]:
        p = REPO_ROOT / inp["path"]
        if not p.exists():
            print(f"[L3 FAIL] 输入文件不存在：{inp['path']}", file=sys.stderr)
            sys.exit(1)
        actual = sha256(p)
        if actual != inp["sha256"]:
            print(
                f"[L3 FAIL] 哈希不一致：{inp['path']}"
                f"（记录 {inp['sha256'][:12]}… != 实际 {actual[:12]}…）",
                file=sys.stderr,
            )
            sys.exit(1)

    # status 语义自洽
    findings = receipt.get("findings", [])
    blockers = [f for f in findings if f.get("severity") in ("P0", "P1")]
    reviewers = receipt.get("independent_review", {}).get("reviewers", [])
    if receipt["status"] == "PASS":
        if blockers:
            print("[L3 FAIL] status=PASS 但存在未解决 P0/P1", file=sys.stderr)
            sys.exit(1)
        if len(reviewers) < 2:
            print("[L3 FAIL] status=PASS 但双 reviewer 未齐", file=sys.stderr)
            sys.exit(1)

    print(
        f"[L3 PASS] 回执可信：gate={receipt['gate']} status={receipt['status']} "
        f"哈希一致 reviewer={len(reviewers)} findings={len(findings)}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
