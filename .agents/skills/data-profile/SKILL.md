---
name: data-profile
description: 对数据集做快速探查并输出字段字典与统计摘要。当用户要求了解数据、生成字段说明或探查缺失值时使用。
---

# 数据探查 Skill

## 目标
对 `projects/01_data/raw/` 或 `competition/data/` 的数据输出探查报告。

## 步骤
1. 读取数据（优先 Polars/pandas）。
2. 输出：行数、列名、类型、缺失率、唯一值、数值统计、样本。
3. 若为官方附件，补充字段含义到 `reference/dataset_docs/`。

## 约束
- 只读 `competition/`，不修改；分析用副本放 `projects/01_data/`。
