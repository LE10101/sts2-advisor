"""蒙特卡洛树搜索（UCT）。"""
from __future__ import annotations
import math
import random
from typing import Optional
from .model import CombatState, Action
from .simulator import legal_actions, apply_action, rollout, is_terminal


class MCTSNode:
    __slots__ = ("state", "parent", "action", "children", "visits", "value",
                 "untried", "terminal")

    def __init__(self, state: CombatState, parent=None, action=None):
        self.state = state
        self.parent = parent
        self.action = action
        self.children: list["MCTSNode"] = []
        self.visits = 0
        self.value = 0.0
        self.untried = legal_actions(state, prune=True)
        self.terminal = is_terminal(state)


class MCTS:
    def __init__(self, c: float = 1.4, default_policy=None, seed: Optional[int] = None):
        self.c = c
        self.default_policy = default_policy
        self.rng = random.Random(seed)

    def search(self, state: CombatState, iterations: int = 600) -> MCTSNode:
        root = MCTSNode(state)
        for i in range(iterations):
            node = self._select(root)
            if not node.terminal and node.untried:
                node = self._expand(node)
            reward = rollout(node.state, policy=self.default_policy, rng=self.rng)
            self._backprop(node, reward)
            # 早期停止：如果某个动作明显领先，提前终止
            if i > 100 and i % 50 == 0 and root.children:
                ranked = sorted(root.children, key=lambda c: c.visits, reverse=True)
                if len(ranked) >= 2:
                    top1, top2 = ranked[0], ranked[1]
                    if top1.visits > 0 and top2.visits > 0:
                        v1 = top1.value / top1.visits
                        v2 = top2.value / top2.visits
                        # 领先15%且访问次数足够，提前停止
                        if v1 - v2 > 0.15 and top1.visits > 30:
                            break
        return root

    def _select(self, node: MCTSNode) -> MCTSNode:
        while not node.terminal and not node.untried:
            node = self._best_child(node)
        return node

    def _expand(self, node: MCTSNode) -> MCTSNode:
        action = self.rng.choice(node.untried)
        node.untried.remove(action)
        child = MCTSNode(apply_action(node.state, action), parent=node, action=action)
        node.children.append(child)
        return child

    def _best_child(self, node: MCTSNode) -> MCTSNode:
        best = None
        best_score = -1.0
        for ch in node.children:
            if ch.visits == 0:
                return ch
            exploit = ch.value / ch.visits
            explore = self.c * math.sqrt(math.log(node.visits) / ch.visits)
            score = exploit + explore
            if score > best_score:
                best_score = score
                best = ch
        return best or node.children[0]

    def _backprop(self, node: MCTSNode, reward: float):
        while node is not None:
            node.visits += 1
            node.value += reward
            node = node.parent

    def ranked_actions(self, root: MCTSNode) -> list[tuple[Action, float, int]]:
        """按平均收益排序的 (action, avg_value, visits)。"""
        results = []
        for ch in root.children:
            if ch.visits > 0 and ch.action is not None:
                results.append((ch.action, ch.value / ch.visits, ch.visits))
        results.sort(key=lambda x: x[1], reverse=True)
        return results
