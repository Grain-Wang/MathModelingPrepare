# Prophet 时间序列预测 (Facebook/Meta Prophet)

> **一句话速记**：把时序分解为"趋势 + 季节 + 节假日 + 噪声"的可加模型，自动处理缺失与异常，开箱即用。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 带强季节性与节假日效应的业务时序（如零售销量、网站流量、销售预测，含周末/促销/假期）。
  - 数据存在缺失、异常值或非等间隔时（Prophet 对时间戳不规则更鲁棒）。
  - 需要快速给出"趋势 + 季节 + 节假日"分量解释的赛题（可画分解图写结论）。
- **不适用场景**：
  - 需要引入大量外部回归特征做精细建模（Prophet 的外部回归器较简单）。
  - 高频数据（分/秒级）、强自相关或需概率分布的严格时序（改用 ARIMA/LSTM）。
  - 小样本（几十点）时趋势拟合可能过拟合，GM(1,1) 更稳。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：全自动、对缺失/异常/节假日稳健、参数直观易调、可给出不确定性区间（`yhat_lower/upper`）。
- **局限性**：对高频或强非线性趋势不够灵活、需将列名固定为 `ds`/`y`、节假日需人工建表。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **准备数据**：两列 DataFrame，`ds`（日期时间列）与 `y`（数值列）。
2. **构建节假日表**（可选）：`holidays` DataFrame，含 `holiday`、`ds` 列，提升节假日精度。
3. **拟合**：`Prophet(yearly_seasonality, weekly_seasonality, daily_seasonality, holidays)`，用 `.fit(df)`。
4. **预测与分解**：`make_future_dataframe(periods)` + `.predict()`；`plot_components` 看趋势/季节/节假日分量。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
Prophet 可加分解模型（$g$ 趋势、$s$ 季节、$h$ 节假日、$\epsilon$ 噪声）：
$$y(t) = g(t) + s(t) + h(t) + \varepsilon_t$$

分段线性趋势（含变点，$k$ 为增长率，$\delta$ 为变点处增长率调整，$\mathbf{1}$ 为指示函数）：
$$g(t) = \left(k + \boldsymbol{a}(t)^T\boldsymbol{\delta}\right)t + \left(m + \boldsymbol{a}(t)^T\boldsymbol{\gamma}\right)$$

季节项用傅里叶级数（$P$ 为周期，$N$ 为阶数）：
$$s(t) = \sum_{n=1}^{N}\left(a_n\cos\frac{2\pi n t}{P} + b_n\sin\frac{2\pi n t}{P}\right)$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：prophet（from prophet import Prophet）
import pandas as pd
from prophet import Prophet

df = pd.DataFrame({'ds': pd.date_range('2020-01-01', periods=48, freq='M'),
                   'y': [...]})  # 列名必须固定为 ds 和 y

# 可选：节假日表（提升假期预测精度）
holidays = pd.DataFrame({'holiday': ['春节'] * 3, 'ds': ['2020-01-25', '2021-02-12', '2022-02-01']})

m = Prophet(yearly_seasonality=True, weekly_seasonality=True,
            daily_seasonality=False, holidays=holidays,
            changepoint_prior_scale=0.05)  # 变点灵活度，越小趋势越平滑
m.fit(df)

future = m.make_future_dataframe(periods=12, freq='M')  # 未来 12 期
fc = m.predict(future)
print(fc[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(12))  # 点预测 + 区间

# 分量分解图（写论文用）
fig = m.plot_components(fc)   # 趋势 / 年季节 / 周季节 / 节假日
```
