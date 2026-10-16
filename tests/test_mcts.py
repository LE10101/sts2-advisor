"""核心逻辑单元测试：状态解析、动作生成、模拟推进、MCTS 收敛。"""
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from advisor.client import OfflineClient, _sample_combat_snapshot
from advisor.model import CombatState, Action
from advisor.simulator import (
    legal_actions, apply_action, enemy_turn, is_terminal, terminal_score, rollout,
)
from advisor.mcts import MCTS
from advisor.policy import greedy_policy


def make_state() -> CombatState:
    return CombatState.from_snapshot(_sample_combat_snapshot())


def test_parse_snapshot():
    s = make_state()
    assert s.player_hp == 62
    assert s.max_hp == 80
    assert s.energy == 3
    assert len(s.hand) == 5
    assert len(s.enemies) == 2
    assert all(e.alive for e in s.enemies)
    print("PASS parse_snapshot")


def test_legal_actions():
    s = make_state()
    acts = legal_actions(s)
    # 5 张牌：3 张攻击(各 2 目标) + 1 防御(无目标) + 1 结束回合 等
    assert len(acts) >= 4
    assert any(a.kind == "end_turn" for a in acts)
    # 所有出牌成本不超能量
    for a in acts:
        if a.kind == "play_card":
            c = next(x for x in s.hand if x.hand_index == a.hand_index)
            assert c.cost <= s.energy
    print("PASS legal_actions")


def test_apply_action():
    s = make_state()
    rng = random.Random(1)
    # 打 0 号牌（打击，伤害8+力量2=10）
    dmg_card = next(c for c in s.hand if c.name == "打击")
    target = s.enemies[0].id
    before_hp = s.enemies[0].hp
    ns = apply_action(s, Action.play(dmg_card.hand_index, target), rng)
    assert ns is not None
    assert ns.energy == s.energy - dmg_card.cost
    assert len(ns.hand) == len(s.hand) - 1
    # 伤害应结算到敌人（扣除格挡0）
    assert ns.enemies[0].hp < before_hp
    print("PASS apply_action")


def test_enemy_turn_and_terminal():
    s = make_state()
    rng = random.Random(2)
    # 给玩家施加大量易伤+清空敌人，验证敌人攻击扣血
    before = s.player_hp
    s.player_buffs["易伤"] = 5
    ns = enemy_turn(s, rng)
    assert ns.turn == s.turn + 1
    assert ns.player_block == 0
    assert ns.energy == 3
    assert ns.player_hp <= before  # 敌人至少一个 attack 意图
    assert is_terminal(ns) is False
    print("PASS enemy_turn")


def test_rollout_range():
    s = make_state()
    rng = random.Random(3)
    v = rollout(s, rng)
    assert 0.0 <= v <= 1.0
    print(f"PASS rollout_range value={v:.3f}")


def test_mcts_converges():
    s = make_state()
    mcts = MCTS(default_policy=greedy_policy, seed=7)
    root = mcts.search(s, iterations=300)
    ranked = mcts.ranked_actions(root)
    assert ranked, "应有推荐动作"
    # 平均收益应单调不增（已排序）
    avgs = [a for _, a, _ in ranked]
    assert all(avgs[i] >= avgs[i + 1] for i in range(len(avgs) - 1))
    best = mcts.best_action(root)
    assert best is not None
    print("PASS mcts_converges")
    print("  最佳动作:", best.describe(s))
    for action, avg, visits in ranked[:4]:
        print(f"    {action.describe(s):30s} avg={avg:.3f} visits={visits}")


if __name__ == "__main__":
    test_parse_snapshot()
    test_legal_actions()
    test_apply_action()
    test_enemy_turn_and_terminal()
    test_rollout_range()
    test_mcts_converges()
    print("\n全部测试通过 ✓")
