"""L3 门禁裁定：汇总 L0–L2，写入 qa/M1.json，并可选自校验。

输入（只读）：
    - 三件套（projects/02_modeling/ 固定名）：题目分析报告.md、术语表格.md、model-contract.json
    - qa/R1.json、qa/R2.json（run_review.py 产出，符合 review-findings.schema.json）
    - 可选 --problem：原始题目/附件目录（作为 problem_statement 输入快照）

输出：
    - qa/M1.json（符合 schemas/gate-receipt.schema.json）

裁定规则（确定性，无模型参与）：
    - 缺三件套或缺 R1/R2 → BLOCKED（缺证据）
    - L0 schema 校验失败 → FAIL
    - 任一 reviewer 有未解决 P0/P1 → consensus=fail → FAIL（P0/P1 均阻断）
    - 否则 → PASS

用法：
    python .agent/skills/modeling/scripts/generate_gate_receipt.py
    python .agent/skills/modeling/scripts/generate_gate_receipt.py --check   # 写完再自校验
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
WRITE_ROOT = REPO_ROOT / "projects" / "02_modeling"
SCHEMA_PATH = (
    REPO_ROOT / ".agent" / "skills" / "modeling" / "schemas" / "gate-receipt.schema.json"
)
DEFAULT_MODEL_CONTRACT_SCHEMA = (
    REPO_ROOT / ".." / "math_modeling" / "reference" / "schemas" / "model-contract.schema.json"
)
ARTIFACTS = [
    ("题目分析报告.md", "analysis_report"),
    ("术语表格.md", "terminology_table"),
    ("model-contract.json", "model_contract"),
]


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_text(path: Path) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_model_contract_schema() -> Path:
    cfg_path = REPO_ROOT / "tools_config.yaml"
    if cfg_path.exists():
        try:
            import yaml

            with open(cfg_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            ref = (cfg.get("references") or {}).get("model_contract_schema")
            if ref:
                p = Path(ref)
                if not p.is_absolute():
                    p = REPO_ROOT / p
                return p
        except Exception:
            pass
    return DEFAULT_MODEL_CONTRACT_SCHEMA


def run_l0() -> dict:
    """确定性 L0：model-contract.json 是否通过外部 schema 校验。"""
    import jsonschema

    contract_path = WRITE_ROOT / "model-contract.json"
    schema_path = resolve_model_contract_schema()
    if not contract_path.exists():
        return {"level": "L0", "tool": "validate_model_contract.py", "exit_code": 1, "result": "contract_missing"}
    if not schema_path.exists():
        return {"level": "L0", "tool": "validate_model_contract.py", "exit_code": 1, "result": "schema_missing"}
    contract = load_json(contract_path)
    schema = load_json(schema_path)
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(contract))
    if errors:
        return {
            "level": "L0",
            "tool": "validate_model_contract.py",
            "exit_code": 1,
            "result": f"{len(errors)} schema errors",
        }
    return {"level": "L0", "tool": "validate_model_contract.py", "exit_code": 0, "result": "pass"}


def build_inputs(problem_dir: Path | None) -> list:
    inputs = []
    for name, role in ARTIFACTS:
        p = WRITE_ROOT / name
        if not p.exists():
            continue
        inputs.append({"role": role, "path": str(p.relative_to(REPO_ROOT)), "sha256": sha256(p), "bytes": p.stat().st_size})
    if problem_dir and problem_dir.exists():
        # 取问题目录下文本文件作为 problem_statement 快照（仅首个主要文件）
        for p in sorted(problem_dir.rglob("*")):
            if p.is_file() and p.suffix.lower() in (".md", ".txt", ".pdf"):
                inputs.append(
                    {"role": "problem_statement", "path": str(p.relative_to(REPO_ROOT)), "sha256": sha256(p), "bytes": p.stat().st_size}
                )
                break
    return inputs


def has_blocker(findings: list) -> bool:
    return any(f.get("severity") in ("P0", "P1") for f in findings)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--problem", default=None, help="原始题目/附件目录（可选）")
    parser.add_argument("--check", action="store_true", help="写完后再跑 validate_gate_receipt.py 自校验")
    args = parser.parse_args()

    try:
        import jsonschema
    except ImportError:
        print("[错误] 缺少 jsonschema，请先安装：pip install jsonschema", file=sys.stderr)
        sys.exit(2)

    # L0
    l0 = run_l0()
    checks = [l0, {"level": "L1", "tool": "references/质检清单.md", "result": "author_self_check"}]

    # 输入快照
    inputs = build_inputs(Path(args.problem) if args.problem else None)
    missing_artifacts = [role for _, role in ARTIFACTS if role not in {i["role"] for i in inputs}]

    # L2：读 R1/R2
    reviewers = []
    merged_findings = []
    missing_reviews = []
    for rid in ("R1", "R2"):
        p = WRITE_ROOT / "qa" / f"{rid}.json"
        if not p.exists():
            missing_reviews.append(rid)
            continue
        r = load_json(p)
        reviewers.append(
            {
                "reviewer_id": r["reviewer_id"],
                "model": r["model"],
                "independence_attested": r["independence_attested"],
                "findings": r["findings"],
            }
        )
        for f in r["findings"]:
            merged_findings.append({**f, "id": f"{rid}.{f['id']}"})

    checks.append(
        {
            "level": "L2",
            "tool": "run_review.py",
            "exit_code": 0,
            "result": f"{len(reviewers)} reviewers, {len(merged_findings)} findings",
        }
    )

    consensus = "fail" if any(has_blocker(x["findings"]) for x in reviewers) else "pass"

    # rework_suggestions：收集 P0/P1 的 suggestion
    rework = []
    for f in merged_findings:
        if f["severity"] in ("P0", "P1"):
            rework.append(f"[{f['id']} {f['severity']}] {f['suggestion']}")
    if l0["exit_code"] != 0:
        rework.insert(0, f"[L0] {l0['result']} —— 请修正 model-contract.json 后重跑")

    # status 判定
    if missing_artifacts or missing_reviews:
        status = "BLOCKED"
        rework.insert(0, f"[BLOCKED] 缺输入：artifacts={missing_artifacts or '无'} reviews={missing_reviews or '无'}")
    elif l0["exit_code"] != 0 or consensus == "fail":
        status = "FAIL"
    else:
        status = "PASS"

    receipt = {
        "gate": "M1",
        "status": status,
        "inputs": inputs,
        "checks": checks,
        "independent_review": {"reviewers": reviewers, "consensus": consensus},
        "findings": merged_findings,
        "rework_suggestions": rework,
    }

    out_dir = WRITE_ROOT / "qa"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "M1.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2)

    print(
        f"[L3 裁定] {out_path.relative_to(REPO_ROOT)}"
        f" status={status} consensus={consensus} reviewers={len(reviewers)}"
        f" findings={len(merged_findings)} rework={len(rework)}"
    )

    if args.check:
        import subprocess

        validator = (
            REPO_ROOT / ".agent" / "skills" / "modeling" / "scripts" / "validate_gate_receipt.py"
        )
        result = subprocess.run(
            [sys.executable, str(validator), "--receipt", str(out_path.relative_to(REPO_ROOT))],
            cwd=str(REPO_ROOT),
        )
        sys.exit(result.returncode)

    sys.exit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()
