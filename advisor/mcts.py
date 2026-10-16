"""蒙特卡洛树搜索（MCTS, UCT 变体）决策核心。

树中的每个节点对应一个"决策点状态"：
- 打一张牌 -> 打牌后的新状态（同一玩家回合内继续决策）
- 结束回合 -> 敌人回合结算后的下一个玩家回合状态

搜索结束，按平均收益（或访问次数）为根节点的每个候选动作打分，
供 CLI 展示推荐排序。
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .model import Action, CombatState
from .simulator import apply_action, enemy_turn, is_terminal, legal_actions, rollout, terminal_score
from .policy import DefaultPolicy, greedy_policy


@dataclass
class MCTSNode:
    state: CombatState
    parent: Optional["MCTSNode"] = None
    action: Optional[Action] = None
    children: Dict[Action, "MCTSNode"] = field(default_factory=dict)
    untried: List[Action] = field(default_factory=list)
    visits: int = 0
    value: float = 0.0  # 累计收益（rollout 值之和）

    def is_fully_expanded(self) -> bool:
        return not self.untried

    def best_child(self, c: float, rng: random.Random) -> "MCTSNode":
        """UCT 选择：取 UCB1 最大的子节点。"""
        best, best_val = None, -math.inf
        for child in self.children.values():
            if child.visits == 0:
                ucb = math.inf
            else:
                exploitation = child.value / child.visits
                exploration = c * math.sqrt(math.log(self.visits + 1) / child.visits)
                ucb = exploitation + exploration
            if ucb > best_val:
                best, best_val = child, ucb
        return best


class MCTS:
    def __init__(
        self,
        default_policy: DefaultPolicy = greedy_policy,
        exploration_c: float = 1.4,
        seed: int = 0,
        memory=None,
    ):
        self.default_policy = default_policy
        self.c = exploration_c
        self.rng = random.Random(seed)
        self.memory = memory  # DrawOrderMemory：让推演按真实牌序确定性抽牌

    # -- 搜索主流程 --------------------------------------------------------
    def search(self, root_state: CombatState, iterations: int = 500) -> MCTSNode:
        """从根状态执行 iterations 次模拟，返回根节点（含各子动作统计）。"""
        root = MCTSNode(state=root_state)
        self._expand(root)
        for _ in range(iterations):
            node = root
            # 1) 选择：沿已展开路径下行到叶子
            while node.is_fully_expanded() and not is_terminal(node.state):
                node = node.best_child(self.c, self.rng)
            # 2) 展开 + 模拟
            if not is_terminal(node.state):
                node = self._expand_one(node)
                leaf = node
            else:
                leaf = node
            value = self._simulate(leaf.state)
            # 3) 回溯
            self._backprop(leaf, value)
        return root

    # -- 内部 --------------------------------------------------------------
    def _expand(self, node: MCTSNode):
        node.untried = legal_actions(node.state)

    def _expand_one(self, node: MCTSNode) -> MCTSNode:
        """从节点取一个未试动作，创建并返回子节点。"""
        if not node.untried:
            return node
        action = node.untried.pop()
        child_state = self._transition(node.state, action)
        if child_state is None:
            # 非法动作：忽略，继续取下一个
            return self._expand_one(node)
        child = MCTSNode(state=child_state, parent=node, action=action)
        node.children[action] = child
        self._expand(child)
        return child

    def _transition(self, state: CombatState, action: Action) -> Optional[CombatState]:
        if action.kind == "end_turn":
            return enemy_turn(state, self.rng, self.memory)
        return apply_action(state, action, self.rng, self.memory)

    def _simulate(self, state: CombatState) -> float:
        return rollout(state, self.rng, policy=self.default_policy, memory=self.memory)

    def _backprop(self, node: MCTSNode, value: float):
        while node is not None:
            node.visits += 1
            node.value += value
            node = node.parent

    # -- 结果解读 ----------------------------------------------------------
    def best_action(self, root: MCTSNode) -> Optional[Action]:
        """返回平均收益最高的根动作。"""
        if not root.children:
            return None
        return max(root.children, key=lambda a: root.children[a].value / max(1, root.children[a].visits))

    def ranked_actions(self, root: MCTSNode) -> List[tuple]:
        """按平均收益降序返回 [(action, 平均收益, 访问次数), ...]。"""
        out = []
        for a, child in root.children.items():
            if child.visits == 0:
                continue
            out.append((a, child.value / child.visits, child.visits))
        out.sort(key=lambda x: -x[1])
        return out
