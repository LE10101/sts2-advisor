"""Self-play 采样器：生成随机战斗对局，采集 (状态特征, 终局结果) 监督样本。

用于训练状态评估器（network.py）。对每一局随机战斗：
- 生成随机手牌 / 敌人 / 我方 HP / 能量
- 用策略（默认混合：随机 + 贪心）推进到终局，取 terminal_score 作为标签
- 记录路径上每个状态的 features，绑定该局终局结果（1 赢 / 0 输）

这样一局对局产出多条"中间状态 → 结局"样本，累积成评估器的训练集。
"""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

from .cards import CARD_EFFECTS, effects_for_card
from .evaluate import state_features
from .model import Action, Card, CombatState, Enemy
from .simulator import MAX_STEPS, apply_action, enemy_turn, legal_actions, terminal_score
from .policy import greedy_policy, random_policy

# 常用战斗牌池（覆盖静默猎手主流 + 通用）
_CARD_POOL = ["打击", "防御", "中和", "致命毒药", "刀刃之舞", "生存者", "杂技", "反射",
              "战术家", "毒雾", "终结技", "淬毒之刃", "优雅", "下毒", "千穿百刺", "毒刃"]


def random_card(rng: random.Random, hand_index: int) -> Card:
    name = rng.choice(_CARD_POOL)
    rule = CARD_EFFECTS.get(name, {})
    ef = effects_for_card(Card(name=name, hand_index=hand_index, cost=0, damage=0, block=0))
    cost = rule.get("cost", 1)
    ctype = rule.get("card_type", "attack" if ef.damage else "skill")
    return Card(name=name, hand_index=hand_index, cost=cost,
                damage=ef.damage, block=ef.block, card_type=ctype)


def random_state(rng: random.Random) -> CombatState:
    hand_n = rng.randint(4, 7)
    hand = [random_card(rng, i) for i in range(hand_n)]
    enemy_n = rng.randint(1, 3)
    enemies = []
    for i in range(enemy_n):
        hp = rng.randint(15, 60)
        enemies.append(Enemy(id=i, name=f"敌人{i}", hp=hp, max_hp=hp, block=0,
                             intent=rng.choice(["attack", "attack", "buff"]),
                             intent_value=rng.randint(4, 15), buffs={}))
    max_hp = rng.randint(50, 80)
    return CombatState(player_hp=rng.randint(30, max_hp), max_hp=max_hp,
                       energy=rng.randint(2, 4), hand=hand, enemies=enemies,
                       draw_pile=rng.randint(3, 12), discard_pile=rng.randint(0, 6))


def _terminal(s: CombatState, rng: random.Random, policy, steps: int) -> Tuple[float, int]:
    """推进到终局，返回 (终局分数, 消耗步数)。"""
    n = 0
    while n < steps:
        sc = terminal_score(s)
        if sc is not None:
            return sc, n
        acts = legal_actions(s)
        if not acts:
            return 0.0, n
        a = policy(s, acts, rng) if policy is not None else rng.choice(acts)
        if a.kind == "end_turn":
            s = enemy_turn(s, rng, None)
        else:
            ns = apply_action(s, a, rng, None)
            s = ns if ns is not None else enemy_turn(s, rng, None)
        n += 1
    t = terminal_score(s)
    return (t if t is not None else 0.5), n


def collect_samples(num_games: int, seed: int = 0, rollouts: int = 4,
                    sample_per_game: int = 3, mix_greedy: float = 0.5,
                    steps: int = MAX_STEPS, progress: bool = True) -> Tuple[List[list], List[float]]:
    """采集样本。返回 (特征列表, 标签列表)。

    - 标签 = 从该状态独立做多次 rollout 的平均结果（更接近真实期望，避免单局结局的归属偏差）。
    - 每局沿策略路径间隔采样几个中间状态，各自多次 rollout 取均值。
    """
    rng = random.Random(seed)
    rng_pol = random.Random(seed + 999)
    X: List[list] = []
    y: List[float] = []
    for g in range(num_games):
        state = random_state(rng)
        use_greedy = rng_pol.random() < mix_greedy
        policy = greedy_policy if use_greedy else random_policy
        # 沿路径采样若干中间状态
        s = state
        n = 0
        sampled = 0
        path_states = [state.copy()]
        while n < steps and sampled < sample_per_game - 1:
            if terminal_score(s) is not None:
                break
            acts = legal_actions(s)
            if not acts:
                break
            a = policy(s, acts, rng_pol) if policy is not None else rng_pol.choice(acts)
            if a.kind == "end_turn":
                s = enemy_turn(s, rng_pol, None)
            else:
                ns = apply_action(s, a, rng_pol, None)
                s = ns if ns is not None else enemy_turn(s, rng_pol, None)
            n += 1
            if n % 2 == 0:
                path_states.append(s.copy())
                sampled += 1
        # 每个中间状态多次 rollout 平均作标签
        for ps in path_states:
            total = 0.0
            for _ in range(rollouts):
                total += _terminal(ps.copy(), random.Random(rng_pol.randrange(10 ** 9)),
                                   policy, steps)[0]
            label = total / rollouts
            X.append(state_features(ps))
            y.append(label)
        if progress and (g + 1) % 50 == 0:
            print(f"  采集 {g + 1}/{num_games} 局, 累计样本 {len(X)}")
    return X, y
