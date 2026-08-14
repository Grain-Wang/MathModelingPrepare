# 支持向量机 (Support Vector Machine, SVM)

> **一句话速记**：找一个使两类样本间隔（margin）最大的超平面，用核函数把线性不可分映射到高维可分。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 中小样本、特征数较多甚至接近样本数的分类（如基因/谱数据、文本 TF-IDF 分类）。
  - 二分类边界清晰的赛题：故障 vs 正常、垃圾/正常邮件、良/恶性判别。
  - 核技巧（RBF/多项式核）处理非线性边界，样本不大时精度优秀。
- **不适用场景**：
  - 超大样本量（>10 万级），SVM 训练复杂度高、耗时长，宜改用线性模型或提升树。
  - 类别严重不平衡且未加权时，决策面偏向多数类；需 `class_weight='balanced'`。
  - 特征远多于样本且含大量噪声时，线性 SVM 尚可，RBF 核易过拟合。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 结构风险最小化 + 间隔最大化，泛化能力好，小样本高维下尤其出色。
  - 核技巧无需显式构造高维映射，可高效处理非线性问题；线性核可解释权重方向。
  - 支持向量只由少数关键样本决定，对多数远离边界的样本不敏感。
- **局限性**：
  - 对核函数与超参（C、γ）极其敏感，需交叉验证细调。
  - 不直接输出概率（需 `probability=True` 额外拟合）、训练与内存在大数据下代价高。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 数据预处理：标准化特征（RBF 核对量纲极敏感，务必 `StandardScaler`），处理不平衡。
2. 选择核函数：线性核（高维/文本）或 RBF 核（非线性、特征少），网格搜索调参。
3. 调参：用 `GridSearchCV` 搜 `C`（间隔与误分类权衡）和 `gamma`（RBF 影响半径）。
4. 评估与解释：交叉验证看 AUC/准确率，用 `support_vectors_`、决策函数分析关键样本。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
硬间隔最大化原始问题：

$$\min_{w,b}\frac{1}{2}\lVert w\rVert^2 \quad \text{s.t.} \quad y_i(w^\top x_i+b)\ge 1$$

引入松弛变量 $\xi_i$ 得到软间隔，容忍少量误分类（C 控制权衡）：

$$\min_{w,b,\xi}\frac{1}{2}\lVert w\rVert^2 + C\sum_{i}\xi_i \quad \text{s.t.} \quad y_i(w^\top x_i+b)\ge 1-\xi_i,\ \xi_i\ge 0$$

核函数隐式计算高维内积，避免显式映射。RBF 核：

$$K(x,x')=\exp\left(-\gamma\lVert x-x'\rVert^2\right)$$

对偶问题只涉及核内积，决策函数：

$$f(x)=\text{sign}\left(\sum_{i}\alpha_i y_i K(x_i,x)+b\right)$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：scikit-learn
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline

# RBF 核：必须先标准化，网格搜 C 与 gamma
pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('svc', SVC(class_weight='balanced', probability=True, random_state=42))
])
param = {
    'svc__C': [0.1, 1, 10, 100],
    'svc__gamma': ['scale', 'auto', 0.01, 0.1, 1],  # gamma 越大边界越复杂
    'svc__kernel': ['rbf'],                          # 线性数据可试 'linear'
}
grid = GridSearchCV(pipe, param, cv=5, scoring='roc_auc', n_jobs=-1)
grid.fit(X_train, y_train)

print(grid.best_params_)
y_prob = grid.predict_proba(X_test)[:, 1]   # probability=True 时可用
y_pred = grid.predict(X_test)

# 线性核：高维文本/稀疏特征直接用，可看权重解释
svc_lin = SVC(kernel='linear', C=1.0, class_weight='balanced')
svc_lin.fit(StandardScaler().fit_transform(X_train), y_train)
print("权重向量 w:", svc_lin.coef_)          # 线性核下可解释各特征贡献
```
