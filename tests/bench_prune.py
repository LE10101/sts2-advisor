"""性能对比：剪枝 开/关 在小状态与大状态下的提速。"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from advisor.model import CombatState, Card, Enemy
from advisor.mcts import MCTS
from advisor.policy import greedy_policy
import advisor.simulator as sim
import advisor.cli as cli


def no_prune(state):
    from advisor.model import Action
    from advisor.cards import effects_for_card
    acts = []
    for card in state.hand:
        if card.cost > state.energy:
            continue
        ef = effects_for_card(card)
        if ef.aoe or (ef.damage <= 0 and ef.poison <= 0):
            acts.append(Action.play(card.hand_index, None))
        else:
            for e in state.enemies:
                acts.append(Action.play(card.hand_index, e.id))
    acts.append(Action.end_turn())
    return acts


def big_state():
    hand = [Card(name='打击', hand_index=i, cost=1, damage=6, card_type='attack') for i in range(5)]
    hand += [Card(name='防御', hand_index=i + 5, cost=1, block=5, card_type='skill') for i in range(3)]
    hand += [Card(name='致命毒药', hand_index=8, cost=1, card_type='skill'),
             Card(name='刀刃之舞', hand_index=9, cost=1, card_type='skill')]
    enemies = [Enemy(id=i, name='敌', hp=40, max_hp=40, intent='attack', intent_value=10) for i in range(4)]
    return CombatState(player_hp=70, max_hp=70, energy=3, hand=hand, enemies=enemies,
                       draw_pile=5, discard_pile=2)


def bench(name, state, iters):
    print(f"== {name} ==")
    s = state.copy()
    print(f"  候选数 带剪枝={len(sim.legal_actions(s))} 未剪枝={len(no_prune(s))}")
    m1 = MCTS(default_policy=greedy_policy, seed=1)
    t0 = time.time(); r1 = m1.search(s, iters); d1 = time.time() - t0
    orig = sim.legal_actions
    sim.legal_actions = no_prune
    m2 = MCTS(default_policy=greedy_policy, seed=1)
    t0 = time.time(); r2 = m2.search(s, iters); d2 = time.time() - t0
    sim.legal_actions = orig
    b1 = m1.best_action(r1); b2 = m2.best_action(r2)
    print(f"  带剪枝 {d1:.3f}s 最佳={b1.describe(s)}")
    print(f"  未剪枝 {d2:.3f}s 最佳={b2.describe(s)}")
    print(f"  提速 = {d2 / max(d1, 1e-9):.2f}x")


if __name__ == "__main__":
    bench("小状态(5牌2敌)", CombatState.from_snapshot(cli._silent_combat_snapshot()), 300)
    bench("大状态(10牌4敌)", big_state(), 400)
