# 熵权法 (Entropy Weight Method, EWM)

> **一句话速记**：指标数据越离散、信息熵越小，说明它携带的区分信息越多，权重越大。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：多指标综合评价的客观赋权（常与 TOPSIS、灰色关联、模糊评价组合）；评价对象间指标值差异明显的赛题（城市竞争力、企业绩效、上市公司评价）；需要完全客观、避免主观偏好的权重确定。
- **不适用场景**：样本极少时熵估计不可靠；指标间高度相关时权重会被扭曲（可改用 CRITIC 法修正）；数据必须先正向化、非负化预处理。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：完全客观、无主观因素，易于解释；计算简单，手写几行即可；对区分度高的指标自动赋予更大权重。
- **局限性**：只反映数据离散程度，不考虑指标本身的业务重要性，可能违背直觉；对零值/负值敏感；样本集合变化会改变权重。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 指标正向化（正向、负向、适度指标分别处理，使所有指标同向）。
2. 归一化得到比重矩阵 $p_{ij}$。
3. 计算每个指标的信息熵 $e_j$。
4. 求信息效用值 $d_j=1-e_j$，归一化得权重 $w_j$。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
比重（$n$ 为样本数）：

$$p_{ij} = \frac{x'_{ij}}{\sum_{i=1}^{n} x'_{ij}}$$

信息熵：

$$e_j = -\frac{1}{\ln n}\sum_{i=1}^{n} p_{ij}\ln p_{ij} \quad (p_{ij}=0\ \text{时该项取}\ 0)$$

权重：

$$w_j = \frac{1-e_j}{\sum_{j=1}^{m}(1-e_j)}$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：numpy（手写）
import numpy as np

def entropy_weight(X):
    """X: 正向化、非负后的原始矩阵 (n_samples, m_indicators)"""
    X = X / X.sum(axis=0)                     # 比重 p_ij
    n = X.shape[0]
    e = -(X * np.log(X + 1e-12)).sum(axis=0) / np.log(n)  # 信息熵, +1e-12 防 log(0)
    d = 1 - e                                 # 信息效用值
    w = d / d.sum()                           # 熵权
    return w

# 负向指标正向化示例：x' = max(x) - x
# 适度指标正向化示例：x' = 1 / (1 + |x - best|)
```
