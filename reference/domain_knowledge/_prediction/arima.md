# 差分自回归移动平均模型 (ARIMA)

> **一句话速记**：对非平稳序列做 $d$ 阶差分变平稳，再用 AR($p$) 与 MA($q$) 组合建模单变量时序。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 单变量、无外部协变量的平稳化时序预测（如历史销量、客流量、股票/汇率短中期）。
  - 中短期点预测 + 置信区间（如"未来 12 期销量"类赛题）。
  - 样本量适中（几十点以上）、无明显强季节性（强季节需用 SARIMA 或 Holt-Winters）。
- **不适用场景**：
  - 需要引入多个外部解释变量（改用 ARIMAX / 回归 / LSTM）。
  - 强非线性、长期依赖或突变多（改用 LSTM/Prophet）。
  - 序列有明确周期但差分后仍不平稳（改用 SARIMA，加季节参数 $P,D,Q,s$）。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：模型结构透明可解释、参数少不易过拟合、能给出置信区间、statsmodels 一行实现。
- **局限性**：只适用单变量线性平稳结构、长期预测误差快速累积、定阶依赖人工判图经验。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **平稳性检验**：画时序图；用 ADF 检验，$p>0.05$ 则差分，重复直到平稳，差分次数即 $d$。
2. **定阶 $p,q$**：画平稳序列的 ACF（定 $q$）与 PACF（定 $p$）；或用 AIC/BIC 网格搜索自动定阶。
3. **拟合**：`ARIMA(endog, order=(p,d,q))`，检验残差是否为白噪声（Ljung-Box 检验）。
4. **预测与回代**：`forecast()` 输出预测值 + 置信区间，与测试集比对评估（RMSE/MAPE）。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
ARIMA($p,d,q$) 结构（对 $d$ 阶差分后序列 $y_t'$ 建模）：
$$y_t' = c + \sum_{i=1}^{p}\phi_i y_{t-i}' + \sum_{j=1}^{q}\theta_j \varepsilon_{t-j} + \varepsilon_t$$

用滞后算子 $B$ 的紧凑形式：
$$(1-\phi_1 B-\cdots-\phi_p B^p)(1-B)^d y_t = (1+\theta_1 B+\cdots+\theta_q B^q)\varepsilon_t$$

定阶经验法则（ACF/PACF 拖尾/截尾）：
- ACF 拖尾、PACF 在 $p$ 后截尾 $\Rightarrow$ AR($p$)
- PACF 拖尾、ACF 在 $q$ 后截尾 $\Rightarrow$ MA($q$)
- 两者都拖尾 $\Rightarrow$ ARMA，用 AIC 网格搜索

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：statsmodels（注：API 因版本而异，新版用 ARIMA，旧版用 ARIMA(endog, order=...)）
import pandas as pd, numpy as np
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.arima.model import ARIMA

ts = pd.Series(...)  # 单变量时序，等间隔，无缺失

# 1) 平稳性检验（ADF），不平稳则差分
d = 0
while adfuller(ts)[1] > 0.05 and d < 3:
    ts = ts.diff().dropna(); d += 1
print('d =', d)

# 2) 网格搜索定阶（用 AIC 最小）
import itertools
best = (0, d, 0, np.inf)
for p, q in itertools.product(range(0, 4), range(0, 4)):
    try:
        m = ARIMA(ts, order=(p, d, q)).fit()
        if m.aic < best[3]: best = (p, d, q, m.aic)
    except Exception: pass
print('best (p,d,q) =', best[:3])

# 3) 拟合 + 预测
model = ARIMA(ts, order=best[:3]).fit()
fc = model.get_forecast(steps=12)              # 未来 12 期
print(fc.predicted_mean)                       # 点预测
print(fc.conf_int())                           # 95% 置信区间
```
