# 引用校验 Prompt

校验 `reference/literature/zotero_library.bib` 中每条 BibTeX 的完整性。

## 检查项

1. 每条 entry 是否包含必要字段：author / title / year / journal(或 booktitle)。
2. cite key 是否唯一、无特殊字符、与论文中 `\cite{}` 一致。
3. 是否存在重复条目（相同 DOI/标题）。
4. 是否有 AI 生成、未经 Zotero 验证的条目（红线：必须删除）。

## 输出

生成/更新 `reference/literature/citation_checklist.md`，逐条标注 ✅ / ⚠️ / ❌。
