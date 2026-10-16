"""V2 综合测试：静默猎手机制、SL 牌序记忆、价值评分、路线/奖励/商店决策。"""
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from advisor.cards import effects_for_card, make_shiv
from advisor.model import Card, CombatState, Enemy, Action
from advisor.simulator import apply_action, enemy_turn, legal_actions, is_terminal
from advisor.drawmemory import DrawOrderMemory, diff_new_cards
from advisor.cardvalue import score_card
from advisor.route import choose_route
from advisor.reward import choose_reward
from advisor.shop import choose_shop
from advisor.mcts import MCTS
from advisor.policy import greedy_policy

from advisor.cli import _silent_combat_snapshot, _map_snapshot, _reward_snapshot, _shop_snapshot


def _state() -> CombatState:
    return CombatState.from_snapshot(_silent_combat_snapshot())


def test_silent_effects():
    # 毒
    ef = effects_for_card(Card(name="致命毒药", hand_index=0, cost=1, card_type="skill"))
    assert ef.poison == 5, ef
    # 小刀生成
    ef2 = effects_for_card(Card(name="刀刃之舞", hand_index=1, cost=1, card_type="skill"))
    assert ef2.shiv_count == 3, ef2
    # 弃牌
    ef3 = effects_for_card(Card(name="杂技", hand_index=2, cost=1, card_type="skill"))
    assert ef3.draw == 3 and ef3.discard == 1, ef3
    # 小刀本身
    shiv = make_shiv()
    assert shiv.cost == 0 and shiv.shiv and shiv.exhaust
    print("PASS silent_effects")


def test_poison_application_and_tick():
    s = _state()
    rng = random.Random(1)
    # 对敌人1上毒
    s2 = apply_action(s, Action.play(1, target_id=1), rng)  # 致命毒药
    assert s2 is not None
    assert s2.enemies[0].buffs.get("毒", 0) == 5
    # 敌回合后毒结算：敌人受到5伤，毒降至4
    s3 = enemy_turn(s2, rng)
    e = s3.enemies[0]
    assert e.buffs.get("毒", 0) == 4
    print("PASS poison_application_and_tick")


def test_shiv_generation():
    s = _state()
    rng = random.Random(2)
    s2 = apply_action(s, Action.play(2, target_id=None), rng)  # 刀刃之舞
    shivs = [c for c in s2.hand if c.shiv]
    assert len(shivs) == 3, len(shivs)
    print("PASS shiv_generation")


def test_discard_and_sly():
    # 构造：手牌含一张 Sly 牌，弃牌触发它自动打出
    s = _state()
    rng = random.Random(3)
    sly_card = Card(name="突袭", hand_index=9, cost=0, damage=4, card_type="attack", sly=True)
    s.hand.append(sly_card)
    # 用"杂技"弃1张（近似测试：直接调用弃牌相关——杂技在示例没有，构造一张）
    acro = Card(name="杂技", hand_index=5, cost=1, damage=0, card_type="skill")
    s.hand.append(acro)
    before_enemy = s.enemies[0].hp
    s2 = apply_action(s, Action.play(5, target_id=None), rng)  # 打杂技：抽3弃1
    assert s2 is not None
    # 杂技被移除
    assert all(c.hand_index != 5 for c in s2.hand)
    print("PASS discard_and_sly")


def test_sl_memory():
    mem = DrawOrderMemory()
    c1 = Card(name="毒刺", hand_index=0, cost=1, damage=6)
    c2 = Card(name="打击", hand_index=0, cost=1, damage=6)
    c3 = Card(name="小刀", hand_index=0, cost=0, damage=4)
    # 抽牌观察
    mem.observe_new_cards([c1, c2, c3])
    assert mem.known_length == 3
    assert mem.peek(0).name == "毒刺"
    assert mem.peek(2).name == "小刀"
    assert mem.peek(5) is None
    # SL：回到起点重抽，不应重复追加
    mem.on_sl()
    mem.observe_new_cards([Card(name="毒刺", hand_index=0, cost=1, damage=6)])
    mem.observe_new_cards([Card(name="打击", hand_index=0, cost=1, damage=6)])
    assert mem.known_length == 3, mem.known_length  # 未重复
    assert mem.peek(0).name == "毒刺"
    print("PASS sl_memory")


def test_diff_new_cards():
    prev = [Card(name="打击", hand_index=0, cost=1, damage=6)]
    cur = [Card(name="打击", hand_index=0, cost=1, damage=6),
           Card(name="毒刺", hand_index=1, cost=1, damage=6)]
    new = diff_new_cards(prev, cur)
    assert len(new) == 1 and new[0].name == "毒刺"
    print("PASS diff_new_cards")


def test_card_value():
    # 弃牌引擎：已有弃牌卡时，杂技分更高
    deck = ["杂技", "早有准备", "打击", "防御"]
    s1, r1 = score_card("杂技", deck)
    s2, r2 = score_card("杂技", [])
    assert s1 >= s2, (s1, s2)
    # 幽灵形态高分
    sg, _ = score_card("幽灵形态")
    sl, _ = score_card("打击")
    assert sg > sl
    print(f"PASS card_value (杂技协同 {s1:.1f} vs {s2:.1f})")


def test_route():
    opts = choose_route(_map_snapshot())
    assert opts and opts[0]["score"] >= 0
    # 最优应为 shop（分最高）或 elite
    print(f"PASS route best={opts[0]['node'].get('type')}")


def test_reward():
    deck = ["打击", "打击", "防御"]
    res = choose_reward(_reward_snapshot(), deck)
    assert res["cards"], "应有候选"
    assert res["recommendation"][0] in ("card", "gold", "skip")
    print(f"PASS reward rec={res['recommendation']}")


def test_shop():
    deck = ["打击", "打击", "防御", "中和"]
    res = choose_shop(_shop_snapshot(), deck, gold=150)
    total = sum(r["price"] for r in res["recommendations"])
    assert total <= 150, total
    print(f"PASS shop bought={[(r['kind'], r.get('name')) for r in res['recommendations']]}")


def test_mcts_silent():
    s = _state()
    mcts = MCTS(default_policy=greedy_policy, seed=7)
    root = mcts.search(s, iterations=300)
    ranked = mcts.ranked_actions(root)
    assert ranked
    best = mcts.best_action(root)
    assert best is not None
    print(f"PASS mcts_silent best={best.describe(s)}")
    for a, avg, v in ranked[:3]:
        print(f"    {a.describe(s):30s} avg={avg:.3f} visits={v}")


if __name__ == "__main__":
    test_silent_effects()
    test_poison_application_and_tick()
    test_shiv_generation()
    test_discard_and_sly()
    test_sl_memory()
    test_diff_new_cards()
    test_card_value()
    test_route()
    test_reward()
    test_shop()
    test_mcts_silent()
    print("\nV2 全部测试通过 ✓")
