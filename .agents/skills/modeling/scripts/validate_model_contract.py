"""L0 确定性 Schema 校验：校验 model-contract.json 是否符合外部合同 schema。

用法：
    python .agents/skills/modeling/scripts/validate_model_contract.py \
        --contract projects/02_modeling/model-contract.json

依赖：jsonschema（已加入 environment.yml 的 pip 段）。

schema 路径解析优先级：
    1. --schema 参数
    2. tools_config.yaml 的 references.model_contract_schema
    3. 默认 ../math_modeling/reference/schemas/model-contract.schema.json（相对 REPO_ROOT）
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SCHEMA = (
    REPO_ROOT / ".." / "math_modeling" / "reference" / "schemas" / "model-contract.schema.json"
)


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_schema_path(args) -> Path:
    if args.schema:
        p = Path(args.schema)
    else:
        p = None
        cfg_path = REPO_ROOT / "tools_config.yaml"
        if cfg_path.exists():
            try:
                import yaml

                with open(cfg_path, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                ref = (cfg.get("references") or {}).get("model_contract_schema")
                if ref:
                    p = Path(ref)
            except Exception:
                p = None
        if p is None:
            p = DEFAULT_SCHEMA
    if not p.is_absolute():
        p = REPO_ROOT / p
    return p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, help="model-contract.json 路径（相对 REPO_ROOT 或绝对）")
    parser.add_argument("--schema", default=None, help="schema 路径（可选，默认读 tools_config 或外部默认）")
    args = parser.parse_args()

    try:
        import jsonschema
    except ImportError:
        print("[错误] 缺少 jsonschema，请先安装：pip install jsonschema", file=sys.stderr)
        sys.exit(2)

    contract_path = Path(args.contract)
    if not contract_path.is_absolute():
        contract_path = REPO_ROOT / contract_path
    schema_path = resolve_schema_path(args)

    if not contract_path.exists():
        print(f"[错误] 合同不存在：{contract_path}", file=sys.stderr)
        sys.exit(1)
    if not schema_path.exists():
        print(f"[错误] schema 不存在：{schema_path}", file=sys.stderr)
        sys.exit(1)

    contract = load_json(contract_path)
    schema = load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(contract), key=lambda e: list(e.path))

    if errors:
        print(f"[L0 FAIL] {contract_path} 有 {len(errors)} 个 schema 错误：")
        for i, e in enumerate(errors, 1):
            loc = "/".join(str(p) for p in e.path) or "(root)"
            print(f"  {i}. {loc}: {e.message}")
        sys.exit(1)

    print(f"[L0 PASS] {contract_path} 通过 schema 校验（{schema_path}）")
    sys.exit(0)


if __name__ == "__main__":
    main()
