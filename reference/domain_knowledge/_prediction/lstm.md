# 长短期记忆网络 (Long Short-Term Memory, LSTM)

> **一句话速记**：带门控单元的循环神经网络，用"记忆细胞 + 遗忘/输入/输出三门"缓解长序列梯度消失，捕捉长期依赖。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 数据量大（数千点以上）、非线性、含长期依赖的单变量或多变量时序（如负荷、销量、交通流量）。
  - 多变量输入预测（特征含天气、节假日、价格等外部变量，作为每步输入）。
  - 需要端到端建模、赛题不要求强可解释性的场景。
- **不适用场景**：
  - 小样本（几十点）——易过拟合，GM(1,1)/ARIMA/Prophet 更稳。
  - 需要给出系数解释与显著性检验（神经网络是黑箱）。
  - 极长依赖或并行序列建模（可考虑 Transformer，但赛题通常 LSTM 已够）。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：能学习复杂非线性与长期记忆、可扩展为多变量/多步输出、精度通常高于传统时序模型。
- **局限性**：黑箱不可解释、训练慢且需调参（层数/隐单元/学习率）、小样本易过拟合。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **构造监督样本**：用滑动窗口把序列切成 (前 $T$ 步 $\to$ 后 $h$ 步)，特征与标签分别标准化。
2. **搭模型**：`nn.LSTM` 堆叠隐层，接全连接输出层；回归用 MSE 损失。
3. **训练**：划分训练/验证集，早停（`patience`）防过拟合，Adam 优化。
4. **预测与反标准化**：对测试集滚动预测，把标准化逆变换还原，算 MAPE/RMSE。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
LSTM 门控单元（输入 $x_t$，隐状态 $h_{t-1}$，细胞状态 $c_{t-1}$）：
$$f_t = \sigma(W_f[h_{t-1}, x_t]+b_f),\quad i_t=\sigma(W_i[h_{t-1},x_t]+b_i),\quad o_t=\sigma(W_o[h_{t-1},x_t]+b_o)$$
$$\tilde c_t = \tanh(W_c[h_{t-1},x_t]+b_c),\quad c_t = f_t\odot c_{t-1} + i_t\odot \tilde c_t,\quad h_t = o_t\odot\tanh(c_t)$$

其中遗忘门 $f_t$ 决定丢弃多少旧记忆，输入门 $i_t$ 决定写入多少新信息，输出门 $o_t$ 决定输出多少。

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：PyTorch（也可用 Keras 的 LSTM 层，思路一致）
import torch, torch.nn as nn, numpy as np

def make_xy(series, T=10, h=1):      # 滑窗：前 T 步 -> 后 h 步
    X, y = [], []
    for i in range(len(series) - T - h + 1):
        X.append(series[i:i+T]); y.append(series[i+T:i+T+h])
    return torch.tensor(np.array(X), dtype=torch.float32), \
           torch.tensor(np.array(y), dtype=torch.float32)

class LSTMNet(nn.Module):
    def __init__(self, in_dim, hidden=64, out=1, n_layer=1):
        super().__init__()
        self.lstm = nn.LSTM(in_dim, hidden, n_layer, batch_first=True)
        self.fc = nn.Linear(hidden, out)
    def forward(self, x):
        out, _ = self.lstm(x)         # out: (batch, T, hidden)
        return self.fc(out[:, -1, :]) # 取最后一步隐状态接全连接

X, y = make_xy(...)                   # 先做标准化
model = LSTMNet(in_dim=X.shape[-1], hidden=64, out=y.shape[-1])
opt = torch.optim.Adam(model.parameters(), lr=1e-3)
loss_fn = nn.MSELoss()
for epoch in range(200):
    opt.zero_grad()
    loss = loss_fn(model(X), y)
    loss.backward(); opt.step()
    # 建议加验证集 + 早停，避免过拟合

model.eval()
with torch.no_grad():
    pred = model(X[-1:])              # 预测未来，反标准化后输出
```
