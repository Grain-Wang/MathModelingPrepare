# 聚类分析 (Clustering)

> **一句话速记**：无监督地把样本按"相似度"自动分组，使得组内尽量相似、组间尽量不同。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 客户/用户分群（消费行为、RFM 特征画像），为后续差异化策略打标签。
  - 无标签数据的探索性分析：先聚类发现隐含结构，再对每类做统计或解释。
  - 异常/离群点检测（DBSCAN 把噪声点标为 -1），如故障样本、欺诈交易初步筛查。
- **不适用场景**：
  - 已有明确标签、要预测新样本类别的监督任务——应改用分类而非聚类。
  - 特征量纲差异巨大且未做标准化时，距离度量被大尺度特征主导，聚类结果不可信。
  - 数据分布呈流形/非凸形状却强行用 K-Means（此时 DBSCAN 或谱聚类更合适）。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 无需标签，可直接在原始数据上挖掘结构，赛题里常用于"无标签分组"第一步。
  - K-Means 实现简单、速度快，适合大规模数据的快速粗分组。
  - DBSCAN 能自动识别任意形状簇并剔除噪声点，层次聚类能给出树状层次结构便于解释。
- **局限性**：
  - 聚类结果好坏缺乏"真值"评价，簇数选择主观，需结合肘部法则/轮廓系数反复验证。
  - K-Means 对初始中心敏感、需预设 k、对离群点敏感；距离定义对结果影响大。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 特征工程与标准化：缺失值处理 + 连续特征 `StandardScaler` 归一化（量纲统一）。
2. 确定簇数 k：用肘部法则（SSE 随 k 下降的拐点）与轮廓系数（Silhouette）综合判断。
3. 运行聚类：K-Means / 层次聚类 / DBSCAN 按数据特性选择算法。
4. 结果解释：对每簇计算特征均值画像，可视化降维（PCA/t-SNE 后散点）验证分组合理性。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
K-Means 最小化组内平方和（SSE），迭代更新簇中心与样本归属：

$$\min_{C,\mu} \sum_{i=1}^{k}\sum_{x\in C_i}\lVert x-\mu_i\rVert^2, \qquad \mu_i=\frac{1}{|C_i|}\sum_{x\in C_i}x$$

轮廓系数衡量聚类紧凑度与分离度，取值 $[-1,1]$，越接近 1 越好：

$$s(i)=\frac{b(i)-a(i)}{\max\{a(i),b(i)\}}$$

其中 $a(i)$ 为样本 $i$ 到同簇其他点的平均距离，$b(i)$ 为到最近其他簇的平均距离。DBSCAN 依赖邻域参数：$\epsilon$（半径）与 `min_samples`（最小点数），密度可达的点构成簇。

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：scikit-learn
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN
from sklearn.metrics import silhouette_score

X_scaled = StandardScaler().fit_transform(X)  # 标准化，量纲统一

# 1) K-Means：肘部法则选 k
sse = []
for k in range(2, 11):
    sse.append(KMeans(n_clusters=k, n_init=10, random_state=42)
               .fit(X_scaled).inertia_)          # inertia_ 即 SSE

km = KMeans(n_clusters=4, n_init=10, random_state=42)
labels = km.fit_predict(X_scaled)

# 2) 层次聚类：无需预设簇数，看树状图切割
hc = AgglomerativeClustering(n_clusters=4, linkage='ward')
labels_hc = hc.fit_predict(X_scaled)

# 3) DBSCAN：自动找任意形状簇，噪声点标为 -1
db = DBSCAN(eps=0.5, min_samples=5)   # eps 可按 k-distance 图选取
labels_db = db.fit_predict(X_scaled)

# 评价：轮廓系数（DBSCAN 需剔除噪声点 -1 再算）
score = silhouette_score(X_scaled, labels)
```
