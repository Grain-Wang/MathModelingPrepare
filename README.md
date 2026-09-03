# MathModelingPrepare

华为杯研究生数学建模竞赛项目工程。三人团队 + AI Agent 辅助。

## 快速上手

```bash
# 1. 创建环境；已有环境可用下一条更新
conda env create -f environment.yml
conda env update -n math_modeling -f environment.yml --prune

# 2. 配置本地工具路径与密钥（改完后勿提交）
cp tools_config.example.yaml tools_config.yaml
cp .env.example .env           # 填入 API Key

# 3. 从 Zotero 同步文献
python scripts/sync_zotero.py

# 4. 本地编译论文
make build-paper
```

## 目录结构速览

| 目录 | 用途 | 权限 |
|---|---|---|
| `competition/` | 赛题原文 / 附件数据 / 评分规则 | ⛔ 只读 |
| `reference/` | 参考资料与文献（Zotero 唯一真相源） | 读写 |
| `projects/` | 核心工作区（数据 / 建模 / 可视化 / 论文） | 读写 |
| `.agents/` | 已接纳/候选 Skills、注册表与 Agent 配置 | 读写 |
| `scripts/` | 跨工作区自动化脚本 | 读写 |
| `docs/` | 团队文档 | 读写 |
| `results/` | 最终提交物 | 读写 |

## 阶段性成果审核

- 建模作者生成 `projects/02_modeling/` 下的三件套草稿。
- DeepSeek 通过 API 独立评审，机器可读反馈写入 `projects/02_modeling/qa/R1.json`。
- ChatGPT Pro 由参赛队员在网页端发起，先读取 `.agents/skills/modeling/references/评审标准.md`，再只读指定仓库内容并直接给出反馈；它不使用 API Key，也不修改仓库。
- 两方反馈由参赛队员汇总、核实和转交；参赛队员承担最终学术责任。

## 合规红线

1. 所有参考文献以 `reference/literature/zotero_library.bib` 为唯一真相源，禁用 AI 生成的引用。
2. 阶段性成果是待人工复核的草稿，评审 AI 只读检查，不直接修改权威产物。
3. `competition/` 只读，任何修改视为违规。

Skill 与依赖的安装、验证、接纳和锁定规则见 `docs/skill-dependency-standard.md`。其余流程详见 `.agents/config/redlines.md` 与 `docs/workflow.md`。
