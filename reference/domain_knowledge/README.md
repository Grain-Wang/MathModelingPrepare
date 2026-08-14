# 数学建模主流方法知识库

面向「华为杯 / 国赛 / 美赛」的即插即用方法库。每个方法一个独立 Markdown，按六大类分子目录存放，统一模板（适用范围 → 优劣 → 步骤/公式/代码），实战导向。

## 目录结构

```
domain_knowledge/
├── README.md                 ← 本索引（全局导航 + 场景速查）
├── _optimization/            优化与规划模型（6）
├── _evaluation/              评价与决策模型（6）
├── _prediction/              预测与时间序列模型（6）
├── _graph_network/           图论与网络模型（5）
├── _machine_learning/        机器学习与数据挖掘（6）
└── _dynamic_stochastic/      动态与随机模型（5）
```

## 一、按大类导航

### 📐 `_optimization/` 优化与规划
- [线性规划](_optimization/linear_programming.md) — 目标与约束均线性的最优化
- [非线性规划](_optimization/nonlinear_programming.md) — 目标/约束含非线性项的数值优化
- [整数规划](_optimization/integer_programming.md) — 决策变量取整数/0-1 的分支定界
- [动态规划](_optimization/dynamic_programming.md) — 多阶段决策的最优子结构递推
- [多目标优化](_optimization/multi_objective.md) — 多冲突目标的 Pareto 前沿
- [元启发式算法](_optimization/metaheuristic.md) — GA/SA/PSO/ACO 求解 NP 难问题

### ⚖️ `_evaluation/` 评价与决策
- [层次分析法 AHP](_evaluation/ahp.md) — 层次分解 + 两两比较求权重
- [熵权法](_evaluation/entropy_weight.md) — 信息熵定客观权重
- [TOPSIS](_evaluation/topsis.md) — 与正负理想解距离排序
- [模糊综合评价](_evaluation/fuzzy_comprehensive.md) — 隶属度 + 模糊算子综合评价
- [数据包络分析 DEA](_evaluation/dea.md) — 多投入多产出相对效率
- [灰色关联分析](_evaluation/grey_relational.md) — 序列几何相似度衡量关联

### 📈 `_prediction/` 预测与时间序列
- [回归分析](_prediction/regression.md) — 线性/多元/岭/逻辑回归
- [ARIMA](_prediction/arima.md) — 差分平稳后自回归移动平均
- [灰色预测 GM(1,1)](_prediction/grey_prediction.md) — 小样本贫信息序列预测
- [指数平滑 Holt-Winters](_prediction/exponential_smoothing.md) — 平滑 + 趋势 + 季节
- [LSTM](_prediction/lstm.md) — 长短期记忆网络序列预测
- [Prophet](_prediction/prophet.md) — 趋势/季节/假日加法分解

### 🕸️ `_graph_network/` 图论与网络
- [最短路径](_graph_network/shortest_path.md) — Dijkstra/Floyd/Bellman-Ford
- [最大流](_graph_network/max_flow.md) — 容量约束下最大流量/最小费用流
- [最小生成树](_graph_network/minimum_spanning_tree.md) — Kruskal/Prim
- [旅行商问题 TSP](_graph_network/tsp.md) — 遍历所有点的最短回路
- [复杂网络](_graph_network/complex_network.md) — 中心性/社团/小世界

### 🤖 `_machine_learning/` 机器学习与数据挖掘
- [聚类分析](_machine_learning/clustering.md) — K-Means/层次/DBSCAN
- [分类方法](_machine_learning/classification.md) — 逻辑回归/KNN/决策树
- [降维](_machine_learning/dimensionality_reduction.md) — PCA/因子分析/t-SNE
- [随机森林](_machine_learning/random_forest.md) — 集成决策树
- [梯度提升](_machine_learning/gradient_boosting.md) — XGBoost/LightGBM
- [支持向量机 SVM](_machine_learning/svm.md) — 最大间隔分类/回归

### 🎲 `_dynamic_stochastic/` 动态与随机
- [微分方程](_dynamic_stochastic/differential_equations.md) — ODE/PDE 连续动态系统
- [马尔可夫链](_dynamic_stochastic/markov_chain.md) — 状态转移随机过程
- [蒙特卡洛模拟](_dynamic_stochastic/monte_carlo.md) — 随机采样求期望/概率
- [排队论](_dynamic_stochastic/queueing_theory.md) — 服务系统等待/队列分析
- [元胞自动机](_dynamic_stochastic/cellular_automata.md) — 局部规则演化复杂系统

## 二、场景 → 方法速查

拿到题目，先判断「要做什么」，再对号入座：

| 你要解决什么 | 首选方法 | 备选/补充 |
|---|---|---|
| 多指标综合打分、排名、选优 | TOPSIS / AHP / 熵权法 | 模糊综合评价、灰色关联、组合赋权 |
| 评价相对效率（多投入多产出） | DEA | 随机前沿 SFA |
| 预测未来数值/趋势 | 回归 / ARIMA | 指数平滑、灰色预测、LSTM、Prophet |
| 小样本、贫信息预测 | 灰色预测 GM(1,1) | 指数平滑 |
| 资源分配、生产排程（线性） | 线性规划 / 整数规划 | 0-1 规划、多目标优化 |
| 多阶段/序列决策 | 动态规划 | 强化学习 |
| 多个冲突目标同时优化 | 多目标优化 | 加权求和、ε 约束、NSGA-II |
| NP 难组合优化（无精确解） | 元启发式（GA/SA/PSO/ACO） | TSP 专用启发式 |
| 路径、配送、连通、流分配 | 最短路径 / 最大流 / MST | TSP、复杂网络 |
| 社交/传播/交通网络结构 | 复杂网络 | 图论基础 |
| 分类、识别、故障/欺诈判定 | 随机森林 / SVM / 梯度提升 | 逻辑回归、KNN、LSTM |
| 无标签数据分组、客户分群 | 聚类分析 | 降维后再聚类 |
| 高维指标压缩、特征提取 | PCA / 因子分析 | t-SNE（可视化） |
| 连续动态演化（种群/传染/物理） | 微分方程 | 元胞自动机 |
| 状态转移概率预测 | 马尔可夫链 | 隐马尔可夫 HMM |
| 风险评估、概率模拟、灵敏度 | 蒙特卡洛 | 方差缩减技巧 |
| 服务台数、排队等待优化 | 排队论 | 离散事件仿真 SimPy |

## 三、使用约定

1. **先查大类再进文件**：每个方法文件第一行有一句话速记，先扫一遍确定方向。
2. **代码为框架级**：`3.3 Python 实战代码框架` 给出的是核心 API 调用 + 注释，落地时按赛题数据补全。
3. **公式为最核心 1-3 条**：完整推导请回到教材或对应方法文件引用文献，此处只抓关键。
4. **方法可组合**：多数赛题需要「评价 + 预测」或「优化 + 仿真」组合，不要死守单一方法。
5. **文件只读**：本目录是知识参考，建模产物仍写入 `projects/02_modeling/`，勿在此改动。
