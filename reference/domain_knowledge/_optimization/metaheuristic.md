# 元启发式算法 (Metaheuristic: GA / SA / PSO / ACO)

> **一句话速记**：基于自然/物理直觉的随机搜索算法，不依赖梯度，适合黑箱、NP-hard、大规模离散或非凸问题，但只保证"足够好"而非最优。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - NP-hard 组合问题：TSP、车辆路径 VRP、作业调度、选址，精确求解器算不动时。
  - 黑箱/仿真优化：目标函数无解析形式、不可导或计算昂贵（如蒙特卡洛仿真）。
  - 非凸多峰问题：有大量局部最优，梯度法易陷入，需全局搜索。
- **不适用场景**：
  - 线性/凸且规模可控的问题——精确求解器（LP/MILP）更快更优。
  - 对最优性、可复现性有硬性要求，且时间充裕时（启发式无最优性保证）。
  - 单次评估极昂贵（如每次评估需数小时仿真），且无法并行时。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 通用性强，几乎任何目标（连续/离散/黑箱）都能套用，实现简单。
  - 天然并行（种群类算法），易扩展、易加约束惩罚、易与局部搜索混合。
  - 不依赖梯度信息，对不可导、含噪目标稳健。
- **局限性**：
  - 无最优性保证，参数（种群规模、变异率等）对结果影响大，需调参。
  - 随机性强，多次运行结果有波动，论文需报告多次统计（均值/方差/最优）。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 编码解：把决策变量映射为染色体/粒子/路径（连续实向量或离散序列）。
2. 定义适应度：目标函数+约束惩罚项，统一为最大化适应度。
3. 设计算子：交叉/变异（GA）、邻域扰动（SA）、速度更新（PSO）、信息素+启发式（ACO）。
4. 迭代与终止：达到最大代数/温度下限/收敛阈值后，输出历史最优解；多次运行取统计。

### 3.2 四种算法速记与区分 (Four Algorithms at a Glance)

| 算法 | 一句话要点 | 最佳场景 | 关键参数 |
|------|-----------|---------|---------|
| **GA 遗传算法** | 种群通过选择、交叉、变异进化，模拟"优胜劣汰" | 连续+离散混合、大规模组合 | 种群规模、交叉率、变异率 |
| **SA 模拟退火** | 以概率接受劣解（随"温度"下降收紧），跳出局部最优 | 单解迭代、路径/调度类 | 初始温度、降温系数、内循环次数 |
| **PSO 粒子群** | 粒子向自身历史最优与全局最优靠拢，更新速度与位置 | 连续变量、参数寻优 | 惯性权重、个体/全局学习因子 |
| **ACO 蚁群** | 信息素累积正反馈+启发式引导，构造路径 | TSP/VRP 等图路径问题 | 信息素蒸发率、启发式权重 |

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：deap（GA）、scipy.optimize.dual_annealing（SA）
import random
import numpy as np
from deap import base, creator, tools, algorithms

# --- 遗传算法 GA（最小化连续函数） ---
creator.create("FitnessMin", base.Fitness, weights=(-1.0,))  # 负号=最小化
creator.create("Individual", list, fitness=creator.FitnessMin)
toolbox = base.Toolbox()
toolbox.register("attr", random.uniform, -5, 5)             # 基因取值
toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr, n=3)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("evaluate", lambda ind: (sum(x**2 for x in ind),))  # 目标函数
toolbox.register("mate", tools.cxTwoPoint)
toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.2, indpb=0.2)
toolbox.register("select", tools.selTournament, tournsize=3)
pop = toolbox.population(n=100)
algorithms.eaSimple(pop, toolbox, cxpb=0.6, mutpb=0.2, ngen=100, verbose=False)
print(tools.selBest(pop, 1)[0])

# --- 模拟退火 SA（scipy 内置，适合连续黑箱） ---
from scipy.optimize import dual_annealing
res = dual_annealing(lambda x: sum(xi**2 for xi in x), bounds=[(-5,5)]*3)
print(res.x, res.fun)

# --- 粒子群 PSO：可用 pyswarm 库 pso(func, lb, ub)；思路为速度+位置迭代 ---
# --- 蚁群 ACO：手写信息素矩阵 + 轮盘赌选下一城市，常用于 TSP，可参考 python-tsp 库 ---
# 上述两类若无现成库，按"初始化->迭代更新(信息素/速度)->收敛"骨架手写即可。
```
