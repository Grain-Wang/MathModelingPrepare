# 灰色预测 (GM(1,1), Grey Prediction)

> **一句话速记**：对"小样本、贫信息"序列做一次累加生成，用微分方程拟合指数趋势再累减还原预测。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 小样本预测：数据仅 4~10 个点（如新项目前几年数据、新兴指标历史短）。
  - 近似指数增长或单调趋势的序列（如某产品渗透率、能源消耗、事故率）。
  - 数据量少、规律不明显、传统统计方法无法满足样本量要求的赛题。
- **不适用场景**：
  - 数据充足（几十点以上）时，GM(1,1) 精度常不如 ARIMA/回归。
  - 波动剧烈、非单调或周期性序列（累加后仍不呈指数规律）。
  - 长期预测（模型本质是指数外推，远期误差发散）。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：样本需求极小（≥4 个点即可）、计算简单可手写、无分布假设、对贫信息有效。
- **局限性**：只适合指数/单调趋势、无法刻画季节与波动、长步长精度差、需做残差检验（后验差比 $C$ 与小误差概率 $P$）。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **级比检验**：原始序列 $x^{(0)}(k)$ 的级比 $\lambda(k)=x^{(0)}(k-1)/x^{(0)}(k)$ 应落在可容覆盖 $(e^{-2/(n+1)}, e^{2/(n+1)})$ 内，不满足可先平移。
2. **一次累加生成 (1-AGO)**：$x^{(1)}(k)=\sum_{i=1}^k x^{(0)}(i)$，使杂乱序列呈单调递增。
3. **构建白化微分方程并最小二乘求参**：解出发展系数 $a$ 与灰作用量 $b$。
4. **还原与检验**：用时间响应式预测 $x^{(1)}$ 后累减还原 $\hat x^{(0)}(k)$；算后验差比 $C$、小误差概率 $P$ 定精度等级。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
GM(1,1) 白化微分方程（一次累加序列 $x^{(1)}$ 满足）：
$$\frac{dx^{(1)}}{dt} + a x^{(1)} = b$$

参数估计（最小二乘，$B$ 为背景值矩阵，$Y$ 为原始序列）：
$$\hat{a} = (B^T B)^{-1} B^T Y,\quad
B=\begin{bmatrix}-\frac{x^{(1)}(1)+x^{(1)}(2)}{2} & 1\\ \vdots & \vdots \\ -\frac{x^{(1)}(n-1)+x^{(1)}(n)}{2} & 1\end{bmatrix},\; Y=\begin{bmatrix}x^{(0)}(2)\\ \vdots \\ x^{(0)}(n)\end{bmatrix}$$

时间响应式（预测累加值）与累减还原：
$$\hat x^{(1)}(k+1)=\left(x^{(0)}(1)-\frac{b}{a}\right)e^{-ak}+\frac{b}{a},\qquad \hat x^{(0)}(k+1)=\hat x^{(1)}(k+1)-\hat x^{(1)}(k)$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：numpy（手写，GM(1,1) 无官方库，纯向量化）
import numpy as np

def gm11(x0, n_predict=3):
    x0 = np.asarray(x0, dtype=float)
    x1 = x0.cumsum()                        # 1-AGO 一次累加
    n = len(x0)
    # 背景值矩阵 B（紧邻均值生成）
    z1 = 0.5 * (x1[1:] + x1[:-1])
    B = np.column_stack([-z1, np.ones(n - 1)])
    Y = x0[1:]
    a, b = np.linalg.lstsq(B, Y, rcond=None)[0]   # [a, b]
    # 时间响应式预测 x1，再累减还原 x0
    k = np.arange(n + n_predict)
    x1_hat = (x0[0] - b / a) * np.exp(-a * k) + b / a
    x0_hat = np.diff(x1_hat, prepend=x0[0])[: n + n_predict]
    # 精度检验：后验差比 C（<0.35 好，<0.5 合格，<0.65 勉强）
    resid = x0 - x0_hat[:n]
    C = resid.std() / x0.std()
    return x0_hat, (a, b, C)

x = [120, 138, 160, 185, 212]               # 小样本，4~10 点为宜
pred, params = gm11(x, n_predict=3)
print(pred)                                  # 历史拟合 + 未来预测
print('a,b,C =', params)
```
