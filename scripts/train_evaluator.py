"""训练并保存状态评估器。

用法：
    python3 scripts/train_evaluator.py [--games 300] [--seed 0] [--mix-greedy 0.5]

流程：self-play 采样 N 局 → 训练线性 + MLP 两种评估器 → 用验证集选优 →
保存到 advisor/weights.json（evaluate.py 会自动加载，替代手工权重）。
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from advisor import network
from advisor.sampling import collect_samples


def mse(model_params, X, y):
    errs = [(network.model_predict(model_params, x) - t) ** 2 for x, t in zip(X, y)]
    return sum(errs) / max(len(errs), 1)


def main():
    games = 300
    seed = 0
    mix_greedy = 0.5
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == "--games" and i + 1 < len(argv):
            games = int(argv[i + 1])
        elif a == "--seed" and i + 1 < len(argv):
            seed = int(argv[i + 1])
        elif a == "--mix-greedy" and i + 1 < len(argv):
            mix_greedy = float(argv[i + 1])

    print(f"采样 {games} 局 self-play 对局 (seed={seed}, greedy占比={mix_greedy}) ...")
    X, y = collect_samples(games, seed=seed, mix_greedy=mix_greedy)
    n = len(X)
    print(f"采集到 {n} 条样本，特征维度 {len(X[0])}，标签均值 {sum(y)/n:.3f}")
    assert n >= 50, "样本太少，请增大 --games"

    # 切训练/验证
    rng = random.Random(seed)
    idx = list(range(n))
    rng.shuffle(idx)
    cut = int(n * 0.85)
    tr, va = [idx[:cut], idx[cut:]]
    Xtr = [X[i] for i in tr]; ytr = [y[i] for i in tr]
    Xva = [X[i] for i in va]; yva = [y[i] for i in va]

    print("训练逻辑回归评估器 ...")
    lin = network.train_linear(Xtr, ytr, epochs=200, lr=0.5, seed=seed)
    m_lin = mse(lin, Xva, yva)
    print(f"  验证 MSE = {m_lin:.4f}")

    print("训练 MLP 评估器 (9->16->1) ...")
    mlp = network.train_mlp(Xtr, ytr, n_hidden=16, epochs=120, lr=0.1, batch=32, seed=seed)
    m_mlp = mse(mlp, Xva, yva)
    print(f"  验证 MSE = {m_mlp:.4f}")

    best = mlp if m_mlp <= m_lin else lin
    kind = best["kind"]
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "advisor", "weights.json")
    out = os.path.abspath(out)
    network.save_params(best, out)
    print(f"\n选优: {'MLP' if kind=='mlp' else '线性'} (MSE {min(m_mlp,m_lin):.4f})")
    print(f"已保存 -> {out}")
    print("启用方式： python3 run.py --model advisor/weights.json")
    print("注意：默认评估仍用启发式；训练模型有分布漂移风险，确认更优后再启用。删除该文件可清理。")


if __name__ == "__main__":
    main()
