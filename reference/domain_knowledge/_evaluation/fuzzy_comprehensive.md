# 模糊综合评价 (Fuzzy Comprehensive Evaluation, FCE)

> **一句话速记**：用隶属度代替"非此即彼"，把模糊定性评价量化成综合评分或等级。

## 1. 适用范围与典型场景 (When to use)
- **适用场景**：评价边界模糊、指标带主观定性成分的赛题（满意度、服务质量、环境质量、教学/医疗评价）；评价等级本身就是"优/良/中/差"这类语言变量；需要给出评价等级而非精确数值的场景。
- **不适用场景**：各指标有精确客观数据且希望精确排序时（用 TOPSIS）；隶属函数构造不当则主观性大；指标过多时模糊矩阵维度增大、权重分配困难。

## 2. 核心优势与局限性 (Pros & Cons)
- **优势**：能处理模糊、定性、不确定的评价信息；结果给出各等级隶属度，比单一得分信息更丰富；与 AHP 结合（权重）是经典组合，写起来有套路。
- **局限性**：隶属函数与合成算子选择主观，结果易被质疑；多等级隶属度接近时最大隶属度原则失真（需加权平均修正）；难以区分隶属度相近的对象。

## 3. 具体实施方法 (How to implement)
### 3.1 核心步骤 (Standard Workflow)
1. 确定因素集 $U=\{u_1,\dots,u_m\}$ 与评语集 $V=\{v_1,\dots,v_n\}$（等级）。
2. 确定权重向量 $A$（可用 AHP 或熵权法）。
3. 构造隶属度矩阵（模糊关系矩阵）$R$，每行是某因素对各等级的隶属度。
4. 模糊合成 $B = A \circ R$，按最大隶属度或加权平均定级。

### 3.2 核心公式/数学表达 (Mathematical Formulation)
模糊综合评价向量：

$$B = A \circ R = (a_1,\dots,a_m) \circ \begin{pmatrix} r_{11} & \cdots & r_{1n}\\ \vdots & & \vdots\\ r_{m1} & \cdots & r_{mn} \end{pmatrix}$$

常用合成算子：
- 加权平均型 $b_k = \sum_j a_j r_{jk}$（保留全部信息，最常用）；
- 主因素决定型 $b_k = \max_j \min(a_j, r_{jk})$。

若评语带分值 $S=(s_1,\dots,s_n)$，综合得分 $T = B\cdot S^T$。

### 3.3 Python 实战代码框架 (Code Snippet)
```python
# 推荐库：numpy（手写）
import numpy as np

def fce(A, R, op='weighted', S=None):
    """A: 权重向量 (m,)；R: 隶属度矩阵 (m,n) 行=因素, 列=评语等级"""
    if op == 'weighted':
        B = A @ R                        # 加权平均型
    else:                                # 主因素决定型
        B = np.max(np.minimum(A[:, None], R), axis=0)
    B = B / B.sum()                      # 归一化
    score = None
    if S is not None:                    # S: 各等级分值 (如 [90,75,60,45])
        score = float(B @ np.array(S))
    return B, score                      # B 为各等级隶属度, score 为综合得分
```
