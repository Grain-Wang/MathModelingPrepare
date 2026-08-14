# 灰色关联分析 (Grey Relational Analysis, GRA)

> **一句话速记**：比较各对象序列与"参考序列"的几何形状相似度，越相似关联度越高。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：样本量小、信息贫乏（"小样本、贫信息"）的赛题；找影响因素主次排序（关联度排序）；与 TOPSIS/熵权结合做综合评价排序（灰色综合评价）。
- **不适用场景**：样本多且分布明确时不如统计回归方法；需先确定参考序列（母序列）；无量纲化方法选择会影响最终结果。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：对样本量和数据分布要求极低，无需大样本；计算简单、无需统计检验；能处理关系不明确、信息不完全的系统。
- **局限性**：分辨系数 $\rho$ 取值主观（常取 0.5）；只能给相对排序，无统计显著性；对无量纲化方法敏感。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 确定参考序列（母序列，如最优指标组合）与比较序列。
2. 无量纲化（初值化或均值化，消除量纲）。
3. 计算各点关联系数 $\xi_{ij}$。
4. 求关联度 $r_i$（关联系数均值）并排序。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
关联系数（$\rho$ 为分辨系数，常取 0.5）：

$$\xi_{ij} = \frac{\min_i\min_j |x_{0j}-x_{ij}| + \rho \max_i\max_j |x_{0j}-x_{ij}|}{|x_{0j}-x_{ij}| + \rho \max_i\max_j |x_{0j}-x_{ij}|}$$

关联度（$m$ 为指标数）：

$$r_i = \frac{1}{m}\sum_{j=1}^{m}\xi_{ij}$$

$r_i$ 越大，第 $i$ 个序列与参考序列关联越强。

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：numpy（手写）
import numpy as np

def grey_relational(X0, X, rho=0.5):
    """X0: 参考序列 (m,)；X: 比较序列矩阵 (n,m)"""
    X0 = X0 / X0[0]                      # 初值化
    X = X / X[:, [0]]
    diff = np.abs(X - X0)                # 绝对差
    dmax, dmin = diff.max(), diff.min()
    xi = (dmin + rho * dmax) / (diff + rho * dmax)  # 关联系数
    r = xi.mean(axis=1)                  # 关联度
    return r                             # 越大关联越强, argsort 排序
```
