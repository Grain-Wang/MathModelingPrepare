# 最大流与最小费用流 (Max-Flow / Min-Cost Flow)

> **一句话速记**：把流量从源点送到汇点，在边容量约束下最大化总流量；若给每条边加单位费用，则求满足给定流量下的最小总费用。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 网络带宽/流量分配：通信网络中各链路容量已知，求两节点间的最大可传输速率。
  - 运输调度与二分图匹配：车辆、航班、工人与任务的分配问题（转化为源汇网络）。
  - 供水/供气/供电管网的能力评估：管道容量有限时系统最大输送量。
  - 最小费用流：物流网络以总费用最小为目标分配流量、带费用的运输平衡问题。
- **不适用场景**：
  - 流量需在节点停留、分时或存在多商品不同源汇时（多商品流），单源汇最大流不适用。
  - 边容量非线性、或要求整数流且算法未保整时需额外处理（Dinic 保整数性）。
  - 目标是最短路径而非吞吐量时，应改用最短路模型。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 有强对偶支撑：最大流值 = 最小割容量（Max-Flow Min-Cut），便于用割解释与证明上界。
  - 保整数性：容量为整数时最大流/最小费用流必存在整数最优解，天然适合离散分配。
  - 算法高效，Dinic 复杂度 $O(V^2 E)$，实际稀疏图远快于此；networkx/scipy 一键求解。
- **局限性**：
  - 只建模单源单汇；多源多汇需人为加超级源/超级汇。
  - 最小费用流的目标函数是线性费用，非线性或分段费用需改建模。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **建模成流网络**：确定源 $s$、汇 $t$、每条有向边容量 $c(e)$（及费用 $cost(e)$）；多源多汇则增设超级源汇。
2. **选算法**：仅求最大流用 Ford-Fulkerson（增广路）/ Dinic；带费用用连续最短路（SSP）或 network_simplex。
3. **求解**：得到最大流值、各边实际流量 $f(e)$（用于报告"哪条链路跑满/拥塞"）。
4. **割与敏感性分析**：用最小割找出瓶颈边，分析扩容哪条边能提升总流量。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
容量约束与流量守恒（对中间节点 $v \neq s,t$）：
$$\max \sum_{v} f(s,v)\quad \text{s.t.}\quad 0 \le f(e) \le c(e),\quad \sum_{(u,v)\in E} f(u,v) = \sum_{(v,w)\in E} f(v,w)$$

残量网络与增广：残量边 $c_f(u,v)=c(u,v)-f(u,v)$（正向）与 $c_f(v,u)=f(u,v)$（反向），沿残量网络找增广路并推送瓶颈流量。

最大流最小割定理：
$$\text{max-flow value} = \min_{S\ni s,\,t\notin S} \sum_{u\in S,\,v\notin S} c(u,v)$$

最小费用流目标：
$$\min \sum_{e} cost(e)\cdot f(e)\quad \text{s.t. 流量守恒且总流量} = F$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
import networkx as nx
from scipy.sparse.csgraph import maximum_flow

# 1) networkx：最大流（有向容量图）
G = nx.DiGraph()
G.add_edge('s', 'a', capacity=10); G.add_edge('s', 'b', capacity=5)
G.add_edge('a', 'b', capacity=3);  G.add_edge('a', 't', capacity=8)
G.add_edge('b', 't', capacity=7)
flow_value, flow_dict = nx.maximum_flow(G, 's', 't', capacity='capacity')
# flow_dict[u][v] 即该边实际流量，flow_value 为最大流值

# 2) 最小费用最大流 / 给定流量最小费用
G2 = nx.DiGraph()
G2.add_edge('s', 'a', capacity=10, weight=2)   # weight 为单位费用
G2.add_edge('a', 't', capacity=8,  weight=5)
G2.add_edge('s', 'b', capacity=5,  weight=3)
G2.add_edge('b', 't', capacity=7,  weight=1)
min_cost = nx.min_cost_flow_cost(G2)            # 在满足所有需求下最小费用
flow = nx.min_cost_flow(G2)                     # 得到各边流量分配

# 3) scipy：邻接矩阵最大流（稠密图）
import numpy as np
cap = nx.to_numpy_array(G, dtype=int)           # 容量矩阵（无自环）
val = maximum_flow(cap, 0, 3).flow_value        # source=0, sink=3

# 4) 最小割（瓶颈分析）：求源点可达的割集，说明扩容方向
cut_val, partition = nx.minimum_cut(G, 's', 't', capacity='capacity')
reachable, non_reachable = partition
```
