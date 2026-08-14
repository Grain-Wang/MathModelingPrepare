# 分类方法 (Classification)

> **一句话速记**：给定带标签样本学习一个判别规则，把新样本划分到有限个离散类别之一。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 二分类赛题：故障/正常识别、欺诈交易检测、患病/未患病判别、违约/未违约预测。
  - 多分类赛题：图像/文本类别识别、客户流失等级、产品质量等级评定。
  - 作为集成模型（随机森林、XGBoost）的基学习器：逻辑回归、决策树常作基准模型或组件。
- **不适用场景**：
  - 目标变量是连续数值（如销量、价格预测）——应改用回归而非分类。
  - 类别严重不平衡且未做采样/加权处理时，直接分类会偏向多数类。
  - 逻辑回归假设特征与 log-odds 线性相关；非线性边界需特征变换或换用树/核方法。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 逻辑回归输出可解释的概率、系数带符号与显著性，易向评委解释"为何这样分"。
  - KNN 无需训练、原理直观，小样本低维数据上手快。
  - 决策树可解释（可视化规则）、天然处理非线性与混合类型特征。
- **局限性**：
  - 逻辑回归对线性假设敏感，需手动构造交互项/多项式项。
  - KNN 对量纲、距离度量、k 值敏感，高维与大数据时查询慢、易受维度灾难影响。
  - 决策树易过拟合，需剪枝或集成（随机森林/提升树）来稳定。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 数据划分与预处理：训练/验证/测试切分，标准化（KNN、逻辑回归必需），编码类别特征。
2. 处理不平衡：`class_weight='balanced'` 或 SMOTE 过采样，用 AUC/F1 而非准确率评估。
3. 建模与调参：网格/随机搜索调 `C`（逻辑回归）、`k`（KNN）、`max_depth`（决策树）。
4. 评估与解释：交叉验证看泛化，输出混淆矩阵、ROC-AUC、特征重要性/系数。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
逻辑回归用 Sigmoid 函数将线性组合映射为概率：

$$P(y=1\mid x)=\sigma(w^\top x+b)=\frac{1}{1+e^{-(w^\top x+b)}}$$

通过最大化对数似然（等价最小化交叉熵损失）训练：

$$\ell(w)=-\sum_{i}\left[y_i\log p_i+(1-y_i)\log(1-p_i)\right]$$

KNN 用多数投票，k 个最近邻中类别 $c$ 的条件概率估计为：

$$P(y=c\mid x)=\frac{1}{k}\sum_{j\in N_k(x)}\mathbb{1}\{y_j=c\}$$

决策树按信息增益/基尼系数递归分裂。基尼不纯度：

$$\text{Gini}(D)=1-\sum_{c}p_c^2$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：scikit-learn
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2,
                                                    stratify=y, random_state=42)

# 逻辑回归：标准化 + 不平衡加权 + 调正则强度 C
pipe_lr = Pipeline([
    ('scaler', StandardScaler()),
    ('lr', LogisticRegression(class_weight='balanced', max_iter=1000))
])
pipe_lr.fit(X_train, y_train)

# KNN：标准化后调 k
pipe_knn = Pipeline([
    ('scaler', StandardScaler()),
    ('knn', KNeighborsClassifier())
])
grid = GridSearchCV(pipe_knn, {'knn__n_neighbors': [3, 5, 7, 9]}, cv=5)
grid.fit(X_train, y_train)

# 决策树：限制深度防过拟合
dt = DecisionTreeClassifier(max_depth=5, min_samples_leaf=10, random_state=42)
dt.fit(X_train, y_train)

# 评估：类别不平衡时优先看 AUC / F1，而非 accuracy
from sklearn.metrics import roc_auc_score, f1_score
y_prob = pipe_lr.predict_proba(X_test)[:, 1]
print(roc_auc_score(y_test, y_prob), f1_score(y_test, pipe_lr.predict(X_test)))
```
