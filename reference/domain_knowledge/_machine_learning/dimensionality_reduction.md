# 降维 (Dimensionality Reduction)

> **一句话速记**：把高维特征压缩到低维空间，保留主要信息（方差/结构），同时去冗余、降噪声、便于可视化。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 高维指标系统评价：几十上百个相关指标先降维，再做综合评价/回归，避免多重共线性。
  - 数据可视化：把高维样本投影到 2D/3D（PCA 或 t-SNE）做散点图、看聚类效果。
  - 表格数据预处理：特征去相关、降噪后喂给 K-Means、KNN 等对高维敏感的方法。
- **不适用场景**：
  - 需要保留每个原始特征的可解释业务含义时（PCA 主成分是特征线性组合，语义模糊）。
  - 数据几乎无冗余、各特征独立且都重要时，强行降维反而丢失信息。
  - t-SNE 仅用于可视化，其距离无绝对尺度、随机性强，不可作为后续距离度量的输入。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 消除多重共线性、降低噪声、减少过拟合，是赛题里"指标太多"的标准预处理手段。
  - 因子分析能给主成分赋予可解释的潜变量含义（如"消费能力因子""活跃度因子"）。
  - 降低维度后计算量与存储开销显著下降，KNN/K-Means 在高维下的性能得到改善。
- **局限性**：
  - 主成分不可直接解释，需结合载荷矩阵人工命名。
  - PCA 是线性方法，对非线性流形结构（如 Swiss roll）无能为力；t-SNE 非线性但计算慢且不可复现。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 标准化特征（PCA 对量纲敏感，务必先 `StandardScaler`）。
2. 确定保留成分数：看累计方差贡献率（如 ≥85%）、碎石图拐点或 Kaiser 准则（特征值 >1）。
3. 分解/降维：PCA 或因子分析，得到主成分得分与载荷矩阵。
4. 解释与后续：结合载荷命名因子，或将低维得分接入回归/聚类/可视化。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
PCA 对协方差矩阵做特征分解，取前 k 个最大特征值对应的特征向量：

$$\Sigma = \frac{1}{n-1}X^\top X = V\Lambda V^\top, \qquad Z_k = X V_k$$

第 $i$ 个主成分的方差贡献率为：

$$\text{贡献率}_i = \frac{\lambda_i}{\sum_{j=1}^{p}\lambda_j}$$

t-SNE 最小化高维分布 $P$ 与低维分布 $Q$ 间的 KL 散度（非线性、保局部邻域）：

$$C = \text{KL}(P\parallel Q) = \sum_{i\ne j} p_{ij}\log\frac{p_{ij}}{q_{ij}}$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：scikit-learn（FactorAnalysis 为因子分析；稀疏数据可用 TruncatedSVD）
from sklearn.decomposition import PCA, FactorAnalysis
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler

X_scaled = StandardScaler().fit_transform(X)

# PCA：保留累计方差贡献率 ≥ 90% 的主成分
pca = PCA(n_components=0.90)          # 按方差比例自动定成分数
Z = pca.fit_transform(X_scaled)
print("累计方差贡献率:", pca.explained_variance_ratio_.cumsum())
loadings = pca.components_            # 载荷矩阵，用于解释各成分

# 因子分析：指定因子个数，输出潜变量得分
fa = FactorAnalysis(n_components=3, random_state=42)
Z_fa = fa.fit_transform(X_scaled)

# t-SNE：仅用于 2D/3D 可视化，不用于距离度量/后续建模
Z_tsne = TSNE(n_components=2, perplexity=30, random_state=42).fit_transform(X_scaled)
```
