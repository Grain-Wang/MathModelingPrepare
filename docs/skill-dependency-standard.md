# 项目级 Skill 与依赖规范

## 1. 目标与唯一入口

本规范让往年赛题演练验证过的 Skill 与运行环境可在正式比赛直接复用。统一入口为：

- 注册表：`.agents/skill-registry.yaml`
- 注册表 Schema：`.agents/schemas/skill-registry.schema.json`
- 已接纳 Skill：`.agents/skills/<name>/`
- 候选 Skill：`.agents/candidates/<name>/`
- 直接依赖：`environment.yml`
- Windows 精确锁：`environment.win-64.lock.yml`
- 管理命令：`python scripts/skillctl.py ...`

唯一 Conda 环境名为 `math_modeling`，目标平台为 `win-64`。仓库不维护离线包镜像。

## 2. 生命周期

1. **发现**：可来自官方、团队、本地或第三方 Git 仓库。
2. **暂存**：复制完整 Skill 目录到 `.agents/candidates/`；远程来源必须固定 commit 或 tag，并记录许可证。
3. **安装候选依赖**：允许装入 `math_modeling`，但此时不进入正式环境清单。
4. **验证**：检查 Schema、路径、frontmatter、内容哈希，并执行注册表中的结构化验证命令。证据必须是仓库相对路径。
5. **人工接纳**：只有验证通过、存在证据且给出 `accepted_by` 后，才移动到 `.agents/skills/`。
6. **同步环境**：接纳时把依赖合并到 `environment.yml` 并生成新的精确锁。
7. **漂移检查**：日常运行 `doctor`；正式比赛前运行 `doctor --release`。

退役 Skill 使用 `disabled` 状态保留追溯信息，不直接抹除历史。需要删除时另行人工审查。

## 3. 注册表约定

每个条目必须包含名称、描述、标签、状态、路径、来源、固定 revision、许可证、内容 SHA-256、依赖和验证记录。依赖分为：

- `conda`：Conda 直接依赖规格；
- `pip`：pip 直接依赖规格；
- `external`：仅允许 `winget`、`npm`；
- `mcp`：`stdio` 或 `http` MCP 配置，可选声明其安装方式。

验证命令使用参数数组，例如 `['python', '-m', 'unittest', '...']`，禁止使用 shell 拼接。MCP 只允许记录所需环境变量的名称；密钥值不进注册表、不进日志。

## 4. 常用命令

```powershell
# 查询
python scripts/skillctl.py list
python scripts/skillctl.py search modeling
python scripts/skillctl.py show modeling

# 引入候选（默认只预览；执行必须加 --apply）
python scripts/skillctl.py stage --source <path-or-url> --ref <commit-or-tag> --license <SPDX-or-license> --apply
python scripts/skillctl.py deps install <skill-name> --apply
python scripts/skillctl.py validate <skill-name> --evidence <repo-relative-path> --apply
python scripts/skillctl.py promote <skill-name> --accepted-by <person> --apply

# 环境和漂移
python scripts/skillctl.py env lock --apply
python scripts/skillctl.py doctor
python scripts/skillctl.py doctor --release
python scripts/skillctl.py env rebuild --confirm math_modeling --apply
```

## 5. 诊断和放行标准

日常诊断中，注册表无效、Skill 缺失、frontmatter 名称不符、哈希漂移、直接依赖缺失或精确版本不符都会失败；锁文件以外的包仅警告。

发布诊断更严格：候选区必须为空，活跃文件不得继续引用旧单数 Agent 目录，当前环境必须与 `win-64` 锁中的包名和版本完全一致，不允许额外包。发布检查通过只说明工程环境一致，不代表建模结论经过学术确认。

## 6. 安全和恢复

- `competition/` 始终只读。
- 管理程序拒绝绝对路径、`..` 路径穿越和 Skill 内符号链接。
- 所有修改命令默认 dry-run。
- 接纳失败时恢复注册表、环境清单与 Skill 原位置。
- 环境重建是破坏性操作，要求 `--confirm math_modeling`；应先保留锁文件并确认工作未在该环境中运行。
- 网络安装失败不改写接纳状态；修复网络或源后重新执行。
