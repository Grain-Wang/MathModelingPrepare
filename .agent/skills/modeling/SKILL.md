---
name: modeling
description: 数学建模主技能：读题、拆解子问题、选择最小充分模型、写出严谨的模型合同，并通过确定性校验、作者自检、DeepSeek API 与 ChatGPT Pro 网页端双通道评审后交付。用于华为杯赛题的建模阶段。
---

# 主建模

把本 Skill 作为建模阶段的唯一入口：完成「读题 → 拆解 → 选型 → 数学定义 → 验证方案 → 三件套 → 确定性校验 → 作者自检 → 双通道评审」全流程。产物只写入 `projects/02_modeling/`；`competition/`、外部参考与 Schema 一律只读。

## 运行约定

- `REPO_ROOT`：包含 `.agent/`、`competition/`、`projects/` 的项目根目录（即 MathModelingPrepare）。
- `WRITE_ROOT`：`projects/02_modeling/`，本 Skill 的唯一写入根目录。
- `EXT_REF`（外部只读参考，实际路径见 `tools_config.yaml` 的 `references` 段）：
  - `建模设计理论.md`、`常见模式.md` —— 来自 math_modeling
  - `model-contract.schema.json` —— 合同校验用，来自 math_modeling
- 原始题目、附件、官方规则、外部参考、Schema 一律只读。

## 固定产物（三件套）

1. `projects/02_modeling/题目分析报告.md`
2. `projects/02_modeling/术语表格.md`
3. `projects/02_modeling/model-contract.json`

Markdown 供人阅读，JSON 合同供下游编码/审查 Skill 稳定消费。

## 执行顺序

1. 读题与附件盘点（记录哈希/版本，只读）。
2. 子问题拆解 + 数据理解。
3. 先写「结论目标」，再选模型。
4. 最小充分模型集合，每个模型定角色与必要性。
5. 数学定义 + 算法步骤/停止条件/复杂度。
6. 验证方案（留出/回测/残差/可行性/灵敏度，阈值注明依据）。
7. 写三件套 → 确定性校验 → 作者自检 → DeepSeek API 与 ChatGPT Pro 网页端分别评审，见 `references/门禁与打回.md`。

## 校验与评审（发现 P0/P1 即打回重改）

- **确定性 Schema 校验**：`python .agent/skills/modeling/scripts/validate_model_contract.py --contract projects/02_modeling/model-contract.json`
- **作者自检**：按 `references/质检清单.md` 逐条确定性勾选。
- **DeepSeek API 评审**：运行 `python .agent/skills/modeling/scripts/run_review.py`，只调用 `tools_config.yaml` 中 `access: api` 的 DeepSeek reviewer，产出 `projects/02_modeling/qa/R1.json`。
- **ChatGPT Pro 网页端评审**：不由脚本调用且不使用 API Key。它以只读方式查看 `tools_config.yaml` 的 `repository_read_scope`，按照 `references/评审标准.md` 给出反馈，由参赛队员转交。
- 两个渠道互不读取对方反馈；参赛队员确认两方 P0/P1 均处理后，才进入编码阶段。不生成自动门禁回执。

## 何时加载

| 情形 | 读取 |
|---|---|
| 开始分析 | `references/工作流程.md` |
| 设计模型组合 | `EXT_REF/建模设计理论.md` |
| 常见问题模式 | `EXT_REF/常见模式.md` |
| 写合同 | `references/前置合同.md` |
| 交付前自检 | `references/质检清单.md` |
| 独立评审 | `references/评审标准.md` |
| 校验、评审与打回 | `references/门禁与打回.md` |

## 选择原则

- 最小充分模型集合；每个模型支撑不可替代的主张、机制、接口或独立验证。
- 可证伪、可实现、可追溯；创新点必须能映射到具体实现与验证。
- 复杂度由问题决定，不把复杂度本身当优点。

## 反馈修正

收到任一评审渠道的修改建议，或编码阶段反馈模型不可实现时，基于具体问题与数据证据修订三件套，并重新完成校验、自检和两方复核；不另建平行版本。
