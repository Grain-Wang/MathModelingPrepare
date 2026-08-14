---
name: citation-check
description: 校验 BibTeX 完整性、查重并生成引用校验清单。当用户要求核对参考文献、检查 BibTeX 或清理引用时使用。
---

# 引用校验 Skill

## 目标
校验 `reference/literature/zotero_library.bib` 完整性，生成 `citation_checklist.md`。

## 步骤
1. 解析 bib，逐条检查必要字段（author/title/year/journal）。
2. 按 DOI/标题查重。
3. 标记任何非 Zotero 来源的条目（红线：删除）。
4. 输出/更新 `reference/literature/citation_checklist.md`。

## 约束
- 不修改 bib 本身（bib 由 Zotero 同步，勿手改）。
