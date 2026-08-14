# 最短路径 (Shortest Path)

> **一句话速记**：在带权图上求两点（或单源到所有点、或任意两点间）边权和最小的路径，是大量图优化问题的底层子模块。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 物流配送、快递路由：已知各路段里程/耗时，求两点间最省时或最省成本的运输线路。
  - 交通网络（地铁/公交/公路）换乘与导航：站点为节点、换乘与行驶时间为边权。
  - 通信/管网敷设的最短链路、故障后网络重路由的最短备用路径。
  - 作为 TSP、最大流、选址问题（如 p-中心问题）的内层求解器反复调用。
- **不适用场景**：
  - 边权为负且存在负环时，Dijkstra 失效（须改用 Bellman-Ford 判定负环）。
  - 需要遍历多个节点（访问所有点）时，最短路径不是答案，应转为 TSP/VRP。
  - 边权随时间动态变化（时变网络）需改用时间依赖最短路径模型。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 算法成熟、复杂度低，Dijkstra 用堆优化后达 $O((V+E)\log V)$。
  - networkx / scipy 一行调用即可求解，工程落地快，结果精确（非启发式）。
  - 可灵活赋予边权不同物理含义（距离/时间/费用/风险），一张图多用。
- **局限性**：
  - 单源最短路只给出一条最短路径，多目标（时间+费用权衡）需改用多目标或分层建模。
  - 不能直接处理负权（Dijkstra）或大规模全源（Floyd $O(V^3)$ 内存与时间压力大）。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **建图**：确定节点（城市/路口/基站）与边权（距离、时间、费用），明确有向/无向。
2. **选算法**：单源正权用 Dijkstra；全源正权用 Floyd（或跑 V 次 Dijkstra）；含负权用 Bellman-Ford（可检测负环）。
3. **求解与还原路径**：用 predecessor 数组回溯得到具体节点序列。
4. **结果校验**：把路径边权加总与算法输出 dist 比对，并检查是否满足赛题附加约束（限速、禁行、必经点）。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
Dijkstra / Bellman-Ford 的松弛操作（核心）：
$$d[v] \leftarrow \min(d[v],\ d[u] + w(u,v))$$

Floyd 动态规划递推（$d_{ij}^{k}$ 表示仅允许经过前 $k$ 个中间节点时 $i\to j$ 的最短距离）：
$$d_{ij}^{k} = \min\left(d_{ij}^{k-1},\ d_{ik}^{k-1} + d_{kj}^{k-1}\right)$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
import networkx as nx
from scipy.sparse.csgraph import dijkstra, floyd_warshall

# 1) networkx：单源最短路 + 还原路径
G = nx.Graph()  # 无向带权图
G.add_weighted_edges_from([(0, 1, 4), (0, 2, 2), (1, 2, 1), (2, 3, 5), (1, 3, 3)])
dist = nx.dijkstra_path_length(G, 0, 3, weight='weight')   # 最短距离
path = nx.dijkstra_path(G, 0, 3, weight='weight')          # 具体节点序列
all_pair = dict(nx.all_pairs_dijkstra_path_length(G))       # 全源最短路

# 2) scipy：邻接矩阵批量求解（矩阵稠密时更快）
import numpy as np
adj = nx.to_numpy_array(G, weight='weight')                 # 转邻接矩阵
D, pred = dijkstra(adj, return_predecessors=True, directed=False)
FW = floyd_warshall(adj, directed=False)                    # 全源最短路矩阵

# 3) 负权/负环判定（networkx 内置 Bellman-Ford）
has_neg_cycle = nx.negative_edge_cycle(G, weight='weight')
if not has_neg_cycle:
    d = nx.bellman_ford_path_length(G, 0, 3, weight='weight')

# 4) 由 predecessor 还原路径（通用回溯思路）
def recover_path(pred, s, t):
    if pred[s, t] == -9999:  # scipy 用 -9999 表示无前驱
        return None
    path = [t]
    while path[-1] != s:
        path.append(int(pred[s, path[-1]]))
    return path[::-1]
```
