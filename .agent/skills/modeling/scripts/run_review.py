"""DeepSeek API 独立评审执行器：对三件套做对抗性评审。

隔离机制：
    本脚本只调用 tools_config.yaml 中 access=api 的 DeepSeek reviewer，
    与作者会话异源；脚本只读三件套，不携带作者思考过程/自检结果。
    ChatGPT Pro 评审由参赛队员在网页端独立发起，不由本脚本调用。

用法：
    python .agent/skills/modeling/scripts/run_review.py
    python .agent/skills/modeling/scripts/run_review.py --problem competition/problem

输出：
    projects/02_modeling/qa/R1.json，符合 schemas/review-findings.schema.json。

依赖：requests、python-dotenv、jsonschema、pyyaml（均在 environment.yml）。
API Key 从 .env 读（gitignored），不硬编码、不打印。
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
WRITE_ROOT = REPO_ROOT / "projects" / "02_modeling"
SCHEMA_PATH = (
    REPO_ROOT / ".agent" / "skills" / "modeling" / "schemas" / "review-findings.schema.json"
)
STANDARDS_PATH = (
    REPO_ROOT / ".agent" / "skills" / "modeling" / "references" / "评审标准.md"
)
ARTIFACTS = [
    ("题目分析报告.md", "analysis_report"),
    ("术语表格.md", "terminology_table"),
    ("model-contract.json", "model_contract"),
]
REVIEW_CONTEXT = [
    (REPO_ROOT / "AGENTS.md", "authoring_rules"),
    (REPO_ROOT / "reference" / "literature" / "zotero_library.bib", "citation_source"),
]


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_text(path: Path) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_yaml_cfg() -> dict:
    import yaml

    with open(REPO_ROOT / "tools_config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def read_problem_extra(problem_dir: Path) -> str:
    """递归读取题目/附件文本，拼入评审输入。"""
    chunks = []
    if problem_dir and problem_dir.exists():
        for p in sorted(problem_dir.rglob("*")):
            if not p.is_file():
                continue
            if p.suffix.lower() not in (".md", ".txt", ".json", ".csv"):
                continue
            try:
                chunks.append(f"\n===== 文件：{p.relative_to(problem_dir)} =====\n{load_text(p)}")
            except UnicodeDecodeError:
                chunks.append(f"\n===== 文件：{p.relative_to(problem_dir)} =====\n[binary/编码不支持，跳过]")
    return "\n".join(chunks)


def build_bundle(problem_dir: Path) -> str:
    parts = []
    for path, role in REVIEW_CONTEXT:
        if not path.exists():
            print(f"[错误] 评审上下文缺失：{path}", file=sys.stderr)
            sys.exit(1)
        parts.append(f"\n===== [{role}] {path.relative_to(REPO_ROOT)} =====\n{load_text(path)}")
    for name, role in ARTIFACTS:
        p = WRITE_ROOT / name
        if not p.exists():
            print(f"[错误] 三件套缺失：{p}", file=sys.stderr)
            sys.exit(1)
        parts.append(f"\n===== [{role}] {name} =====\n{load_text(p)}")
    extra = read_problem_extra(problem_dir)
    if extra:
        parts.append(f"\n===== 原始题目/附件（只读） =====\n{extra}")
    return "\n".join(parts)


def extract_json(text: str):
    """先整体解析，失败则截取首尾大括号重试。"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


