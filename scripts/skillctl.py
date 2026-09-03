#!/usr/bin/env python3
"""Project-local Skill registry and dependency lifecycle manager.

All mutating commands are dry-runs unless ``--apply`` is supplied. Commands are
executed as argument arrays with ``shell=False``; secret values and .env files
are deliberately outside this tool's data model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / ".agents" / "skill-registry.yaml"
SCHEMA_PATH = REPO_ROOT / ".agents" / "schemas" / "skill-registry.schema.json"
IGNORED_TREE_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
IGNORED_TREE_SUFFIXES = {".pyc", ".pyo"}
BOOTSTRAP_ENV = "_math_modeling_lock_bootstrap"


class SkillCtlError(RuntimeError):
    """Expected command failure with a user-facing message."""


def yaml_module():
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - environment bootstrap path
        raise SkillCtlError("缺少 PyYAML；请先在 math_modeling 环境安装 pyyaml。") from exc
    return yaml


def load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.is_file():
        raise SkillCtlError(f"注册表不存在：{REGISTRY_PATH.relative_to(REPO_ROOT)}")
    data = yaml_module().safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    # Break YAML alias identity so editing one entry never mutates another one.
    return json.loads(json.dumps(data, ensure_ascii=False))


def save_registry(registry: dict[str, Any]) -> None:
    text = yaml_module().safe_dump(
        registry, allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    atomic_write_text(REGISTRY_PATH, text)


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(content, encoding="utf-8", newline="\n")
    temp_path.replace(path)


def validate_registry_schema(registry: dict[str, Any]) -> None:
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - environment bootstrap path
        raise SkillCtlError("缺少 jsonschema；请先在 math_modeling 环境安装。") from exc
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    errors = sorted(validator.iter_errors(registry), key=lambda item: list(item.path))
    if errors:
        lines = []
        for error in errors:
            where = "/".join(str(part) for part in error.path) or "(root)"
            lines.append(f"{where}: {error.message}")
        raise SkillCtlError("注册表不符合 Schema：\n  " + "\n  ".join(lines))


def find_skill(registry: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [item for item in registry["skills"] if item["name"] == name]
    if not matches:
        raise SkillCtlError(f"Skill 未登记：{name}")
    if len(matches) > 1:
        raise SkillCtlError(f"注册表存在重复 Skill 名称：{name}")
    return matches[0]


def safe_repo_path(relative: str, *, allow_missing: bool = True) -> Path:
    posix = PurePosixPath(relative.replace("\\", "/"))
    if posix.is_absolute() or ".." in posix.parts or not posix.parts:
        raise SkillCtlError(f"拒绝不安全的仓库路径：{relative}")
    if any(part.lower() == ".env" for part in posix.parts):
        raise SkillCtlError("维护工具不访问 .env。")
    if posix.parts[0].lower() == "competition":
        raise SkillCtlError("competition/ 是只读目录，维护工具拒绝写入。")
    candidate = REPO_ROOT.joinpath(*posix.parts)
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise SkillCtlError(f"路径逃逸仓库：{relative}") from exc
    probe = REPO_ROOT
    for part in posix.parts:
        probe = probe / part
        if probe.exists() and probe.is_symlink():
            raise SkillCtlError(f"拒绝符号链接路径：{relative}")
    if not allow_missing and not candidate.exists():
        raise SkillCtlError(f"路径不存在：{relative}")
    return candidate


def ensure_no_symlinks(root: Path) -> None:
    if root.is_symlink():
        raise SkillCtlError(f"Skill 根目录不能是符号链接：{root}")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SkillCtlError(f"Skill 中不允许符号链接：{path}")


def parse_skill_frontmatter(skill_dir: Path) -> dict[str, Any]:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        raise SkillCtlError(f"缺少 SKILL.md：{skill_dir}")
    text = skill_file.read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|\Z)", text, re.DOTALL)
    if not match:
        raise SkillCtlError(f"SKILL.md 缺少合法 YAML frontmatter：{skill_file}")
    metadata = yaml_module().safe_load(match.group(1)) or {}
    if not isinstance(metadata, dict):
        raise SkillCtlError(f"SKILL.md frontmatter 必须是对象：{skill_file}")
    name = metadata.get("name")
    description = metadata.get("description")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise SkillCtlError(f"Skill name 非法：{name!r}")
    if not isinstance(description, str) or not description.strip():
        raise SkillCtlError("Skill description 不能为空。")
    return metadata


def tree_hash(skill_dir: Path) -> str:
    if not skill_dir.is_dir():
        raise SkillCtlError(f"Skill 目录不存在：{skill_dir}")
    ensure_no_symlinks(skill_dir)
    digest = hashlib.sha256()
    files = []
    for path in skill_dir.rglob("*"):
        relative = path.relative_to(skill_dir)
        if path.is_dir():
            continue
        if any(part in IGNORED_TREE_PARTS for part in relative.parts):
            continue
        if path.suffix.lower() in IGNORED_TREE_SUFFIXES:
            continue
        files.append(path)
    for path in sorted(files, key=lambda item: item.relative_to(skill_dir).as_posix()):
        relative_bytes = path.relative_to(skill_dir).as_posix().encode("utf-8")
        digest.update(len(relative_bytes).to_bytes(8, "big"))
        digest.update(relative_bytes)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def command_text(command: Sequence[str]) -> str:
    return subprocess.list2cmdline([str(part) for part in command])


def run_command(
    command: Sequence[str],
    *,
    apply: bool,
    cwd: Path = REPO_ROOT,
    capture: bool = False,
) -> subprocess.CompletedProcess[str] | None:
    print(("[执行] " if apply else "[预览] ") + command_text(command))
    if not apply:
        return None
    try:
        return subprocess.run(
            [str(part) for part in command],
            cwd=cwd,
            check=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=capture,
            shell=False,
        )
    except FileNotFoundError as exc:
        raise SkillCtlError(f"找不到可执行程序：{command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        suffix = f"\n{detail}" if detail else ""
        raise SkillCtlError(f"命令失败（{exc.returncode}）：{command_text(command)}{suffix}") from exc


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def expected_skill_prefix(status: str) -> str:
    return ".agents/candidates/" if status == "candidate" else ".agents/skills/"


def check_skill_entry(skill: dict[str, Any], *, check_hash: bool = True) -> list[str]:
    errors: list[str] = []
    path_text = skill["path"]
    if not path_text.startswith(expected_skill_prefix(skill["status"])):
        errors.append(f"{skill['name']}: status 与 path 不一致")
    try:
        skill_dir = safe_repo_path(path_text, allow_missing=False)
        if not skill_dir.is_dir():
            errors.append(f"{skill['name']}: path 不是目录")
            return errors
        metadata = parse_skill_frontmatter(skill_dir)
        if metadata["name"] != skill["name"]:
            errors.append(
                f"{skill['name']}: frontmatter name 为 {metadata['name']}"
            )
        if check_hash:
            actual = tree_hash(skill_dir)
            if actual != skill["content_sha256"]:
                errors.append(
                    f"{skill['name']}: 内容哈希漂移（登记 {skill['content_sha256'][:12]}，实际 {actual[:12]}）"
                )
    except SkillCtlError as exc:
        errors.append(f"{skill['name']}: {exc}")
    return errors


def cmd_list(args: argparse.Namespace) -> int:
    registry = load_registry()
    validate_registry_schema(registry)
    skills = registry["skills"]
    if args.status:
        skills = [item for item in skills if item["status"] == args.status]
    for skill in sorted(skills, key=lambda item: item["name"]):
        print(f"{skill['name']:<24} {skill['status']:<9} {skill['description']}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    registry = load_registry()
    validate_registry_schema(registry)
    query = args.query.casefold()
    matches = []
    for skill in registry["skills"]:
        haystack = " ".join(
            [skill["name"], skill["description"], *skill.get("tags", [])]
        ).casefold()
        if query in haystack:
            matches.append(skill)
    for skill in sorted(matches, key=lambda item: item["name"]):
        print(f"{skill['name']:<24} {skill['status']:<9} {skill['description']}")
    return 0 if matches else 1


def cmd_show(args: argparse.Namespace) -> int:
    registry = load_registry()
    validate_registry_schema(registry)
    skill = find_skill(registry, args.name)
    print(yaml_module().safe_dump(skill, allow_unicode=True, sort_keys=False), end="")
    return 0


def resolve_stage_source(args: argparse.Namespace, temp_root: Path) -> tuple[Path, str, str]:
    local_source = Path(args.source).expanduser()
    if local_source.exists():
        root = local_source.resolve()
        source_type = args.source_type or "local"
    else:
        if not args.ref:
            raise SkillCtlError("远程来源必须用 --ref 固定 commit 或 tag。")
        if args.ref.startswith("-"):
            raise SkillCtlError("--ref 不能以连字符开头。")
        checkout = temp_root / "checkout"
        run_command(["git", "clone", "--quiet", "--", args.source, str(checkout)], apply=True)
        run_command(
            ["git", "-C", str(checkout), "checkout", "--quiet", "--detach", args.ref],
            apply=True,
        )
        result = run_command(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], apply=True, capture=True
        )
        assert result is not None
        revision = result.stdout.strip()
        root = checkout
        source_type = args.source_type or "third-party"
    if args.subdir:
        subdir = PurePosixPath(args.subdir.replace("\\", "/"))
        if subdir.is_absolute() or ".." in subdir.parts:
            raise SkillCtlError("--subdir 不能是绝对路径或包含 ..。")
        root = root.joinpath(*subdir.parts)
    if not root.is_dir():
        raise SkillCtlError(f"Skill 来源目录不存在：{root}")
    ensure_no_symlinks(root)
    if local_source.exists():
        revision = args.ref or f"sha256:{tree_hash(root)}"
    return root, revision, source_type


def cmd_stage(args: argparse.Namespace) -> int:
    registry = load_registry()
    validate_registry_schema(registry)
    with tempfile.TemporaryDirectory(prefix="skillctl-stage-") as temp:
        source_dir, revision, source_type = resolve_stage_source(args, Path(temp))
        metadata = parse_skill_frontmatter(source_dir)
        name = args.name or metadata["name"]
        if name != metadata["name"]:
            raise SkillCtlError("--name 必须与 SKILL.md frontmatter name 一致。")
        if any(item["name"] == name for item in registry["skills"]):
            raise SkillCtlError(f"Skill 已登记：{name}")
        destination_rel = f".agents/candidates/{name}"
        destination = safe_repo_path(destination_rel)
        if destination.exists():
            raise SkillCtlError(f"候选目录已存在：{destination_rel}")
        entry = {
            "name": name,
            "description": metadata["description"].strip(),
            "tags": sorted(set(args.tag or [])),
            "status": "candidate",
            "path": destination_rel,
            "source": {
                "type": source_type,
                "location": args.source,
                "revision": revision,
                "license": args.license,
            },
            "content_sha256": tree_hash(source_dir),
            "dependencies": {
                "conda": sorted(set(args.conda or [])),
                "pip": sorted(set(args.pip or [])),
                "external": [],
                "mcp": [],
            },
            "validation": {
                "commands": [],
                "evidence": [],
                "last_result": None,
                "last_validated_at": None,
                "accepted_by": None,
                "accepted_at": None,
            },
        }
        print(f"[预览] 暂存 {name} -> {destination_rel} ({entry['content_sha256'][:12]})")
        if not args.apply:
            return 0
        shutil.copytree(source_dir, destination, symlinks=False)
        registry["skills"].append(entry)
        registry["skills"].sort(key=lambda item: item["name"])
        validate_registry_schema(registry)
        save_registry(registry)
        print(f"[完成] 已暂存候选 Skill：{name}")
    return 0


def dependency_commands(skill: dict[str, Any], env_name: str) -> list[list[str]]:
    deps = skill["dependencies"]
    commands: list[list[str]] = []
    for spec in [*deps["conda"], *deps["pip"]]:
        if spec.lstrip().startswith("-"):
            raise SkillCtlError(f"依赖规格不能以选项开头：{spec!r}")
    if deps["conda"]:
        commands.append(
            ["conda", "install", "-n", env_name, "-c", "conda-forge", "-y", *deps["conda"]]
        )
    if deps["pip"]:
        commands.append(
            ["conda", "run", "-n", env_name, "python", "-m", "pip", "install", *deps["pip"]]
        )
    for dep in deps["external"]:
        if dep["package"].lstrip().startswith("-"):
            raise SkillCtlError(f"外部包标识不能以选项开头：{dep['package']!r}")
        if dep["manager"] == "npm":
            commands.append(["npm", "install", "--global", dep["package"]])
        elif dep["manager"] == "winget":
            commands.append(
                [
                    "winget", "install", "--id", dep["package"], "--exact",
                    "--accept-package-agreements", "--accept-source-agreements",
                ]
            )
    for mcp in deps["mcp"]:
        install = mcp.get("install")
        if install:
            manager = install["manager"]
            package = install["package"]
            if manager == "pip":
                commands.append(
                    ["conda", "run", "-n", env_name, "python", "-m", "pip", "install", package]
                )
            elif manager == "npm":
                commands.append(["npm", "install", "--global", package])
            elif manager == "winget":
                commands.append(
                    ["winget", "install", "--id", package, "--exact",
                     "--accept-package-agreements", "--accept-source-agreements"]
                )
        missing = [name for name in mcp["env_vars"] if name not in os.environ]
        if mcp.get("bearer_token_env_var") and mcp["bearer_token_env_var"] not in os.environ:
            missing.append(mcp["bearer_token_env_var"])
        if missing:
            raise SkillCtlError(
                f"MCP {mcp['name']} 缺少环境变量：{', '.join(sorted(set(missing)))}"
            )
        if mcp["transport"] == "stdio":
            commands.append(
                ["codex", "mcp", "add", mcp["name"], "--", mcp["command"], *mcp["args"]]
            )
        else:
            command = ["codex", "mcp", "add", mcp["name"], "--url", mcp["url"]]
            if mcp.get("bearer_token_env_var"):
                command.extend(["--bearer-token-env-var", mcp["bearer_token_env_var"]])
            commands.append(command)
    return commands


def cmd_deps_install(args: argparse.Namespace) -> int:
    registry = load_registry()
    validate_registry_schema(registry)
    skill = find_skill(registry, args.name)
    commands = dependency_commands(skill, registry["environment"]["name"])
    if not commands:
        print(f"{args.name} 没有待安装依赖。")
        return 0
    for command in commands:
        run_command(command, apply=args.apply)
    return 0


def validate_evidence(paths: Iterable[str]) -> list[str]:
    checked: list[str] = []
    for path_text in paths:
        path = safe_repo_path(path_text, allow_missing=False)
        if not path.is_file():
            raise SkillCtlError(f"验证证据必须是文件：{path_text}")
        checked.append(path.relative_to(REPO_ROOT).as_posix())
    return sorted(set(checked))


def cmd_validate(args: argparse.Namespace) -> int:
    registry = load_registry()
    validate_registry_schema(registry)
    skill = find_skill(registry, args.name)
    errors = check_skill_entry(skill)
    if errors:
        if args.apply:
            skill["validation"]["last_result"] = "fail"
            skill["validation"]["last_validated_at"] = now_iso()
            save_registry(registry)
        raise SkillCtlError("\n".join(errors))
    for command in skill["validation"]["commands"]:
        try:
            run_command(command, apply=True)
        except SkillCtlError:
            if args.apply:
                skill["validation"]["last_result"] = "fail"
                skill["validation"]["last_validated_at"] = now_iso()
                save_registry(registry)
            raise
    evidence = validate_evidence(args.evidence or skill["validation"]["evidence"])
    print(f"[通过] {args.name} 的结构与验证命令均通过。")
    if args.apply:
        skill["validation"]["last_result"] = "pass"
        skill["validation"]["last_validated_at"] = now_iso()
        skill["validation"]["evidence"] = evidence
        save_registry(registry)
    else:
        print("[预览] 未写回验证结果；需要时增加 --apply。")
    return 0


def package_name(spec: str) -> str:
    value = spec.split("::")[-1].strip()
    value = value.split("[", 1)[0]
    return re.split(r"\s|[<>=!~]", value, maxsplit=1)[0].lower().replace("_", "-")


def merge_specs(groups: Iterable[Iterable[str]]) -> list[str]:
    result: list[str] = []
    by_name: dict[str, str] = {}
    for group in groups:
        for spec in group:
            name = package_name(spec)
            prior = by_name.get(name)
            if prior and prior != spec:
                raise SkillCtlError(f"依赖规格冲突：{prior!r} 与 {spec!r}")
            if not prior:
                by_name[name] = spec
                result.append(spec)
    return result


def canonical_dependencies(registry: dict[str, Any]) -> tuple[list[str], list[str]]:
    accepted = [item for item in registry["skills"] if item["status"] == "accepted"]
    core = registry["environment"]["core_dependencies"]
    conda = merge_specs([core["conda"], *(item["dependencies"]["conda"] for item in accepted)])
    pip = merge_specs([core["pip"], *(item["dependencies"]["pip"] for item in accepted)])
    return conda, pip


def render_environment(registry: dict[str, Any]) -> str:
    conda_deps, pip_deps = canonical_dependencies(registry)
    dependencies: list[Any] = list(conda_deps)
    if pip_deps:
        dependencies.append({"pip": pip_deps})
    data = {
        "name": registry["environment"]["name"],
        "channels": ["conda-forge", "defaults"],
        "dependencies": dependencies,
    }
    return yaml_module().safe_dump(data, allow_unicode=True, sort_keys=False)


def lock_command(registry: dict[str, Any]) -> list[str]:
    env = registry["environment"]
    return [
        "conda", "run", "-n", env["name"], "conda-lock", "lock",
        "--file", env["manifest"], "--platform", env["platform"],
        "--lockfile", env["lockfile"],
    ]


def cmd_env_lock(args: argparse.Namespace) -> int:
    registry = load_registry()
    validate_registry_schema(registry)
    manifest = safe_repo_path(registry["environment"]["manifest"])
    rendered = render_environment(registry)
    if manifest.exists() and manifest.read_text(encoding="utf-8") != rendered:
        print("[提示] environment.yml 将同步为注册表中的已接纳依赖。")
        if args.apply:
            atomic_write_text(manifest, rendered)
    run_command(lock_command(registry), apply=args.apply)
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    registry = load_registry()
    validate_registry_schema(registry)
    skill = find_skill(registry, args.name)
    if skill["status"] != "candidate":
        raise SkillCtlError(f"只能接纳 candidate；当前状态为 {skill['status']}。")
    validation = skill["validation"]
    if validation["last_result"] != "pass" or not validation["evidence"]:
        raise SkillCtlError("接纳前必须验证通过，并登记至少一个证据文件。")
    errors = check_skill_entry(skill)
    if errors:
        raise SkillCtlError("\n".join(errors))
    source = safe_repo_path(skill["path"], allow_missing=False)
    destination_rel = f".agents/skills/{skill['name']}"
    destination = safe_repo_path(destination_rel)
    if destination.exists():
        raise SkillCtlError(f"接纳目标已存在：{destination_rel}")
    print(f"[预览] 接纳 {skill['name']}：{skill['path']} -> {destination_rel}")
    if not args.apply:
        print("[预览] 将同步 environment.yml 并重新生成 win-64 锁。")
        return 0

    registry_before = REGISTRY_PATH.read_text(encoding="utf-8")
    manifest = safe_repo_path(registry["environment"]["manifest"])
    manifest_before = manifest.read_text(encoding="utf-8") if manifest.exists() else None
    lockfile = safe_repo_path(registry["environment"]["lockfile"])
    lock_before = lockfile.read_bytes() if lockfile.exists() else None
    moved = False
    try:
        shutil.move(str(source), str(destination))
        moved = True
        skill["status"] = "accepted"
        skill["path"] = destination_rel
        skill["content_sha256"] = tree_hash(destination)
        skill["validation"]["accepted_by"] = args.accepted_by
        skill["validation"]["accepted_at"] = now_iso()
        validate_registry_schema(registry)
        save_registry(registry)
        atomic_write_text(manifest, render_environment(registry))
        run_command(lock_command(registry), apply=True)
    except Exception:
        atomic_write_text(REGISTRY_PATH, registry_before)
        if manifest_before is None:
            if manifest.exists():
                manifest.unlink()
        else:
            atomic_write_text(manifest, manifest_before)
        if lock_before is None:
            if lockfile.exists():
                lockfile.unlink()
        else:
            lockfile.write_bytes(lock_before)
        if moved and destination.exists() and not source.exists():
            shutil.move(str(destination), str(source))
        raise
    print(f"[完成] 已接纳 {skill['name']}，并更新环境锁。")
    return 0


def installed_packages(env_name: str) -> dict[str, str]:
    result = run_command(
        ["conda", "list", "-n", env_name, "--json"], apply=True, capture=True
    )
    assert result is not None
    data = json.loads(result.stdout)
    return {
        item["name"].lower().replace("_", "-"): str(item["version"])
        for item in data
    }


def requirement_satisfied(spec: str, installed: dict[str, str], *, pip: bool) -> tuple[bool, str]:
    name = package_name(spec)
    version = installed.get(name)
    if version is None:
        return False, f"缺少 {name}"
    exact = re.search(r"==\s*([^\s;]+)", spec) if pip else re.search(r"(?<![<>=!~])=\s*([^=,\s]+)", spec)
    if exact:
        wanted = exact.group(1).rstrip(".*")
        if pip and version != wanted:
            return False, f"{name}={version}，要求 {wanted}"
        if not pip and not (version == wanted or version.startswith(wanted + ".")):
            return False, f"{name}={version}，要求 {wanted}"
    return True, ""


def read_lock_packages(lockfile: Path, platform: str) -> dict[str, str]:
    if not lockfile.is_file():
        raise SkillCtlError(f"锁文件不存在：{lockfile.relative_to(REPO_ROOT)}")
    data = yaml_module().safe_load(lockfile.read_text(encoding="utf-8")) or {}
    packages = data.get("package")
    if not isinstance(packages, list):
        raise SkillCtlError("锁文件不是 conda-lock 统一锁格式（缺少 package 列表）。")
    result: dict[str, str] = {}
    for package in packages:
        if package.get("platform") != platform:
            continue
        name = str(package.get("name", "")).lower().replace("_", "-")
        version = str(package.get("version", ""))
        if name:
            result[name] = version
    if not result:
        raise SkillCtlError(f"锁文件中没有 {platform} 包。")
    return result


def external_dependency_errors(skill: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for dep in skill["dependencies"]["external"]:
        check = dep["check"]
        if check["kind"] == "executable" and shutil.which(check["value"]) is None:
            errors.append(f"{skill['name']}: 找不到外部命令 {check['value']}")
        elif check["kind"] == "path" and not Path(check["value"]).exists():
            errors.append(f"{skill['name']}: 找不到外部路径 {check['value']}")
        elif check["kind"] == "mcp":
            result = subprocess.run(
                ["codex", "mcp", "get", check["value"]],
                cwd=REPO_ROOT, text=True, capture_output=True, shell=False,
            )
            if result.returncode != 0:
                errors.append(f"{skill['name']}: MCP 未注册 {check['value']}")
    for mcp in skill["dependencies"]["mcp"]:
        if shutil.which("codex") is None:
            errors.append(f"{skill['name']}: 找不到 codex，无法检查 MCP {mcp['name']}")
            continue
        result = subprocess.run(
            ["codex", "mcp", "get", mcp["name"]],
            cwd=REPO_ROOT, text=True, capture_output=True, shell=False,
        )
        if result.returncode != 0:
            errors.append(f"{skill['name']}: MCP 未注册 {mcp['name']}")
    return errors


def find_legacy_agent_references() -> list[str]:
    hits: list[str] = []
    excluded_roots = {".git", "competition", "reference"}
    binary_suffixes = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".docx", ".xlsx", ".xls", ".zip"}
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file() or any(part in excluded_roots for part in path.relative_to(REPO_ROOT).parts):
            continue
        if path.suffix.lower() in binary_suffixes or path.name == "environment.win-64.lock.yml":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        old_forward = ".agent" + "/"
        old_backward = ".agent" + "\\"
        if old_forward in text or old_backward in text:
            hits.append(path.relative_to(REPO_ROOT).as_posix())
    return sorted(hits)


def cmd_doctor(args: argparse.Namespace) -> int:
    failures: list[str] = []
    warnings: list[str] = []
    try:
        registry = load_registry()
        validate_registry_schema(registry)
    except SkillCtlError as exc:
        print(f"[失败] {exc}")
        return 1
    names = [item["name"] for item in registry["skills"]]
    if len(names) != len(set(names)):
        failures.append("注册表存在重复 Skill 名称")
    for skill in registry["skills"]:
        failures.extend(check_skill_entry(skill))
        if skill["status"] == "accepted":
            failures.extend(external_dependency_errors(skill))
    manifest = safe_repo_path(registry["environment"]["manifest"])
    expected_manifest = render_environment(registry)
    if not manifest.is_file() or manifest.read_text(encoding="utf-8") != expected_manifest:
        failures.append("environment.yml 与注册表中的已接纳依赖不一致")
    try:
        installed = installed_packages(registry["environment"]["name"])
        conda_specs, pip_specs = canonical_dependencies(registry)
        for spec in conda_specs:
            ok, message = requirement_satisfied(spec, installed, pip=False)
            if not ok:
                failures.append(message)
        for spec in pip_specs:
            ok, message = requirement_satisfied(spec, installed, pip=True)
            if not ok:
                failures.append(message)
        try:
            locked = read_lock_packages(
                safe_repo_path(registry["environment"]["lockfile"]),
                registry["environment"]["platform"],
            )
            missing_or_wrong = [
                f"{name}: installed={installed.get(name)!r}, locked={version!r}"
                for name, version in locked.items()
                if installed.get(name) != version
            ]
            extras = sorted(set(installed) - set(locked))
            if args.release:
                failures.extend(f"锁漂移 {item}" for item in missing_or_wrong)
                failures.extend(f"锁外额外包 {name}={installed[name]}" for name in extras)
            else:
                if missing_or_wrong:
                    warnings.append(f"当前环境与锁有 {len(missing_or_wrong)} 个版本/缺失差异")
                if extras:
                    warnings.append(f"当前环境有 {len(extras)} 个锁外额外包")
        except SkillCtlError as exc:
            if args.release:
                failures.append(str(exc))
            else:
                warnings.append(str(exc))
    except (SkillCtlError, json.JSONDecodeError) as exc:
        failures.append(f"无法检查 Conda 环境：{exc}")
    if args.release:
        candidates = [item["name"] for item in registry["skills"] if item["status"] == "candidate"]
        candidate_dirs = [
            item.name for item in (REPO_ROOT / ".agents" / "candidates").iterdir()
            if item.is_dir()
        ]
        unresolved = sorted(set(candidates + candidate_dirs))
        if unresolved:
            failures.append("仍有候选 Skill：" + ", ".join(unresolved))
        legacy = find_legacy_agent_references()
        if legacy:
            failures.append("仍有旧单数 Agent 目录活跃引用：" + ", ".join(legacy))
    for warning in warnings:
        print(f"[警告] {warning}")
    for failure in failures:
        print(f"[失败] {failure}")
    if failures:
        print(f"doctor 未通过：{len(failures)} 个失败，{len(warnings)} 个警告。")
        return 1
    print(f"doctor 通过：0 个失败，{len(warnings)} 个警告。")
    return 0


def cmd_rehash(args: argparse.Namespace) -> int:
    registry = load_registry()
    validate_registry_schema(registry)
    skills = [find_skill(registry, args.name)] if args.name else registry["skills"]
    for skill in skills:
        path = safe_repo_path(skill["path"], allow_missing=False)
        actual = tree_hash(path)
        print(f"{skill['name']}: {skill['content_sha256']} -> {actual}")
        if args.apply:
            skill["content_sha256"] = actual
    if args.apply:
        save_registry(registry)
        print("[完成] 已更新内容哈希。")
    else:
        print("[预览] 未写回；需要时增加 --apply。")
    return 0


def cmd_env_rebuild(args: argparse.Namespace) -> int:
    registry = load_registry()
    validate_registry_schema(registry)
    env = registry["environment"]
    if args.confirm != env["name"]:
        raise SkillCtlError(f"重建环境必须显式传入 --confirm {env['name']}。")
    if os.environ.get("CONDA_DEFAULT_ENV") == env["name"]:
        raise SkillCtlError("不能从正在运行的目标环境内重建自身；请先切换到 base。")
    lockfile = safe_repo_path(env["lockfile"], allow_missing=False)
    commands = [
        ["conda", "create", "-n", BOOTSTRAP_ENV, "-c", "conda-forge", "conda-lock", "-y"],
        ["conda", "env", "remove", "-n", env["name"], "-y"],
        ["conda", "run", "-n", BOOTSTRAP_ENV, "conda-lock", "install", "--name", env["name"], str(lockfile)],
        ["conda", "env", "remove", "-n", BOOTSTRAP_ENV, "-y"],
    ]
    print(f"将从精确锁重建 {env['name']}；这是破坏性操作。")
    if not args.apply:
        for command in commands:
            run_command(command, apply=False)
        return 0
    listed = run_command(["conda", "env", "list", "--json"], apply=True, capture=True)
    assert listed is not None
    existing = {
        Path(path).name.casefold() for path in json.loads(listed.stdout).get("envs", [])
    }
    if BOOTSTRAP_ENV.casefold() in existing:
        raise SkillCtlError(
            f"保留的临时环境名已存在，拒绝覆盖：{BOOTSTRAP_ENV}"
        )
    run_command(commands[0], apply=True)
    try:
        run_command(commands[1], apply=True)
        run_command(commands[2], apply=True)
    finally:
        run_command(commands[3], apply=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="项目级 Skill 与依赖生命周期管理")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="列出注册的 Skill")
    list_parser.add_argument("--status", choices=["candidate", "accepted", "disabled"])
    list_parser.set_defaults(func=cmd_list)

    search_parser = sub.add_parser("search", help="按名称、描述和标签搜索")
    search_parser.add_argument("query")
    search_parser.set_defaults(func=cmd_search)

    show_parser = sub.add_parser("show", help="显示一个 Skill 的完整登记信息")
    show_parser.add_argument("name")
    show_parser.set_defaults(func=cmd_show)

    stage_parser = sub.add_parser("stage", help="把本地或固定 Git revision 暂存为候选")
    stage_parser.add_argument("--source", required=True)
    stage_parser.add_argument("--ref")
    stage_parser.add_argument("--subdir")
    stage_parser.add_argument("--name")
    stage_parser.add_argument(
        "--source-type", choices=["team", "official", "third-party", "local"]
    )
    stage_parser.add_argument("--license", required=True)
    stage_parser.add_argument("--tag", action="append")
    stage_parser.add_argument("--conda", action="append")
    stage_parser.add_argument("--pip", action="append")
    stage_parser.add_argument("--apply", action="store_true")
    stage_parser.set_defaults(func=cmd_stage)

    deps_parser = sub.add_parser("deps", help="管理 Skill 依赖")
    deps_sub = deps_parser.add_subparsers(dest="deps_command", required=True)
    install_parser = deps_sub.add_parser("install", help="安装某个 Skill 声明的依赖")
    install_parser.add_argument("name")
    install_parser.add_argument("--apply", action="store_true")
    install_parser.set_defaults(func=cmd_deps_install)

    validate_parser = sub.add_parser("validate", help="验证 Skill 并记录证据")
    validate_parser.add_argument("name")
    validate_parser.add_argument("--evidence", action="append")
    validate_parser.add_argument("--apply", action="store_true")
    validate_parser.set_defaults(func=cmd_validate)

    promote_parser = sub.add_parser("promote", help="人工确认后接纳候选 Skill")
    promote_parser.add_argument("name")
    promote_parser.add_argument("--accepted-by", required=True)
    promote_parser.add_argument("--apply", action="store_true")
    promote_parser.set_defaults(func=cmd_promote)

    doctor_parser = sub.add_parser("doctor", help="检查 Skill、环境和锁漂移")
    doctor_parser.add_argument("--release", action="store_true")
    doctor_parser.set_defaults(func=cmd_doctor)

    rehash_parser = sub.add_parser("rehash", help="重新计算登记的 Skill 内容哈希")
    rehash_parser.add_argument("name", nargs="?")
    rehash_parser.add_argument("--apply", action="store_true")
    rehash_parser.set_defaults(func=cmd_rehash)

    env_parser = sub.add_parser("env", help="锁定或重建统一环境")
    env_sub = env_parser.add_subparsers(dest="env_command", required=True)
    lock_parser = env_sub.add_parser("lock", help="生成 win-64 精确锁")
    lock_parser.add_argument("--apply", action="store_true")
    lock_parser.set_defaults(func=cmd_env_lock)
    rebuild_parser = env_sub.add_parser("rebuild", help="从精确锁破坏性重建环境")
    rebuild_parser.add_argument("--confirm", required=True)
    rebuild_parser.add_argument("--apply", action="store_true")
    rebuild_parser.set_defaults(func=cmd_env_rebuild)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return int(args.func(args))
    except SkillCtlError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("[中止] 用户取消。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
