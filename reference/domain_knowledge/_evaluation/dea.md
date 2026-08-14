# 数据包络分析 (Data Envelopment Analysis, DEA)

> **一句话速记**：用投入产出比衡量"多投入多产出"决策单元的相对效率，效率值为 1 即为 DEA 有效。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：效率评价（企业、银行、医院、高校、区域经济效率）；多投入多产出且无需预设权重的赛题；碳排放效率、创新效率、能源效率等相对效率排序与改进分析。
- **不适用场景**：样本数需 $\ge 2\times(\text{投入数}+\text{产出数})$，否则区分度差；只能给相对效率（横向比较），不能给绝对绩效；投入产出指标需非负且方向合理。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：无需预设权重，客观；可同时处理多投入多产出；能识别标杆（有效单元）并通过松弛变量给出改进方向。
- **局限性**：结果是相对效率，受样本集合影响（增删 DMU 会变）；对异常值敏感；经典 CCR 假设规模报酬不变，需 BCC 模型放宽。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 确定决策单元 DMU 与投入、产出指标。
2. 选择模型：CCR（规模报酬不变）或 BCC（规模报酬可变，加约束 $\sum \lambda = 1$）。
3. 每个 DMU 建立一个线性规划，求解效率 $\theta$。
4. $\theta=1$ 为有效，否则无效；用松弛变量给出改进量。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
CCR（投入导向）模型：

$$\min \theta$$

$$\text{s.t.} \quad \sum_{j=1}^{n}\lambda_j x_{j} \le \theta x_0, \qquad \sum_{j=1}^{n}\lambda_j y_j \ge y_0, \qquad \lambda_j \ge 0$$

其中 $\theta$ 为效率值，$\theta=1$ 表示 DEA 有效；$x_j, y_j$ 分别为第 $j$ 个 DMU 的投入、产出向量。BCC 模型额外增加约束 $\sum_j \lambda_j = 1$。

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：scipy.optimize.linprog（手写 CCR 线性规划）
import numpy as np
from scipy.optimize import linprog

def ccr_efficiency(X, Y, dmu):
    """X: 投入 (n,k)；Y: 产出 (n,m)；dmu: 待评单元下标"""
    n, k = X.shape
    m = Y.shape[1]
    c = np.zeros(n + 1); c[0] = 1        # 目标: 最小化 theta
    A_ub, b_ub = [], []
    for i in range(k):                   # 投入约束: sum(λ x) - θ x0 <= 0
        row = np.zeros(n + 1)
        row[1:] = X[:, i]; row[0] = -X[dmu, i]
        A_ub.append(row); b_ub.append(0)
    for o in range(m):                   # 产出约束: -sum(λ y) <= -y0
        row = np.zeros(n + 1)
        row[1:] = -Y[:, o]
        A_ub.append(row); b_ub.append(-Y[dmu, o])
    bounds = [(0, None)] * (n + 1)       # theta, λ 均 >= 0
    res = linprog(c, A_ub=np.array(A_ub), b_ub=np.array(b_ub),
                  bounds=bounds, method='highs')
    return res.x[0]                      # 效率值 theta <= 1

# 对每个 dmu 循环调用, 得到全样本效率向量; BCC 只需加等式约束 ∑λ=1
```
