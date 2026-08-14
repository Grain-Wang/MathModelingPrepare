# 复杂网络 (Complex Network)

> **一句话速记**：用图论统计指标（中心性、社团、小世界/无标度特性）刻画真实网络的结构规律，支撑传播、鲁棒性与关键节点分析。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 社交网络信息/舆情传播：识别关键意见领袖（中心性）与信息扩散路径。
  - 交通/电网/互联网的鲁棒性评估：删除节点后网络连通性变化、关键枢纽识别。
  - 蛋白质互作、论文合作、产业链关联网络：社团检测与演化规律分析。
  - 传染病/谣言传播建模：结合 SIR 等传播模型，用网络结构预测传播规模。
- **不适用场景**：
  - 数据量巨大（上亿节点）时需分布式图计算（Spark GraphX 等），普通 networkx 内存受限。
  - 仅需两点间路径/流量时，直接用具象算法（最短路/最大流）而非笼统网络指标。
  - 网络无真实交互关系（凭相关性硬连边）时，结论易被噪声误导，需先做显著性检验。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 指标丰富、可解释性强，能定量回答"谁最关键""社区如何划分""是否小世界"。
  - 与传播动力学（SIR/阈值模型）天然结合，适合机理建模类赛题。
  - networkx 覆盖度/介数/聚类系数/社团检测等全套 API，实现成本低。
- **局限性**：
  - 多个指标结论可能矛盾，需综合权衡而非单一指标下结论。
  - 指标对网络构建方式（连边阈值、权重）敏感，鲁棒性需用重连边/扰动检验。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **构建网络**：确定节点与连边规则（共现、合作、交易、地理相邻），赋权与方向。
2. **基础统计**：节点数、边数、平均度、平均最短路径、直径、平均聚类系数、度分布。
3. **中心性分析**：度/介数/接近/特征向量/PageRank，识别关键节点并排序对比。
4. **社团检测与特性判定**：Louvain 或贪心模块度划分社团；计算模块度 Q、小世界系数 $\sigma$，判断网络类型。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
度分布（无标度网络的幂律特征）：
$$P(k) \sim k^{-\gamma}$$

介数中心性（节点 $v$ 位于多少条最短路中间）：
$$C_B(v) = \sum_{s\neq v\neq t} \frac{\sigma_{st}(v)}{\sigma_{st}}$$

聚类系数（节点局部三角密度）与模块度（社团划分质量）：
$$C_i = \frac{2E_i}{k_i(k_i-1)},\qquad Q = \frac{1}{2m}\sum_{ij}\left[A_{ij} - \frac{k_i k_j}{2m}\right]\delta(c_i, c_j)$$

小世界系数（相对随机网络，聚集高且平均路径短）：
$$\sigma = \frac{C / C_{rand}}{L / L_{rand}}$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
import networkx as nx
import numpy as np

# 1) 构建网络（示例：合作/共现网络，边权为共现次数）
G = nx.Graph()
G.add_weighted_edges_from([(0, 1, 3), (1, 2, 2), (2, 3, 4), (0, 3, 1), (3, 4, 2)])

# 2) 基础统计
n, m = G.number_of_nodes(), G.number_of_edges()
avg_deg = np.mean([d for _, d in G.degree()])
avg_cluster = nx.average_clustering(G)               # 平均聚类系数
try:
    avg_len = nx.average_shortest_path_length(G)     # 平均最短路径（需连通）
except nx.NetworkXError:
    avg_len = nx.average_shortest_path_length(G.subgraph(max(nx.connected_components(G), key=len)))

# 3) 中心性（识别关键节点）
deg_c   = nx.degree_centrality(G)                    # 度中心性
bet_c   = nx.betweenness_centrality(G)               # 介数中心性
clo_c   = nx.closeness_centrality(G)                 # 接近中心性
pr_c    = nx.pagerank(G)                             # PageRank（有向也可用）
eig_c   = nx.eigenvector_centrality_numpy(G)         # 特征向量中心性
key_node = max(bet_c, key=bet_c.get)

# 4) 社团检测与模块度（networkx >= 3.0）
from networkx.algorithms import community
part = community.louvain_communities(G, weight='weight')   # Louvain 划分
Q = community.modularity(G, part, weight='weight')          # 模块度
# 备选：community.greedy_modularity_communities(G)

# 5) 小世界性：与同规模随机图对比（用配置模型打乱后取期望）
import networkx as nx
C_rand = nx.average_clustering(nx.gnm_random_graph(n, m, seed=42))
L_rand = nx.average_shortest_path_length(nx.gnm_random_graph(n, m, seed=42))
sigma = (avg_cluster / C_rand) / (avg_len / L_rand)  # sigma > 1 提示小世界
```
