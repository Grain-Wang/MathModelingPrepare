# 回归分析 (Regression Analysis)

> **一句话速记**：用自变量线性（或经变换）组合拟合因变量，是解释性最强的预测基线方法。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 影响因素明确的预测（如房价 = 面积/地段/房龄；销量 = 价格/广告/季节）。
  - 需要给出"哪个因素影响最大、影响方向如何"的解释型赛题（如美赛评价/政策题）。
  - 数据量不大（几十到几百条）、变量关系近似线性的场景。
- **不适用场景**：
  - 时间序列强自相关（相邻样本不独立）时，OLS 估计有偏，应改用 ARIMA/LSTM。
  - 强非线性关系且无法通过特征变换线性化（改用树模型或神经网络）。
  - 多重共线性严重、样本数远小于变量数（改用岭回归/LASSO）。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：可解释性强（回归系数 = 边际效应）、计算快、可检验显著性（$t$ 检验/$F$ 检验）、便于写"政策建议"。
- **局限性**：对异常值敏感、对非线性与交互项需手工构造特征、无法自动捕捉时序记忆。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **数据清洗**：处理缺失值与异常值，特征标准化（对正则化回归必须）。
2. **特征工程**：构造交互项、多项式项、对数变换（缓解异方差与偏态）。
3. **拟合与选择**：OLS 起步，看 $R^2$ 与系数显著性；共线性/过拟合时换 Ridge/Lasso。
4. **诊断与验证**：残差正态性、异方差、多重共线性（VIF>10 报警）；交叉验证评估泛化。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
多元线性回归目标（最小二乘）：
$$\hat{\beta} = \arg\min_{\beta} \|y - X\beta\|_2^2 \;\Rightarrow\; \hat{\beta}=(X^TX)^{-1}X^Ty$$

岭回归（加 $L_2$ 惩罚，缓解共线性）：
$$\hat{\beta}_{ridge} = \arg\min_{\beta} \|y - X\beta\|_2^2 + \lambda\|\beta\|_2^2$$

逻辑回归（二分类，$p=P(y=1|x)$）：
$$\log\frac{p}{1-p} = x^T\beta \;\Rightarrow\; p = \frac{1}{1+e^{-x^T\beta}}$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：scikit-learn + statsmodels
import numpy as np, pandas as pd
from sklearn.linear_model import LinearRegression, Ridge, LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm  # 用于显著性检验/系数 p 值

X = pd.DataFrame(...); y = ...

# 1) OLS + 显著性检验（写论文用 statsmodels）
Xc = sm.add_constant(X)              # 加截距项
ols = sm.OLS(y, Xc).fit()
print(ols.summary())                 # 看系数、p 值、R^2、F 检验

# 2) 岭回归（共线性/高维时）
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
sc = StandardScaler().fit(Xtr)       # 正则化前必须标准化
ridge = Ridge(alpha=1.0).fit(sc.transform(Xtr), ytr)
print(ridge.score(sc.transform(Xte), yte))  # 测试集 R^2

# 3) 逻辑回归（分类赛题，如"是否违约"）
clf = LogisticRegression(C=1.0, max_iter=1000).fit(Xtr, ytr)
print(clf.predict_proba(Xte)[:, 1])  # 输出正类概率
```
