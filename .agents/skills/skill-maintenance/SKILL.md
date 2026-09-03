---
name: skill-maintenance
description: 管理本项目的 Skill 与依赖生命周期。用户要求查找、下载、暂存、验证、接纳或诊断项目级 Skill，或要求安装、锁定、重建 math_modeling 环境及 MCP/外部工具时使用。
---

# 项目 Skill 与依赖维护

以 `.agents/skill-registry.yaml` 为唯一注册表，以 `environment.yml` 为直接依赖清单，以 `environment.win-64.lock.yml` 为 Windows 精确环境快照。

## 边界

- 已接纳 Skill 放在 `.agents/skills/<name>/`，候选 Skill 放在 `.agents/candidates/<name>/`。
- 不修改 `competition/`，不读取、打印或写入 `.env` 和任何密钥。
- 查询命令可直接运行；下载、安装、接纳、锁定和重建仅在用户明确要求后运行。
- 第三方 Skill 必须记录固定 revision、来源和许可证；拒绝符号链接及逃逸仓库的路径。
- 候选依赖允许安装到唯一环境 `math_modeling`，但只有人工确认接纳后才能写入正式清单并重锁。
- MCP 只记录环境变量名，不记录其值；缺少所需变量时停止注册。

## 标准流程

1. 查询：`python scripts/skillctl.py list`、`search <关键词>`、`show <名称>`。
2. 暂存：`stage --source <目录或 Git URL> --ref <提交或标签> --license <许可证> --apply`。
3. 安装候选依赖：`deps install <名称> --apply`。
4. 验证：在注册表中配置无 shell 的参数数组，运行 `validate <名称> --evidence <证据路径> --apply`。
5. 人工确认后接纳：`promote <名称> --accepted-by <确认人> --apply`。该命令同步正式依赖并重建锁文件。
6. 日常检查：`doctor`；正式比赛/发布前检查：`doctor --release`。

所有变更命令默认 dry-run，只有带 `--apply` 才执行。环境重建还必须显式传入 `--confirm math_modeling`。

## 依赖规则

- Python 包优先声明为 Conda 依赖；只能通过 pip 获得或确需紧跟上游时才放入 pip 子节。
- 外部安装器仅允许 `winget` 和 `npm`；包安装不拼接 shell 字符串。
- MCP 支持 `stdio` 与 `http`；按注册表字段生成 `codex mcp add` 参数。
- 日常诊断：缺失或直接版本不符为失败，锁文件之外的额外包为警告。
- 发布诊断：候选未清空、内容哈希漂移、旧单数 Agent 目录活跃引用、锁文件缺失或环境与锁不完全一致均为失败。

详细字段、命令和故障恢复规则见 `docs/skill-dependency-standard.md`。
