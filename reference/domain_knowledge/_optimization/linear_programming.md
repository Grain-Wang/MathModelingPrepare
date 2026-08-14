# 线性规划 (Linear Programming, LP)

> **一句话速记**：目标函数与约束均为线性、变量连续时，可用单纯形法/内点法求得全局最优解，是最可靠的确定性优化工具。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 资源分配：多原料、多产品、多约束下的产量最大化/成本最小化（如工厂排产、原材料配比）。
  - 运输/指派问题：从多个产地到多个销地的运输成本最小化，或任务与人员的指派。
  - 投资组合/营养配比：线性目标+线性约束的组合优化（如资金在各渠道的分配）。
- **不适用场景**：
  - 决策变量必须取整数、0-1（需转整数规划，见 integer_programming）。
  - 目标或约束含非线性项（如成本随产量二次增长、指数衰减），此时 LP 假设失效。
  - 多目标冲突且无统一量纲时（需转多目标方法）。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 有成熟高效的求解器（单纯形法、内点法），规模上千变量/约束也能秒级求解。
  - 全局最优性有理论保证，结果可复现、可解释，适合论文中做精确基准。
  - 灵敏度分析可直接给出影子价格，用于解释"约束每放宽一单位目标改善多少"。
- **局限性**：
  - 仅处理线性关系，现实问题常需线性化近似，可能损失精度。
  - 对大规模 0-1/整数变量无能为力（那是 MILP 的范畴）。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 定义决策变量：明确每个变量含义、量纲与取值范围（下限/上限）。
2. 写出目标函数：成本最小化或收益最大化，统一为 $\min$ 或 $\max$ 形式。
3. 列出所有约束：物料、产能、需求、非负性，逐条翻译成不等式/等式。
4. 调用求解器求最优解，并对关键约束做灵敏度分析（影子价格）支撑论文结论。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
标准型（最小化）：
$$\min_{\mathbf{x}} \ \mathbf{c}^T\mathbf{x} \quad \text{s.t.} \quad A\mathbf{x} \le \mathbf{b}, \quad \mathbf{x} \ge 0$$

对偶问题与影子价格：对偶变量 $y^*$ 对应原约束的影子价格，满足
$$\mathbf{c}^T\mathbf{x}^* = \mathbf{b}^T\mathbf{y}^*$$
即第 $i$ 个约束右端项 $b_i$ 每增加一单位，最优目标改善约 $y_i^*$。

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：scipy.optimize（linprog）或 PuLP（建模更直观）
from scipy.optimize import linprog

# min c^T x，s.t. A_ub x <= b_ub, x >= 0
c = [3, 2]                      # 目标系数（成本）
A_ub = [[1, 1], [2, 1]]         # 不等式约束系数
b_ub = [4, 5]                   # 不等式约束右端
bounds = [(0, None), (0, None)] # 变量上下界

res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')
print(res.x, res.fun)           # res.x 最优解, res.fun 最优目标值

# 用 PuLP 的等价写法（可读性强，适合写进论文附录）
import pulp
prob = pulp.LpProblem("allocation", pulp.LpMinimize)
x1 = pulp.LpVariable("x1", lowBound=0)
x2 = pulp.LpVariable("x2", lowBound=0)
prob += 3*x1 + 2*x2                       # 目标
prob += x1 + x2 <= 4                      # 约束1
prob += 2*x1 + x2 <= 5                    # 约束2
prob.solve()
print(x1.value(), x2.value(), pulp.value(prob.objective))
```
