# 旅行商问题 (Traveling Salesman Problem, TSP)

> **一句话速记**：求一条经过所有节点且只经过一次、最后回到起点的最短闭合回路（Hamilton 回路），是 NP 难的经典组合优化问题。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 快递/外卖/巡检路径规划：一辆车（或一名人员）遍历多个点后返回，最小化总里程。
  - 无人机或机器人巡检、电路板钻孔、激光切割的最短走刀路径。
  - 赛题中的"遍历型"配送、景点游览顺序规划（可扩展为带时间窗的 TSP-TW）。
- **不适用场景**：
  - 多辆车同时配送且各车载量受限，应升级为车辆路径问题（VRP/CVRP）。
  - 无需返回起点、只求一条遍历所有点的开路径，需用"最短 Hamilton 路径"变体。
  - 节点规模大（如数百上千点）且要求精确解时不可行，须用启发式/元启发式。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 模型简洁、可扩展性强（加时间窗、容量、优先级即得各类 VRP）。
  - 小规模（$n \le 20$ 左右）可用动态规划精确求解，结果可作为启发式的基准。
  - ortools 等求解器内建元启发式，数千点规模也能快速给出近似最优解。
- **局限性**：
  - NP 难：精确解复杂度指数级（Held-Karp $O(n^2 2^n)$），规模一大只能求近似。
  - 目标仅总里程，忽略时间窗、路况、满载率等，实际场景需额外约束。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **构建距离矩阵**：由坐标算欧氏距离，或直接用路网最短路填充 $d_{ij}$。
2. **选求解器**：$n$ 小用 DP/整数规划精确解；$n$ 大用 ortools 元启发式或 2-opt 局部搜索。
3. **求解**：得到访问顺序（闭环路径），输出总里程与路线图。
4. **改进与验证**：用 2-opt / Lin-Kernighan 局部优化消除交叉；必要时加对称性、时间窗等约束重解。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
整数规划（DFJ 消子回路）形式：
$$\min \sum_{i<j} d_{ij}x_{ij}\quad \text{s.t.}\ \sum_{j\neq i}x_{ij}=2\ (\forall i),\quad \sum_{i,j\in S,\,i<j}x_{ij}\le |S|-1\ (\forall\, S\subsetneq V, |S|\ge 3)$$

动态规划（Held-Karp，$x_{ij}\in\{0,1\}$，$S$ 为已访问点集）：
$$dp[S][j] = \min_{i\in S,\, i\neq j}\left\{dp[S\setminus\{j\}][i] + d_{ij}\right\},\quad \text{复杂度 } O(n^2 2^n)$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
import networkx as nx
import numpy as np
from scipy.spatial.distance import cdist

# 1) 距离矩阵（坐标点 -> 欧氏距离）
points = np.array([[0, 0], [1, 3], [4, 2], [5, 0], [2, 1]])
D = cdist(points, points)

# 2) 小规模精确解：Held-Karp 动态规划（O(n^2 2^n)，n<=20 可用）
def tsp_dp(D):
    n = D.shape[0]
    dp = {(1, 0): 0}                      # dp[(mask, last)] = 最短路径长
    for mask in range(1, 1 << n):
        for last in range(n):
            if not (mask >> last) & 1 or (mask, last) not in dp:
                continue
            for nxt in range(n):
                if not (mask >> nxt) & 1:
                    nm = (mask | (1 << nxt), nxt)
                    val = dp[(mask, last)] + D[last, nxt]
                    if val < dp.get(nm, np.inf):
                        dp[nm] = val
    return min(dp[( (1 << n) - 1, last)] + D[last, 0] for last in range(n))

# 3) 大规模近似：ortools 元启发式（数千点可解）
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
def tsp_ortools(D):
    n = D.shape[0]
    manager = pywrapcp.RoutingIndexManager(n, 1, 0)      # 1 辆车，起点 0
    routing = pywrapcp.RoutingModel(manager)
    def dist_cb(i, j):
        return int(D[manager.IndexToNode(i), manager.IndexToNode(j)] * 1000)
    idx = routing.RegisterTransitCallback(dist_cb)
    routing.SetArcCostEvaluatorOfAllVehicles(idx)
    search = routing.DefaultRoutingSearchParameters()
    search.local_search_metaheuristic = (routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search.time_limit.seconds = 30
    solution = routing.SolveWithParameters(search)
    route = [manager.IndexToNode(i) for i in range(n) if not routing.IsEnd(i)]
    return solution.ObjectiveValue() / 1000.0, route

# 4) networkx 快速近似（内置 Christofides，满足三角不等式时 <= 1.5 倍最优）
G = nx.complete_graph(len(points))
for i in range(len(points)):
    for j in range(i + 1, len(points)):
        G[i][j]['weight'] = D[i, j]
approx_route = nx.approximation.traveling_salesman_problem(G, cycle=True)
```
