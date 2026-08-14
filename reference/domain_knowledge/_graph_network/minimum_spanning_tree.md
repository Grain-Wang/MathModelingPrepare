# 最小生成树 (Minimum Spanning Tree, MST)

> **一句话速记**：用总边权最小的 $n-1$ 条边把 $n$ 个节点连通成一棵树，是"低成本连通全网"的基础模型。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 电网/通信网/管网初建：以最小敷设成本连通所有站点（光缆、管道、电线杆选址）。
  - 供水供气管网的树状布局优化、局域网最小布线成本。
  - 聚类预处理：用 MST 的边权分布做单链接层次聚类的依据。
  - 作为近似算法的子步骤（如某些 TSP 近似解、Steiner 树问题的基础）。
- **不适用场景**：
  - 要求任意两点间路径短（MST 只保证连通，不保证最短路径，需另建最短路）。
  - 存在冗余容灾要求（网络需环路备份）时，树结构不满足可靠性约束。
  - 边权为负不影响正确性，但若要求"最大生成树"需对边权取负后求解。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - Kruskal $O(E\log E)$、Prim $O((V+E)\log V)$，规模友好，实现极简。
  - 结果唯一性由边权决定，理论成熟（割性质、交换性质），易于证明与解释。
  - networkx / scipy 直接给出树边集合，方便画图与进一步分析。
- **局限性**：
  - 只优化总成本，忽略连通后的网络性能（延迟、拥塞、直径），需多目标扩展。
  - 树结构单点故障即断网，实际工程常需加少量冗余边（需额外建模）。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **建图**：节点为待连通站点，边权为两站间建设/敷设成本（距离×单位造价）。
2. **选算法**：稀疏图用 Kruskal（边排序+并查集），稠密图用 Prim（按点贪心扩展）。
3. **求解**：得到 MST 的边集合与总权值，即最小建设总成本。
4. **后处理与敏感性**：分析哪些边是关键边（去掉后 MST 变重/不连通），考虑加冗余边或约束（如 Steiner 中间节点）。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
目标函数（总边权最小）：
$$\min_{T} \sum_{e \in T} w(e)\quad \text{s.t. } T \text{ 是连通 } V \text{ 的树（} n-1 \text{ 条边，无环）}$$

割性质（Kruskal/Prim 正确性根基）：对任意割 $(S, V\setminus S)$，跨割的最小权边必属于某个 MST。

Prim 贪心选择（从已选点集 $S$ 扩展）：
$$e^{*} = \arg\min_{u\in S,\, v\notin S} w(u,v)$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
import networkx as nx
from scipy.sparse.csgraph import minimum_spanning_tree

# 1) networkx：最小生成树（可指定算法）
G = nx.Graph()
G.add_weighted_edges_from([(0, 1, 4), (0, 2, 2), (1, 2, 1), (2, 3, 5), (1, 3, 3)])
T = nx.minimum_spanning_tree(G, algorithm='kruskal')   # 或 'prim' / 'boruvka'
total_cost = T.size(weight='weight')                    # MST 总权值
mst_edges = sorted(T.edges(data=True))                  # 选中的边集合

# 2) scipy：邻接矩阵求 MST（返回稀疏矩阵，非零项即树边）
import numpy as np
adj = nx.to_numpy_array(G, weight='weight')
T_sp = minimum_spanning_tree(adj)                       # 稀疏矩阵
rows, cols = T_sp.nonzero()                             # 树边端点
costs = T_sp.data                                       # 对应边权

# 3) 敏感性：删除某条 MST 边后，重连两子图的最小代价
def edge_importance(G, T):
    imp = {}
    for u, v in T.edges():
        w = G[u][v]['weight']
        T_ = T.copy(); T_.remove_edge(u, v)
        # 找到跨两个连通分量的最轻非树边（次小生成树的关键步骤）
        comp = list(nx.connected_components(T_))
        imp[(u, v)] = w  # 占位：实际需枚举跨分量边求最小替代代价
    return imp
```
