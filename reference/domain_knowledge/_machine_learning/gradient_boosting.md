# 梯度提升 (Gradient Boosting / XGBoost / LightGBM)

> **一句话速记**：串行训练弱学习器（浅树），每棵新树拟合前面模型的残差/负梯度，逐步逼近真实目标。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 表格数据建模竞赛（国赛/美赛数据题）的"天花板模型"：结构化数据分类/回归首选。
  - 风控、销量预测、故障诊断等需高精度且特征以数值/类别为主的场景。
  - 特征规模大、样本量大时，LightGBM 的直方图算法与 leaf-wise 生长可显著提速。
- **不适用场景**：
  - 样本极少（<几百条）时容易过拟合，正则/早停也难救，逻辑回归或浅树更稳。
  - 高维稀疏特征（如词袋文本）效果通常不如线性模型；时序外推能力受限。
  - 需要极强的全局可解释性或严格单调约束时，需额外处理（SHAP 或加单调约束）。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 精度高、正则化好（含 L1/L2、早停、子采样），是结构化数据竞赛的主流选择。
  - 原生支持缺失值、类别特征（LightGBM）、并行/直方图加速，工程性能强。
  - 通过 SHAP / `feature_importances_` 能给出较可靠的特征重要性。
- **局限性**：
  - 超参数多且敏感（学习率、树数、深度、子采样），调参成本高。
  - 串行训练不易并行到极致，训练比随机森林慢；对噪声/离群点需谨慎。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 数据准备：划分训练/验证集（用于早停），XGBoost 需对类别编码，LightGBM 可直接用 `category` 类型。
2. 设定核心超参：`learning_rate`（小值 0.01–0.1）、`n_estimators`、`max_depth`、`subsample`、`colsample_bytree`。
3. 早停训练：监控验证集指标，`early_stopping_rounds` 防止过拟合。
4. 评估与解释：验证集 AUC/RMSE，输出特征重要性或 SHAP 值解释关键特征。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
加法模型逐步累加弱学习器，第 $t$ 轮预测为：

$$\hat{y}_i^{(t)} = \hat{y}_i^{(t-1)} + \eta\, f_t(x_i)$$

XGBoost 的目标函数 = 损失 + 正则（叶节点权重与数量惩罚），并做二阶泰勒展开：

$$\mathcal{L}^{(t)} \approx \sum_{i}\left[g_i f_t(x_i)+\frac{1}{2}h_i f_t^2(x_i)\right] + \gamma T + \frac{1}{2}\lambda\sum_{j}w_j^2$$

其中 $g_i=\partial_{\hat{y}}\ell(y_i,\hat{y}_i^{(t-1)})$、$h_i=\partial^2_{\hat{y}}\ell(y_i,\hat{y}_i^{(t-1)})$ 为损失的一阶、二阶梯度。

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：xgboost / lightgbm
import xgboost as xgb
import lightgbm as lgb

# XGBoost：早停防过拟合
dtrain = xgb.DMatrix(X_train, label=y_train)
dvalid = xgb.DMatrix(X_valid, label=y_valid)
params = {
    'objective': 'binary:logistic',   # 回归用 'reg:squarederror'
    'learning_rate': 0.05,
    'max_depth': 6,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'eval_metric': 'auc',
    'seed': 42,
}
bst = xgb.train(params, dtrain, num_boost_round=1000,
                evals=[(dvalid, 'valid')], early_stopping_rounds=50)
y_prob = bst.predict(dvalid)

# LightGBM：原生支持类别特征，直接传 categorical_feature
lgbm = lgb.LGBMClassifier(
    learning_rate=0.05, n_estimators=1000, max_depth=-1,
    num_leaves=31, subsample=0.8, colsample_bytree=0.8,
    random_state=42, n_jobs=-1
)
lgbm.fit(X_train, y_train, eval_set=[(X_valid, y_valid)],
         eval_metric='auc', callbacks=[lgb.early_stopping(50)])
y_prob = lgbm.predict_proba(X_valid)[:, 1]
```
