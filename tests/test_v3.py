"""V3 测试：状态评估器（特征/单调性）+ 支配剪枝（正确性/效果）+ 收敛。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from advisor.model import CombatState, Enemy
from advisor.evaluate import evaluate_state, state_features
from advisor.prune import prune_actions, TARGET_KEEP
from advisor.simulator import legal_actions
from advisor.mcts import MCTS
from advisor.policy import greedy_policy
from advisor.cli import _silent_combat_snapshot


def _state() -> CombatState:
    return CombatState.from_snapshot(_silent_combat_snapshot())


def test_features():
    s = _state()
    f = state_features(s)
    assert len(f) == len([0.32, 0.26, -0.22, 0.07, 0.10, 0.05, 0.04, 0.03, -0.05])
    assert 0.0 <= f[0] <= 1.0  # HP占比
    assert 0.0 <= f[1] <= 1.0  # 敌削弱
    assert 0.0 <= f[2] <= 1.0  # 威胁
    print(f"PASS features f={[round(x,2) for x in f]}")


def test_monotonic():
    from advisor.evaluate import DEFAULT_WEIGHTS
    s = _state()
    base = evaluate_state(s, weights=DEFAULT_WEIGHTS)
    # HP 越高分越高
    s_high = s.copy(); s_high.player_hp = s.max_hp
    assert evaluate_state(s_high, weights=DEFAULT_WEIGHTS) >= base
    # 威胁越高分越低
    s_threat = s.copy()
    for e in s_threat.enemies:
        e.intent = "attack"; e.intent_value = 100
    assert evaluate_state(s_threat, weights=DEFAULT_WEIGHTS) <= base
    # 敌人削弱越多分越高
    s_weak = s.copy()
    for e in s_weak.enemies:
        e.hp = 1
    assert evaluate_state(s_weak, weights=DEFAULT_WEIGHTS) >= base
    # 终局精确
    s_die = s.copy(); s_die.player_hp = 0
    s_win = s.copy(); s_win.enemies = []
    assert evaluate_state(s_die) == 0.0
    assert evaluate_state(s_win) == 1.0
    print(f"PASS monotonic base={base:.3f}")


def test_learned_model():
    """训练好 weights.json 时，评估器应自动加载模型且输出在 [0,1]，终局仍精确。"""
    from advisor.evaluate import _learned_model
    m = _learned_model()
    s = _state()
    if m is not None:
        v = evaluate_state(s)
        assert 0.0 <= v <= 1.0, v
        s_die = s.copy(); s_die.player_hp = 0
        s_win = s.copy(); s_win.enemies = []
        assert evaluate_state(s_die) == 0.0 and evaluate_state(s_win) == 1.0
        print(f"PASS learned_model kind={m.get('kind')} 预测={v:.3f}")
    else:
        print("SKIP learned_model (无 weights.json)")


def test_prune_correctness():
    s = _state()
    raw = legal_actions(s)  # 已带剪枝
    # end_turn 保留
    assert any(a.kind == "end_turn" for a in raw)
    # 每张牌的目标候选不超过 TARGET_KEEP
    from collections import Counter
    cnt = Counter(a.hand_index for a in raw if a.kind == "play_card")
    for hi, c in cnt.items():
        # 无目标牌算1个；有目标的 ≤ TARGET_KEEP
        card = next(x for x in s.hand if x.hand_index == hi)
        no_tgt = any(a.target_id is None for a in raw if a.kind == "play_card" and a.hand_index == hi)
        if no_tgt:
            assert c == 1, (hi, c)
        else:
            assert c <= TARGET_KEEP, (hi, c)
    # 同名牌同目标无重复
    seen = set()
    for a in raw:
        if a.kind == "play_card":
            key = (a.hand_index, a.target_id)
            assert key not in seen, key
            seen.add(key)
    print(f"PASS prune_correctness 剪枝后候选数={len(raw)}")


def test_prune_reduction():
    """对比剪枝前后候选动作数：4 敌人场景下每张攻击牌目标从 4 裁剪到 ≤TARGET_KEEP。"""
    from advisor.model import Card
    from advisor.cards import effects_for_card
    s = _state()
    # 加到 4 个敌人（确保候选数 > PRUNE_MIN，触发剪枝）
    for k in range(3, 7):
        s.enemies.append(Enemy(id=k, name="邪教徒", hp=45, max_hp=45, block=0,
                               intent="attack", intent_value=11, buffs={}))
    # 构造未剪枝动作
    raw_actions = []
    for card in s.hand:
        if card.cost > s.energy:
            continue
        ef = effects_for_card(card)
        if ef.aoe or (ef.damage <= 0 and ef.poison <= 0):
            raw_actions.append(type("A", (), {"kind": "play_card", "hand_index": card.hand_index,
                                              "target_id": None})())
        else:
            for e in s.enemies:
                raw_actions.append(type("A", (), {"kind": "play_card", "hand_index": card.hand_index,
                                                  "target_id": e.id})())
    raw_actions.append(type("A", (), {"kind": "end_turn"}))
    pruned = prune_actions(s, raw_actions)
    assert len(raw_actions) > len(pruned), f"期望剪枝生效: 原始{len(raw_actions)} 剪后{len(pruned)}"
    ratio = len(pruned) / max(len(raw_actions), 1)
    print(f"PASS prune_reduction 原始={len(raw_actions)} 剪枝后={len(pruned)} 保留率={ratio:.2f}")


def test_mcts_converges_v3():
    s = _state()
    mcts = MCTS(default_policy=greedy_policy, seed=7)
    t0 = time.time()
    root = mcts.search(s, iterations=300)
    dt = time.time() - t0
    ranked = mcts.ranked_actions(root)
    assert ranked
    best = mcts.best_action(root)
    assert best is not None
    print(f"PASS mcts_v3 best={best.describe(s)} (300次迭代 {dt:.2f}s)")
    for a, avg, v in ranked[:3]:
        print(f"    {a.describe(s):28s} avg={avg:.3f} visits={v}")


if __name__ == "__main__":
    test_features()
    test_monotonic()
    test_learned_model()
    test_prune_correctness()
    test_prune_reduction()
    test_mcts_converges_v3()
    print("\nV3 全部测试通过 ✓")
