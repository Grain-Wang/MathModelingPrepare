# 元胞自动机 (Cellular Automata, CA)

> **一句话速记**：把空间离散成格子，每个格子按"自身+邻居的局部规则"同步更新状态，宏观复杂现象（扩散、传播、拥堵）从微观交互中涌现。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 疏散/交通流模拟：行人疏散、车流 Nagel-Schreckenberg 模型、火灾/烟雾蔓延。
  - 传染扩散与生态：流行病在二维空间传播、森林火灾、种群扩散、城市化扩张。
  - 晶格模型与演化博弈：相变、意见传播、舆情扩散、沙堆自组织。
- **不适用场景**：
  - 空间连续、需要精确几何或连续场描述的物理问题（改用 PDE/有限元）。
  - 全局规则占主导、个体局部交互不重要时（直接用宏观微分方程更高效）。
  - 需精确标定、结果对规则/时间步高度敏感时，CA 结论偏定性，需谨慎外推。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **离散化空间与状态**：定义网格（一维/二维）、邻域（von Neumann 四邻域 / Moore 八邻域）、状态集合。
2. **定义局部演化规则**：写出"新状态 = f(自身状态, 邻居状态)"的显式规则表（如 Conway 生命游戏、传播阈值）。
3. **设定初值与边界**：初始分布（人群位置、火源、车流密度）、边界条件（周期/吸收/固定）。
4. **同步迭代**：每个时间步所有格点同时更新，记录宏观量（密度、蔓延面积、疏散时间）并可视化。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
通用演化规则（离散时间、离散空间、同步更新）：

$$s_i^{t+1} = f\left(s_i^{t},\ \sum_{j\in \mathcal{N}(i)} s_j^{t}\right)$$

Moore 邻域（八邻域，常用作邻居定义）：

$$\mathcal{N}(i) = \{j: \|x_j - x_i\|_{\infty} \le 1,\ j \ne i\}$$

二维传播模型（如森林火灾：$s\in\{0空,1树,2火\}$，$p$ 为着火概率）：

$$s_i^{t+1} = \begin{cases} 2, & s_i^t=1 \text{ 且 } \exists j\in\mathcal{N}(i), s_j^t=2 \ (\text{以概率 } p)\\ s_i^t, & \text{否则}\end{cases}$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：numpy（向量化网格更新）、matplotlib（可视化）
import numpy as np
import matplotlib.pyplot as plt

# Conway 生命游戏（状态：0死 1活，Moore 邻域，B3/S23 规则）
def life_step(G):
    # 用 np.roll 计算 8 邻域活邻居数（向量化，比逐格循环快）
    N = sum(np.roll(np.roll(G, i, 0), j, 1)
            for i in (-1, 0, 1) for j in (-1, 0, 1) if (i, j) != (0, 0))
    # B3/S23：3 个邻居出生；2 或 3 个邻居存活
    return ((N == 3) | ((G == 1) & (N == 2))).astype(np.int8)

rng = np.random.default_rng(0)
grid = (rng.random((100, 100)) < 0.25).astype(np.int8)  # 随机初始

for _ in range(200):
    grid = life_step(grid)

plt.imshow(grid, cmap='binary'); plt.show()

# 森林火灾蔓延：状态 0空 1树 2火，火以概率 p 点燃 Moore 邻居中的树
def fire_step(G, p=0.3, rng=np.random):
    fire = (G == 2)
    neigh_burn = sum(np.roll(np.roll(fire, i, 0), j, 1)
                     for i in (-1, 0, 1) for j in (-1, 0, 1) if (i, j) != (0, 0))
    ignite = (G == 1) & (neigh_burn > 0) & (rng.random(G.shape) < p)
    out = G.copy()
    out[G == 2] = 0        # 火烧过变为空
    out[ignite] = 2        # 被点燃
    return out
```
