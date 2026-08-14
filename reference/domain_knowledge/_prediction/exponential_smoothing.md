# 指数平滑与 Holt-Winters (Exponential Smoothing)

> **一句话速记**：对历史观测做指数衰减加权（越近越重），分别估计水平、趋势、季节三个分量来外推。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 带明显趋势与季节性周期的业务时序（如月销量、季度客流、节假日用电量）。
  - 需要快速、稳健、可解释的基线预测，样本点中等到较多。
  - 简单指数平滑（SES）适合无趋势无季节的平稳序列；Holt 适合有趋势；Holt-Winters 适合趋势+季节。
- **不适用场景**：
  - 需要引入外部协变量（广告、天气）——改用回归/ARIMAX。
  - 突变、节假日效应复杂或多周期叠加（改用 Prophet 或机器学习）。
  - 数据有强自相关且要求严格统计推断（可用 ARIMA 对比）。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：实现简单、参数少（3 个平滑系数）、对近端变化敏感、天然处理趋势+季节。
- **局限性**：本质是加权移动平均，长期外推能力弱、周期长度需事先设定、对突变滞后。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **判断分量**：画时序图确定是否有趋势、季节，选择 SES / Holt / Holt-Winters。
2. **设定周期 $m$**：如月度数据 $m=12$，季度 $m=4$；选加法（季节幅度恒定）或乘法（季节幅度随水平放大）季节。
3. **拟合**：statsmodels 中 `ExponentialSmoothing` 用 `trend`、`seasonal`、`seasonal_periods` 指定，可让 `initialization_method='estimated'` 自动估计初值。
4. **预测与评估**：`forecast(steps)` 输出未来值，用 MAPE/RMSE 与 ARIMA、Prophet 对比。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
Holt-Winters 三参数（水平 $\ell_t$、趋势 $b_t$、季节 $s_t$，加法季节为例，$m$ 为周期）：
$$\ell_t = \alpha(y_t - s_{t-m}) + (1-\alpha)(\ell_{t-1}+b_{t-1})$$
$$b_t = \beta(\ell_t-\ell_{t-1}) + (1-\beta)b_{t-1}$$
$$s_t = \gamma(y_t-\ell_{t-1}-b_{t-1}) + (1-\gamma)s_{t-m}$$

向前 $h$ 步预测：
$$\hat y_{t+h} = \ell_t + h\,b_t + s_{t+h-m\lceil h/m\rceil}$$

三个平滑系数：$\alpha$（水平）、$\beta$（趋势）、$\gamma$（季节），均在 $[0,1]$。

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：statsmodels（新版用 statsmodels.tsa.holtwinters，API 随版本略有差异）
import pandas as pd, numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing

ts = pd.Series(...)  # 等间隔时序，最好已有 2 个以上完整季节周期

# 1) 简单指数平滑（无趋势无季节）
ses = ExponentialSmoothing(ts, trend=None, seasonal=None,
                           initialization_method='estimated').fit()
# 2) Holt 线性趋势（无季节）
holt = ExponentialSmoothing(ts, trend='add', seasonal=None).fit()
# 3) Holt-Winters 加法季节（季节幅度恒定）
hw_add = ExponentialSmoothing(ts, trend='add', seasonal='add',
                              seasonal_periods=12).fit()
# 乘法季节（季节幅度随水平放大，适合销量随基数增长）
hw_mul = ExponentialSmoothing(ts, trend='add', seasonal='mul',
                              seasonal_periods=12).fit()

fc = hw_add.forecast(12)   # 未来 12 期
print(fc)
print('alpha,beta,gamma =', hw_add.params)  # 查看平滑系数（命名因版本而异）
```
