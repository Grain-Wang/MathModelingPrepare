# 整数规划 (Integer/0-1 Programming, IP)

> **一句话速记**：部分或全部决策变量必须取整数/0-1 的优化问题，常用分支定界或割平面求解，建模能力极强但规模敏感。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 选址/设施问题：在候选点中决定"建或不建"（0-1 变量），最小化总成本。
  - 排班/指派：人员、车辆、机器的整数分配，任务只能整体分配。
  - 背包与资源切割：装哪些物品、切几段原料，变量是"个数"而非连续量。
- **不适用场景**：
  - 变量可连续取值（用量、比例），直接用线性/非线性规划更高效。
  - 规模过大（变量/约束上百万）时，精确方法难收敛，需转启发式或松弛近似。
  - 约束高度非线性且离散时，MILP 求解器可能失效，可考虑元启发式。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 0-1 变量+线性约束可表达大量逻辑关系（如"选了 A 才能选 B"：$x_A \le x_B$）。
  - 现代求解器（Gurobi/CBC/SCIP）分支定界+割平面，中小规模精确求解。
  - 结果直接可执行（就是"选谁""装几件"），论文落地方便。
- **局限性**：
  - 属 NP-hard，规模增大求解时间爆炸式增长，需设时间上限取可行解。
  - 逻辑约束（大 M 法）引入会削弱松弛界，参数 $M$ 选不好影响效率。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 用 0-1 变量 $x_i \in \{0,1\}$ 表达"选/不选"，用整数变量表达"个数/批次"。
2. 用线性不等式表达逻辑与容量约束（大 M 法处理"若…则…"）。
3. 先解 LP 松弛，检验松弛解是否恰好整数（若整数则已最优）。
4. 调用 MILP 求解器，设 gap 阈值或时间上限，记录最优解与最优值。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
一般整数规划：
$$\min_{\mathbf{x}} \mathbf{c}^T\mathbf{x} \quad \text{s.t.} \quad A\mathbf{x} \le \mathbf{b}, \quad \mathbf{x} \in \mathbb{Z}^n$$

0-1 规划（选址/背包）：
$$\max \sum_{i} p_i x_i \quad \text{s.t.} \quad \sum_i w_i x_i \le W, \quad x_i \in \{0,1\}$$

逻辑约束示例（大 M 法）：若 $x=1$ 则必须满足 $a^T y \le b$，可写作
$$a^T y \le b + M(1-x)$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：PuLP（免费，调用 CBC）或 gurobipy（性能更强）
import pulp
prob = pulp.LpProblem("knapsack", pulp.LpMaximize)
x = pulp.LpVariable.dicts("x", range(5), cat=pulp.LpBinary)   # 0-1 变量
p = [10, 15, 8, 20, 12]      # 价值
w = [3, 5, 2, 7, 4]          # 重量
prob += pulp.lpSum(p[i]*x[i] for i in range(5))               # 目标
prob += pulp.lpSum(w[i]*x[i] for i in range(5)) <= 10         # 容量约束
prob.solve()
print([i for i in range(5) if x[i].value() > 0.5])  # 选中的物品

# gurobipy 等价写法（需安装 gurobipy，建模风格一致）
# import gurobipy as gp
# m = gp.Model(); xv = m.addVars(5, vtype=gp.GRB.BINARY)
# m.setObjective(gp.quicksum(p[i]*xv[i] for i in range(5)), gp.GRB.MAXIMIZE)
# m.addConstr(gp.quicksum(w[i]*xv[i] for i in range(5)) <= 10)
# m.optimize(); print([i for i in range(5) if xv[i].X > 0.5])
```
