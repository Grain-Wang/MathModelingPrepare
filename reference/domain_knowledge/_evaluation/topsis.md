# 优劣解距离法 (Technique for Order Preference by Similarity to Ideal Solution, TOPSIS)

> **一句话速记**：离最优解最近、离最劣解最远，就是最好的方案。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：多方案多指标排序（城市竞争力、供应商评价、企业绩效排名）；需要给出明确优劣顺序与相对贴近度的赛题；与熵权法/AHP 结合作为综合评价核心。
- **不适用场景**：指标高度相关且未做去相关处理时结果失真；样本需先正向化归一化；对极端值敏感，理想解随样本集合变化。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：充分利用原始数据，结果体现各方案与理想解的差距；对样本量和分布要求低；计算简单、几何直观（欧氏距离）。
- **局限性**：默认各指标等权，需外部配权重；未考虑指标相关性；增减对象会改变理想解，结果不稳定。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 正向化指标矩阵（成本型取倒数或 `max-x`，适度型转换）。
2. 标准化（向量归一化或极差归一化，消除量纲）。
3. 加权标准化，确定正理想解 $Z^+$ 与负理想解 $Z^-$。
4. 计算各对象到理想解的距离 $D^+$、$D^-$，求相对贴近度 $C_i$ 并排序。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
正/负理想解（效益型取 max、成本型取 min）：

$$Z^+ = (\max_i z_{i1}, \dots, \max_i z_{im}), \qquad Z^- = (\min_i z_{i1}, \dots, \min_i z_{im})$$

欧氏距离与相对贴近度：

$$D_i^+ = \sqrt{\sum_j (z_{ij}-z_j^+)^2}, \qquad D_i^- = \sqrt{\sum_j (z_{ij}-z_j^-)^2}$$

$$C_i = \frac{D_i^-}{D_i^+ + D_i^-} \in [0,1]$$

$C_i$ 越大越优。

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：numpy（手写）
import numpy as np

def topsis(X, w, benefit):
    """X: 正向化后的矩阵 (n,m)；w: 权重向量；benefit: 是否效益型 (bool 数组)"""
    Z = X / np.sqrt((X ** 2).sum(axis=0))    # 1) 向量归一化
    Z = Z * w                                 # 2) 加权
    Zp = np.where(benefit, Z.max(axis=0), Z.min(axis=0))  # 3) 正理想解
    Zn = np.where(benefit, Z.min(axis=0), Z.max(axis=0))  #    负理想解
    Dp = np.sqrt(((Z - Zp) ** 2).sum(axis=1)) # 4) 到正理想解距离
    Dn = np.sqrt(((Z - Zn) ** 2).sum(axis=1)) #    到负理想解距离
    C = Dn / (Dp + Dn)                        # 相对贴近度, 越接近 1 越优
    return C
```
