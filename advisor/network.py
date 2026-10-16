"""轻量 MLP 评估网络：纯 Python 实现，无第三方依赖。

用途：作为战斗状态评估器（输入 state_features 的 9 维特征，输出 [0,1] 期望胜率）。
支持两种形态（存入同一 weights.json）：
- "linear"：权重 + 偏置（逻辑回归），训练快、可解释，覆盖 evaluate.DEFAULT_WEIGHTS。
- "mlp"  : 单隐层 MLP（sizes，如 [9,16,1]），隐层 tanh、输出 sigmoid，更强。

纯 Python 手写前向/反向，数据量小（数千~几万样本）时训练秒级完成。
若环境有 numpy 可选加速（未安装则自动回退纯 Python）。
"""

from __future__ import annotations

import json
import math
import os
import random
from typing import List, Optional, Sequence

try:
    import numpy as np  # type: ignore
    _HAS_NUMPY = True
except Exception:  # pragma: no cover
    _HAS_NUMPY = False


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


class MLP:
    """单隐层 MLP：[n_in] -> [n_hidden] -> [1]。"""

    def __init__(self, n_in: int, n_hidden: int = 16, seed: Optional[int] = None):
        rng = random.Random(seed)
        s = 1.0 / math.sqrt(n_in)
        self.W1 = [[rng.uniform(-s, s) for _ in range(n_hidden)] for _ in range(n_in)]
        self.b1 = [0.0] * n_hidden
        s2 = 1.0 / math.sqrt(n_hidden)
        self.W2 = [rng.uniform(-s2, s2) for _ in range(n_hidden)]
        self.b2 = 0.0

    def predict(self, x: Sequence[float]) -> float:
        """前向，返回 [0,1]。"""
        h = [math.tanh(sum(x[j] * self.W1[j][k] for j in range(len(x))) + self.b1[k])
             for k in range(len(self.b1))]
        return sigmoid(sum(h[k] * self.W2[k] for k in range(len(h))) + self.b2)


def train_linear(X, y, epochs=200, lr=0.5, seed=0) -> dict:
    """逻辑回归训练（线性评估器），返回权重+偏置。"""
    n = len(X)
    d = len(X[0])
    rng = random.Random(seed)
    w = [rng.uniform(-0.05, 0.05) for _ in range(d)]
    b = 0.0
    for _ in range(epochs):
        for i in range(n):
            pred = sigmoid(sum(w[j] * X[i][j] for j in range(d)) + b)
            err = pred - y[i]
            g = err * pred * (1 - pred)
            for j in range(d):
                w[j] -= lr * g * X[i][j]
            b -= lr * g
    return {"kind": "linear", "weights": w, "bias": b}


def train_mlp(X, y, n_hidden=16, epochs=120, lr=0.1, batch=32, seed=0) -> dict:
    """单隐层 MLP 训练（回归到 [0,1] 胜率）。返回可序列化的参数字典。"""
    n = len(X)
    d = len(X[0])
    model = MLP(d, n_hidden, seed=seed)
    rng = random.Random(seed + 1)
    idx = list(range(n))
    for _ in range(epochs):
        rng.shuffle(idx)
        for start in range(0, n, batch):
            bi = idx[start:start + batch]
            dw1 = [[0.0] * n_hidden for _ in range(d)]
            db1 = [0.0] * n_hidden
            dw2 = [0.0] * n_hidden
            db2 = 0.0
            for i in bi:
                x = X[i]
                z1 = [sum(x[j] * model.W1[j][k] for j in range(d)) + model.b1[k] for k in range(n_hidden)]
                h = [math.tanh(v) for v in z1]
                pred = sigmoid(sum(h[k] * model.W2[k] for k in range(n_hidden)) + model.b2)
                err = pred - y[i]
                # 输出层
                delta2 = err * pred * (1 - pred)
                db2 += delta2
                for k in range(n_hidden):
                    dw2[k] += delta2 * h[k]
                # 隐层
                for k in range(n_hidden):
                    dk = delta2 * model.W2[k] * (1 - h[k] * h[k])
                    db1[k] += dk
                    for j in range(d):
                        dw1[j][k] += dk * x[j]
            m = max(len(bi), 1)
            for k in range(n_hidden):
                model.b1[k] -= lr * db1[k] / m
                model.W2[k] -= lr * dw2[k] / m
                for j in range(d):
                    model.W1[j][k] -= lr * dw1[j][k] / m
            model.b2 -= lr * db2 / m
    return {"kind": "mlp", "n_in": d, "n_hidden": n_hidden,
            "W1": model.W1, "b1": model.b1, "W2": model.W2, "b2": model.b2}


def model_predict(params: dict, x: Sequence[float]) -> float:
    """对序列化参数做前向预测。"""
    if params.get("kind") == "linear":
        w = params["weights"]
        b = params.get("bias", 0.0)
        return sigmoid(sum(w[j] * x[j] for j in range(len(w))) + b)
    z1 = [sum(x[j] * params["W1"][j][k] for j in range(len(x))) + params["b1"][k]
          for k in range(len(params["b1"]))]
    h = [math.tanh(v) for v in z1]
    return sigmoid(sum(h[k] * params["W2"][k] for k in range(len(h))) + params["b2"])


def save_params(params: dict, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(params, f)


def load_params(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
