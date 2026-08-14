# 非线性规划 (Nonlinear Programming, NLP)

> **一句话速记**：目标或约束含非线性项时的优化问题，通用解法是迭代局部寻优（梯度法/内点法），只有凸问题才能保证全局最优。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 连续变量的非线性建模：成本/收益随产量呈二次、指数、对数变化（如规模效应、边际递减）。
  - 曲线拟合/参数估计：最小二乘、最大似然估计本质上都是无约束非线性优化。
  - 工程与物理模型：几何结构优化、力学平衡、能耗最小化等含 $x^2, \sin x, e^{-x}$ 的模型。
- **不适用场景**：
  - 问题天然是离散/组合的（选哪几个点、走哪条路），应转整数或元启发式。
  - 非凸且多局部极值时，梯度法会陷局部解，需配合多起点或全局方法。
  - 变量维度极高且不可导/黑箱（仿真）时，宜用元启发式而非梯度法。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 表达能力强，能贴合真实非线性关系，模型更准确。
  - 求解器成熟（SQP、内点法），中小规模凸问题收敛快、精度高。
  - 可自然嵌入等式/不等式约束，KKT 条件提供理论判据。
- **局限性**：
  - 非凸问题只能得局部最优，结果依赖初值，需多起点验证。
  - 对梯度/光滑性有要求，不可导点需特殊处理。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 明确变量与目标，写出非线性目标函数 $f(\mathbf{x})$ 和约束。
2. 判断凸性：若 Hessian 半正定且约束集为凸，则局部最优即全局最优。
3. 选求解器并给初值，必要时做变量缩放（归一化）改善收敛。
4. 多起点（随机多个初值）运行，比较目标值，规避局部最优陷阱。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
一般形式：
$$\min_{\mathbf{x}} f(\mathbf{x}) \quad \text{s.t.} \quad g_i(\mathbf{x}) \le 0,\ h_j(\mathbf{x}) = 0$$

一阶最优性条件（KKT，局部最优的必要条件）：
$$\nabla f(\mathbf{x}^*) + \sum_i \lambda_i \nabla g_i(\mathbf{x}^*) + \sum_j \mu_j \nabla h_j(\mathbf{x}^*) = 0$$
其中 $\lambda_i \ge 0,\ \lambda_i g_i(\mathbf{x}^*)=0$（互补松弛）。

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：scipy.optimize.minimize（通用 NLP 求解器）
import numpy as np
from scipy.optimize import minimize

# 目标：min (x1-2)^2 + (x2-1)^2，s.t. x1 + x2 - 3 <= 0
def f(x):
    return (x[0]-2)**2 + (x[1]-1)**2

cons = {'type': 'ineq', 'fun': lambda x: 3 - (x[0] + x[1])}  # g(x)>=0 形式
x0 = np.array([0.0, 0.0])
res = minimize(f, x0, method='SLSQP', constraints=[cons])
print(res.x, res.fun)

# 无约束最小二乘拟合（曲线拟合典型场景）
from scipy.optimize import curve_fit
def model(x, a, b):
    return a * np.exp(-b * x)
popt, _ = curve_fit(model, xdata, ydata, p0=[1.0, 0.5])  # 返回拟合参数
```
