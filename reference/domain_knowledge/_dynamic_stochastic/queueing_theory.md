# 排队论 (Queueing Theory, M/M/1 等)

> **一句话速记**：用"到达率 $\lambda$ + 服务率 $\mu$"刻画排队系统，靠 Little 定律与生灭过程算出队长、等待时间等稳态指标。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：
  - 服务台/窗口优化：银行柜员、医院挂号、收费站、客服座席数配置。
  - 网络与通信：数据包排队时延、呼叫中心、任务调度（CPU/云计算）。
  - 排队拥堵治理：安检通道、景区排队、红绿灯/交叉口车流等待分析。
- **不适用场景**：
  - 到达或服务时间不符合泊松/指数假设（如强周期性、预约制到店），需改用一般分布 $G/G/s$ 或仿真。
  - 顾客行为复杂（中途离队、插队、批量到达）或服务台间高度耦合时，解析模型失效，宜用离散事件仿真。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：
  - 解析公式直接给出 $L, W, L_q, W_q$ 与忙期等指标，计算快、参数少。
  - 经典 $M/M/s$ 有封闭解，便于敏感性分析与服务台数寻优。
  - Little 定律 $L=\lambda W$ 普适性强，几乎任何稳态系统都成立。
- **局限性**：
  - 假设严格（泊松到达、指数服务、稳态、无限容量），现实常被违反。
  - 只给稳态均值，不刻画瞬时波动；非马尔可夫型系统需近似或仿真。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. **建模标识**：用 Kendall 记号 $A/B/s/K$ 描述系统（如 $M/M/1$、$M/M/c$、$M/G/1$）。
2. **定参数**：由数据估计到达率 $\lambda$、服务率 $\mu$（=1/平均服务时间），算交通强度 $\rho=\lambda/\mu$（多服务台为 $\lambda/(c\mu)$）。
3. **算指标**：套公式求队长 $L$、等待时间 $W$、排队长度 $L_q$、忙期等；校验 $\rho<1$ 保证稳定。
4. **优化**：调整服务台数 $c$ 或服务率，使成本/等待时间达到目标；复杂场景用 `simpy` 仿真验证。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
Little 定律（普适，稳态下成立）：

$$L = \lambda W,\quad L_q = \lambda W_q$$

$M/M/1$ 稳态指标（交通强度 $\rho=\lambda/\mu<1$）：

$$P_0 = 1-\rho,\quad L=\frac{\rho}{1-\rho}=\frac{\lambda}{\mu-\lambda},\quad W=\frac{1}{\mu-\lambda}$$

$M/M/c$ 稳态概率（$r=\lambda/\mu$，$c$ 为服务台数）：

$$P_0=\left[\sum_{k=0}^{c-1}\frac{r^k}{k!}+\frac{r^c}{c!(1-\rho)}\right]^{-1},\quad \rho=\frac{r}{c}$$

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：numpy（解析公式）、simpy（离散事件仿真）
import math

# M/M/1 解析计算
lam, mu = 4.0, 5.0          # 到达率、服务率
rho = lam / mu
assert rho < 1, "系统不稳定，rho 必须 < 1"
L = rho / (1 - rho)         # 平均队长
W = 1 / (mu - lam)          # 平均逗留时间
Lq = L - rho                # 平均排队长度
print(f"rho={rho:.2f}  L={L:.2f}  W={W:.2f}  Lq={Lq:.2f}")

# M/M/c 的 P0
def p0_mmc(lam, mu, c):
    r = lam / mu
    rho = r / c
    if rho >= 1:
        return None         # 不稳定
    s = sum(r**k / math.factorial(k) for k in range(c))
    s += r**c / (math.factorial(c) * (1 - rho))
    return 1 / s

# --- simpy 离散事件仿真（复杂排队场景，思路级示例）---
# 核心：env.process 生成到达流，resource 表示服务台，顾客请求/释放资源
# import simpy
# def customer(env, name, server):
#     with server.request() as req:
#         yield req                      # 排队等待服务台
#         yield env.timeout(service_time)  # 服务耗时
# env = simpy.Environment()
# server = simpy.Resource(env, capacity=3)  # 3 个服务台
# env.process(gen_arrivals(env, lam))       # 到达进程按指数间隔 env.timeout(...)
# env.run(until=1000)                       # 运行仿真后统计平均等待
```
