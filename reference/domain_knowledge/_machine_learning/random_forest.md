# 随机森林 (Random Forest, RF)

> **一句话速记**：训练多棵决策树（每棵用自助采样 + 随机特征子集），用投票/平均集成，稳定且抗过拟合。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 表格数据的分类/回归"默认基线"：客户流失预测、信用违约、销量/房价回归。
  - 特征重要性排序与特征筛选：赛题里快速找出关键影响因素，辅助解释与建模。
  - 中小规模、混合类型特征、含缺失值的数据，无需太多预处理也能得到不错结果。
- **不适用场景**：
  - 超高维稀疏数据（如 TF-IDF 文本、One-Hot 高基数类别），树分裂效率低，XGBoost/线性模型更优。
  - 需要外推训练集取值范围的回归（树模型预测不会超出见过的目标区间）。
  - 对可解释性有硬性要求时，单棵浅决策树或逻辑回归更易向评委讲清因果。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 随机性（样本自助采样 + 特征随机子集）降低方差，几乎不用调参就有较好表现。
  - 天然支持分类与回归、无需标准化、能处理缺失与非线性关系。
  - 自带袋外（OOB）误差评估和特征重要性，省去单独划分验证集的成本。
- **局限性**：
  - 树多时内存与推理开销大，实时预测场景不如单树/线性模型轻量。
  - 对高基数类别特征、时序外推、极端稀疏数据效果一般；黑盒程度高于单棵树。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 数据划分：训练/测试切分；类别特征可 One-Hot 或 LabelEncoder（树模型对编码不敏感）。
2. 设定超参：`n_estimators`（树数量，宜大）、`max_depth`、`max_features`、`min_samples_leaf`。
3. 训练与调参：先用默认参数跑基线，再用随机/网格搜索调 `max_depth`、`max_features`。
4. 评估与解释：OOB 得分 / 交叉验证评估，`feature_importances_` 输出特征重要性排序。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
每棵树对自助采样集 $B_b$ 训练；回归取均值，分类取多数投票：

$$\hat{f}_{\text{RF}}(x)=\frac{1}{B}\sum_{b=1}^{B}\hat{f}_b(x), \qquad \hat{y}_{\text{class}}=\arg\max_c\sum_{b=1}^{B}\mathbb{1}\{\hat{f}_b(x)=c\}$$

特征重要性常用基于不纯度减少的度量（基尼重要性），对特征 $j$ 在所有节点分裂上的基尼下降量求和：

$$\text{Importance}(j)=\sum_{t:\,\text{split on } j}\Delta\text{Gini}(t)$$

袋外（OOB）误差用未参与该树训练的样本（约 36.8%）做无偏估计：

$$\text{OOB}=\frac{1}{n}\sum_{i}\mathcal{L}(y_i,\hat{f}_{\text{OOB}}(x_i))$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：scikit-learn
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import RandomizedSearchCV

# 分类：oob_score 直接利用袋外样本评估，无需另分验证集
rf = RandomForestClassifier(
    n_estimators=300,        # 树数量，越大越稳（边际收益递减）
    max_features='sqrt',     # 每次分裂随机选 sqrt(d) 个特征
    max_depth=None,          # 先不限制，再按 OOB 调
    min_samples_leaf=2,
    oob_score=True,
    random_state=42, n_jobs=-1
)
rf.fit(X_train, y_train)
print("OOB 准确率:", rf.oob_score_)

# 特征重要性排序（赛题中用于找关键影响因素）
import numpy as np
imp = np.argsort(rf.feature_importances_)[::-1]
print([(feature_names[i], rf.feature_importances_[i]) for i in imp[:10]])

# 回归版本
rfr = RandomForestRegressor(n_estimators=300, random_state=42, n_jobs=-1)
rfr.fit(X_train, y_train)

# 调参（分类与回归均可套用此范式）
param = {'max_depth': [5, 10, None], 'max_features': ['sqrt', 'log2', 0.3]}
search = RandomizedSearchCV(rf, param, cv=5, n_iter=10, scoring='roc_auc', random_state=42)
search.fit(X_train, y_train)
```
