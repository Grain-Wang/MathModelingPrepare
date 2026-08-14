# 蒙特卡洛模拟 (Monte Carlo Simulation, MCS)

> **一句话速记**：用大量随机抽样逼近解析难求的积分/概率/期望，靠大数定律"以次数换精度"。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 风险概率估计：项目工期/成本、投资组合 VaR、排队等待时间等含随机变量的系统。
  - 高维/复杂积分与期望：定积分、期权定价、可靠性（故障概率）估计。
  - 随机过程仿真：随机游走、扩散、带随机扰动的库存/供应链优化。
- **不适用场景**：
  - 有解析解且低维的确定性计算（直接算更快更准）。
  - 精度要求极高的问题——MCS 误差按 $O(1/\sqrt{N})$ 收敛，需大量样本才降误差。
  - 分布假设不明确、随机变量间依赖关系复杂且无法建模时结果不可信。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 适用面广，几乎任何可"生成样本再统计"的问题都能做，维度灾难影响小。
  - 实现简单直观，容易并行与扩展。
  - 能同时给出点估计与置信区间，可量化不确定性。
- **局限性**：
  - 收敛慢，精度每提升 10 倍需样本数提升 100 倍。
  - 依赖随机数质量与分布假设，坏种子/坏分布直接污染结果。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **建模随机性**：确定随机变量的分布类型与参数（正态、均匀、指数等）。
2. **抽样**：固定随机种子，生成 $N$ 组样本。
3. **映射与统计**：把每组样本代入模型得到输出，求均值、分位数、置信区间。
4. **降方差与定样本量**：用对偶变量、控制变量、重要抽样缩减方差；按精度要求用 $\hat{\sigma}$ 反推所需 $N$。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
大数定律——样本均值收敛到期望（MCS 的根基）：

$$\hat{\mu}=\frac{1}{N}\sum_{i=1}^{N} g(X_i)\ \xrightarrow{\ N\to\infty\ }\ E[g(X)]=\int g(x)f(x)\,dx$$

中心极限定理给出误差尺度与置信区间：

$$\hat{\mu}\pm z_{\alpha/2}\frac{\hat{\sigma}}{\sqrt{N}},\quad \hat{\sigma}^2=\frac{1}{N-1}\sum_{i=1}^{N}(g(X_i)-\hat{\mu})^2$$

（误差 $\propto 1/\sqrt{N}$，这是 MCS 收敛慢的根源。）

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：numpy（向量化抽样）、scipy.stats（分布）
import numpy as np
from scipy import stats

np.random.seed(42)                    # 固定种子保证可复现

# 例1：圆周率 —— 投点法（几何概率估计）
N = 1_000_000
x, y = np.random.rand(N), np.random.rand(N)
inside = (x**2 + y**2) <= 1.0
pi_hat = 4 * inside.mean()
print("pi 估计:", pi_hat)

# 例2：项目工期 = 三个子任务之和（各服从三角/正态分布）
def simulate_duration(n=100_000):
    a = np.random.triangular(5, 8, 12, n)      # 子任务1
    b = np.random.normal(10, 2, n)             # 子任务2
    c = np.random.exponential(3, n)            # 子任务3
    return a + b + c

T = simulate_duration()
mu, sigma = T.mean(), T.std(ddof=1)
z = stats.norm.ppf(0.975)                     # 95% 置信区间
print(f"工期均值={mu:.2f}  95%CI=[{mu-z*sigma/np.sqrt(len(T)):.2f}, "
      f"{mu+z*sigma/np.sqrt(len(T)):.2f}]")
print("超过 30 天的概率:", (T > 30).mean())
```