def call_reviewer(cfg: dict, standards: str, bundle: str) -> list:
    import requests

    api_key = os.environ.get(cfg["api_key_env"])
    if not api_key:
        print(
            f"[错误] 环境变量 {cfg['api_key_env']} 未设置（请在 .env 中配置）",
            file=sys.stderr,
        )
        sys.exit(2)

    url = cfg["base_url"].rstrip("/") + "/chat/completions"
    system = (
        standards
        + "\n\n你是对抗性独立评审者。只根据下方材料给出 findings，"
        "不要复述、不要客套。\n"
        "严格返回一个 JSON 对象，形如：\n"
        '{"findings": [{"id":"F1","severity":"P0","claim":"...","evidence":"...","suggestion":"..."}]}\n'
        "severity 只能取 P0/P1/P2；无问题则 findings 为空数组。"
    )
    payload = {
        "model": cfg["model"],
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": bundle},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    resp = requests.post(url, json=payload, headers=headers, timeout=180)
    if resp.status_code != 200:
        print(
            f"[错误] {cfg['provider']} API 返回 {resp.status_code}: {resp.text[:400]}",
            file=sys.stderr,
        )
        sys.exit(2)

    content = resp.json()["choices"][0]["message"]["content"]
    data = extract_json(content)
    if isinstance(data, list):
        return data
    findings = data.get("findings", [])
    if not isinstance(findings, list):
        print(f"[错误] 评审输出无有效 findings 数组：{content[:400]}", file=sys.stderr)
        sys.exit(2)
    return findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewer", action="append", default=None, help="只跑指定 reviewer（可多次）")
    parser.add_argument(
        "--problem",
        default=str(REPO_ROOT / "competition"),
        help="原始题目/附件目录（默认 competition，只读）",
    )
    args = parser.parse_args()

    try:
        import jsonschema
    except ImportError:
        print("[错误] 缺少 jsonschema，请先安装：pip install jsonschema", file=sys.stderr)
        sys.exit(2)

    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")

    cfg = load_yaml_cfg()
    reviewers_cfg = (cfg.get("review") or {}).get("reviewers") or {}
    if not reviewers_cfg:
        print("[错误] tools_config.yaml 的 review.reviewers 未配置", file=sys.stderr)
        sys.exit(2)

    api_reviewers = {
        rid: reviewer
        for rid, reviewer in reviewers_cfg.items()
        if reviewer.get("access") == "api"
    }
    if not api_reviewers:
        print("[错误] 未配置 access=api 的 DeepSeek reviewer", file=sys.stderr)
        sys.exit(2)

    selected = args.reviewer or list(api_reviewers.keys())
    standards = load_text(STANDARDS_PATH)
    bundle = build_bundle(Path(args.problem) if args.problem else None)

    schema = load_json(SCHEMA_PATH)
    validator = jsonschema.Draft202012Validator(schema)

    out_dir = WRITE_ROOT / "qa"
    out_dir.mkdir(parents=True, exist_ok=True)

    for rid in selected:
        if rid not in api_reviewers:
            print(f"[错误] 未找到 API reviewer：{rid}", file=sys.stderr)
            sys.exit(2)
        r = api_reviewers[rid]
        if r.get("provider") != "deepseek":
            print(f"[错误] API reviewer {rid} 不是 DeepSeek", file=sys.stderr)
            sys.exit(2)
        print(f"[评审中] {rid} via {r['provider']}/{r['model']} …")
        findings = call_reviewer(r, standards, bundle)
        obj = {
            "reviewer_id": rid,
            "model": r["model"],
            "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
            "independence_attested": True,
            "findings": findings,
        }
        # 校验后写入
        errors = sorted(validator.iter_errors(obj), key=lambda e: list(e.path))
        if errors:
            print(f"[错误] {rid} 输出不符合 schema：", file=sys.stderr)
            for e in errors:
                loc = "/".join(str(p) for p in e.path) or "(root)"
                print(f"  {loc}: {e.message}", file=sys.stderr)
            sys.exit(2)
        out_path = out_dir / f"{rid}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        n_p0 = sum(1 for x in findings if x.get("severity") == "P0")
        n_p1 = sum(1 for x in findings if x.get("severity") == "P1")
        print(f"[完成] {rid} → {out_path}（P0×{n_p0} P1×{n_p1} 共 {len(findings)} 条）")

    print("DeepSeek API 评审完成。请另行在 ChatGPT Pro 网页端完成只读评审。")
    sys.exit(0)


if __name__ == "__main__":
    main()
