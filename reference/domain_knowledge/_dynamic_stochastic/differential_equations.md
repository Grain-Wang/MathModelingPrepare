# 微分方程模型 (Differential Equations, ODE / PDE)

> **一句话速记**：用"变化率 = 函数关系"刻画系统随时间/空间演化的规律，通过数值或符号求解得到状态曲线。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 传染病传播、种群竞争/捕食（Lotka-Volterra）、经济增长——状态量随时间连续变化且可写出变化率关系。
  - 物体运动、温度传导、污染物扩散、药物在体内代谢（房室模型）等物理/生化过程。
  - 需要求"任意时刻状态"或"长期趋势/平衡点"的连续动力系统问题。
- **不适用场景**：
  - 状态是离散跳变、个体异质性强的系统（改用马尔可夫链 / 元胞自动机 / 基于 Agent 的模拟）。
  - 机制不明确、只能靠数据外推的问题（改用回归/时间序列），或随机性主导的问题（改用随机微分/蒙特卡洛）。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 物理意义清晰、可解释性强，参数可溯源（如传染率 $\beta$、恢复率 $\gamma$）。
  - 可做定性分析（平衡点稳定性、相图）与解析解（线性系统）。
  - 数值求解库成熟，ODE 一维到高维均可高效求解。
- **局限性**：
  - 依赖机理假设，模型错则结论全错；参数估计是难点（常需配合最小二乘/数据拟合）。
  - 高维 PDE 或刚性（stiff）方程数值求解开销大、需谨慎选算法。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **建模型**：明确状态变量 $x(t)$，依据守恒/速率关系写出 $\dot{x}=f(x,t,\theta)$，给定初值 $x(t_0)=x_0$。
2. **定参数**：由文献/数据拟合确定参数 $\theta$（用 `scipy.optimize.curve_fit` 或最小二乘）。
3. **求解**：线性/低维优先用 `sympy` 求解析解；一般用 `solve_ivp` 数值求解。
4. **验证与解读**：与真实数据对比校准，分析平衡点、稳定性、敏感性。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
一阶 ODE 系统与初值问题：

$$\dot{\mathbf{x}} = f(\mathbf{x}, t), \quad \mathbf{x}(t_0)=\mathbf{x}_0$$

经典 SIR 传染病模型（$N=S+I+R$ 守恒）：

$$\dot{S}=-\beta \frac{SI}{N},\quad \dot{I}=\beta \frac{SI}{N}-\gamma I,\quad \dot{R}=\gamma I$$

Logistic 增长与解析解：

$$\frac{dP}{dt}=rP\left(1-\frac{P}{K}\right),\quad P(t)=\frac{K P_0 e^{rt}}{K+P_0(e^{rt}-1)}$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：scipy.integrate.solve_ivp（新版替代 odeint）、numpy、sympy
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# SIR 模型右端：状态 y = [S, I, R]
def sir(t, y, beta, gamma, N):
    S, I, R = y
    dS = -beta * S * I / N
    dI =  beta * S * I / N - gamma * I
    dR =  gamma * I
    return [dS, dI, dR]

beta, gamma, N = 0.3, 0.1, 1000
y0 = [999, 1, 0]            # 初始状态
t_span = (0, 160)

sol = solve_ivp(sir, t_span, y0, args=(beta, gamma, N),
                method='RK45', t_eval=np.linspace(0, 160, 200))

plt.plot(sol.t, sol.y[1], label='I(t) 感染者')
plt.legend(); plt.show()

# 解析解：sympy 符号求解 Logistic
import sympy as sp
t, P = sp.symbols('t P', positive=True)
r, K, P0 = sp.symbols('r K P0', positive=True)
f = sp.Function('P')
eq = sp.Eq(sp.diff(f(t), t), r * f(t) * (1 - f(t) / K))
print(sp.dsolve(eq, ics={f(0): P0}))   # 符号通解/特解
```
