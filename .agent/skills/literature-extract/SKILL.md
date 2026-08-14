---
name: literature-extract
description: 从文献中提取"问题-模型-算法-结果"四要素并写入结构化笔记。当用户要求处理文献、写阅读笔记或导入论文时使用。
---

# 文献结构化提取 Skill

## 目标
对给定文献提取四要素，写入 `reference/literature/reading_notes/<citekey>.md`。

## 步骤
1. 确认文献已存在于 `reference/literature/zotero_library.bib`（红线：未导入 Zotero 不得引用）。
2. 读取 PDF 或摘要，按 `.agent/prompts/literature_extract.md` 模板提取。
3. 输出笔记到 `reading_notes/`，文件名用 BibTeX cite key。

## 约束
- 只基于原文，不臆造。
- 公式用 LaTeX。
