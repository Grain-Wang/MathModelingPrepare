# 马尔可夫链 (Markov Chain, MC)

> **一句话速记**：未来只取决于当前状态（无后效性），用转移矩阵 $P$ 刻画状态间跳转概率，通过矩阵运算预测长期行为。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 状态离散且"下一步只与当前有关"的预测：天气状态、信用评级迁移、用户行为（活跃/流失）预测。
  - 市场占有率（品牌切换）、人口/人员流动、设备状态（正常/故障）的长期稳态分析。
  - 排名类问题（PageRank 可视为随机游走的平稳分布）、隐马尔可夫 HMM 的底层模型。
- **不适用场景**：
  - 明显依赖历史（高阶记忆）或受外部变量驱动的序列（改用时间序列/回归）。
  - 状态连续、变化是微分式演化的系统（改用微分方程）。
  - 转移概率随时间显著变化（非齐次）且难以估计的情况，需谨慎。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 模型简单、可解释，转移矩阵可由历史频率直接估计。
  - 矩阵运算即可得到 $n$ 步预测 $P^n$ 与平稳分布，计算高效。
  - 平稳分布、吸收概率等有成熟理论（Chapman-Kolmogorov 方程）。
- **局限性**：
  - 一阶无后效假设过强，现实问题常被违反。
  - 对数据量敏感，稀疏转移难以估计；只刻画概率均值，不做个体轨迹。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **定义状态空间**：将系统离散为有限状态集合 $\{1,\dots,n\}$（如晴/阴/雨）。
2. **估计转移矩阵**：由历史频数 $P_{ij}=\frac{\#(i\to j)}{\# i}$，保证每行和为 1。
3. **预测与稳态**：$n$ 步分布 $\pi^{(n)}=\pi^{(0)}P^n$；解 $\pi=\pi P$（即求 $P^T$ 特征值 1 对应的特征向量并归一化）得平稳分布。
4. **验证**：检验马尔可夫性（卡方检验相邻转移是否独立），评估预测误差。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
转移矩阵与一步/多步转移（Chapman-Kolmogorov）：

$$P_{ij}=P(X_{t+1}=j\mid X_t=i),\quad P^{(n)}=P^n$$

平稳分布 $\pi$（满足 $\pi P=\pi$ 且 $\sum_i \pi_i=1$）：

$$\pi = \pi P \quad\Longleftrightarrow\quad \pi (I-P)=0,\ \ \pi \mathbf{1}=1$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：numpy（转移矩阵与幂运算）、scipy.linalg（特征向量求平稳分布）
import numpy as np
from scipy.linalg import eig

# 由频数估计转移矩阵（行和为 1）
def estimate_P(seq, n_states):
    P = np.zeros((n_states, n_states))
    for i, j in zip(seq[:-1], seq[1:]):
        P[i, j] += 1
    row_sum = P.sum(axis=1, keepdims=True)
    P = P / np.where(row_sum == 0, 1, row_sum)  # 避免除零
    return P

seq = [0, 1, 0, 2, 2, 1, 0, 0, 2, 1]   # 示例状态序列（3 个状态）
P = estimate_P(seq, 3)

# n 步预测
pi0 = np.array([0.5, 0.3, 0.2])
print("3 步后分布:", pi0 @ np.linalg.matrix_power(P, 3))

# 平稳分布：P^T 特征值≈1 对应特征向量归一化
vals, vecs = eig(P.T)
idx = np.argmin(np.abs(vals - 1.0))
pi = np.real(vecs[:, idx]); pi = pi / pi.sum()
print("平稳分布 pi:", pi)

# 验证：pi @ P 应 ≈ pi
print("误差:", np.max(np.abs(pi @ P - pi)))
```
