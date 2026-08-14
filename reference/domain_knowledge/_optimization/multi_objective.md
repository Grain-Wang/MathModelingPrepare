# 多目标优化 (Multi-Objective Optimization, MOO)

> **一句话速记**：同时优化多个互相冲突的目标，输出的是帕累托（Pareto）前沿而非单一解，供决策者按偏好权衡取舍。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 成本 vs 质量/时间/风险权衡：如运输"费用最低"与"时间最短"冲突。
  - 经济效益 vs 环境/社会效益：碳排放最小与利润最大需同时考虑。
  - 多维度评价的系统设计：投资组合"收益最大化 vs 风险最小化"。
- **不适用场景**：
  - 各目标可用统一量纲（如都折算成钱）聚合为单一目标时，直接单目标求解更简单。
  - 目标间无冲突、同增同减时，本质是单目标，不必上 MOO。
  - 需要"唯一答案"且决策者无法参与权衡时，MOO 给出的解集反而难落地。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 不预先加权，客观呈现各目标的折中关系，结果全面、不偏颇。
  - Pareto 前沿直观展示"改善一个目标要以牺牲另一个为代价"，适合写进论文分析。
  - 与 NSGA-II 等进化算法结合，能一次得到一整组折中解。
- **局限性**：
  - 输出是解集而非单解，需额外用决策方法（TOPSIS、AHP、加权）选出最终方案。
  - 高维目标（>3）时前沿难以可视化、解集维护困难。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 明确各目标函数 $f_1,\dots,f_m$ 与约束，统一为最小化（最大化取负号）。
2. 选解法：标量化（加权和/ε-约束）或进化算法（NSGA-II）生成 Pareto 前沿。
3. 求出一组非支配解，验证每个解都不能在不损害其他目标下改进任一目标。
4. 用多准则决策方法（如 TOPSIS、熵权法、层次分析法）从前沿中选最终方案。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
多目标问题（统一最小化）：
$$\min_{\mathbf{x} \in \Omega} \big( f_1(\mathbf{x}), f_2(\mathbf{x}), \ldots, f_m(\mathbf{x}) \big)$$

加权和标量化（最常用的单目标化方法）：
$$\min_{\mathbf{x} \in \Omega} \sum_{i=1}^{m} w_i f_i(\mathbf{x}), \quad \sum_i w_i = 1,\ w_i \ge 0$$

帕累托支配关系：称 $\mathbf{x}_1$ 支配 $\mathbf{x}_2$，若对所有 $i$ 有 $f_i(\mathbf{x}_1) \le f_i(\mathbf{x}_2)$，且至少一个严格小于。

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：pymoo（NSGA-II 等进化多目标求解）
import numpy as np
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize

class MyProblem(ElementwiseProblem):
    def __init__(self):
        super().__init__(n_var=2, n_obj=2, xl=np.array([0, 0]), xu=np.array([5, 5]))
    def _evaluate(self, x, out, *args, **kwargs):
        f1 = x[0]**2 + x[1]**2          # 目标1
        f2 = (x[0]-3)**2 + (x[1]-3)**2  # 目标2
        out["F"] = [f1, f2]

problem = MyProblem()
algorithm = NSGA2(pop_size=100)
res = minimize(problem, algorithm, ('n_gen', 200), verbose=False)
F = res.F          # Pareto 前沿的目标值矩阵
X = res.X          # 对应的决策变量
print(F)

# 简单标量化：加权和（可自行扫多组权重得近似前沿）
# for w in np.linspace(0, 1, 11):
#     F_weighted = w*f1(x) + (1-w)*f2(x)  -> 用单目标求解器求最优
```
