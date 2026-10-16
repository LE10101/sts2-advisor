"""命令行主循环：AI 教练（多阶段决策）。

两种模式：
- offline : 内置示例，可选择演示战斗 MCTS / SL 牌序记忆 / 地图路线 / 奖励选卡 / 商店。
- real    : 连接 autoSpire HTTP 服务，按 phase 路由到对应决策器；
            战斗阶段自动记录 SL 牌序，MCTS 按真实牌序推演；
            支持用户确认后通过 /action 半自动执行。

phase 路由：combat -> MCTS 战斗推荐
           map    -> 路线推荐
           reward -> 奖励选卡推荐
           shop   -> 商店购买推荐
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from typing import Optional

from .client import build_client
from .drawmemory import DrawOrderMemory, diff_new_cards
from .model import Card, CombatState
from .mcts import MCTS
from .policy import greedy_policy
from .reward import choose_reward, format_reward_result
from .route import choose_route
from .shop import choose_shop, format_shop_result
from .simulator import enemy_turn, is_terminal, play_player_turn, terminal_score


# ===========================================================================
# 战斗推荐（共用）
# ===========================================================================
def format_state(state: CombatState) -> str:
    lines = [f"== 回合 {state.turn} =="]
    lines.append(
        f"玩家 HP {state.player_hp}/{state.max_hp}  能量 {state.energy}  格挡 {state.player_block}  buff {state.player_buffs or '-'}"
    )
    lines.append(f"牌堆 抽:{state.draw_pile} 弃:{state.discard_pile}  手牌 {len(state.hand)}")
    for c in state.hand:
        lines.append(f"   {c}")
    for e in state.enemies:
        alive = "存活" if e.alive else "死亡"
        lines.append(
            f"   {e.name} HP {e.hp}/{e.max_hp} 格挡{e.block} 意图:{e.intent}({e.intent_value}) buff{e.buffs} [{alive}]"
        )
    return "\n".join(lines)


def recommend_combat(state: CombatState, iterations: int, memory=None) -> tuple:
    mcts = MCTS(default_policy=greedy_policy, seed=state.seed, memory=memory)
    root = mcts.search(state, iterations=iterations)
    return mcts, root


def print_recommendations(state: CombatState, ranked: list):
    if not ranked:
        print("  （无可行动作）")
        return
    print("  MCTS 推荐（按预期收益排序）：")
    for i, (action, avg, visits) in enumerate(ranked[:8]):
        print(f"   [{i}] {action.describe(state)}  预期收益 {avg*100:.1f}%  (采样{visits})")
    from .explanation import explain_combat
    best = ranked[0][0]
    print(f"  理由: {explain_combat(state, best, ranked)}")


def _action_to_payload(action) -> dict:
    if action.kind == "end_turn":
        return {"action": "end_turn"}
    if action.kind == "play_card":
        payload = {"action": "play_card", "hand_index": action.hand_index}
        if action.target_id is not None:
            payload["target_id"] = action.target_id
        return payload
    if action.kind == "use_potion":
        return {"action": "use_potion", "slot_index": action.potion_slot}
    return {"action": action.kind}


# ===========================================================================
# 真实模式：按 phase 路由
# ===========================================================================
def run_real(client, iterations: int, dump_dir: Optional[str] = None, overlay=None):
    """真实模式主循环。overlay 为已创建的 SubtitleOverlay（主线程创建），或 None。"""
    print("连接 autoSpire ...（请确认游戏已启动且 mod 已初始化）")
    if not client.ping():
        print("✗ 无法连接 autoSpire 服务。请检查：")
        print("   1) 游戏已启动且 autoSpire mod 加载成功（日志见 autoSpire mod initialized）")
        print("   2) 端口是否正确（默认 8765，客机 8766）")
        sys.exit(1)
    print("✓ 已连接。按阶段自动给出推荐：战斗 / 路线 / 奖励 / 商店")
    if dump_dir:
        import os
        os.makedirs(dump_dir, exist_ok=True)
        print(f"  原始状态将按帧写入 {dump_dir}/（供校准字段映射）")

    ov = overlay  # 由主线程创建的 SubtitleOverlay，或 None
    if ov is not None and not getattr(ov, "available", False):
        ov = None

    mem = DrawOrderMemory()
    prev_state: Optional[CombatState] = None

    while True:
        try:
            snap = client.get_state()
        except Exception as e:
            print(f"  读取状态失败: {e}，3s 后重试")
            time.sleep(3)
            continue

        if dump_dir:
            import json
            import os
            run_real._seq = getattr(run_real, "_seq", 0) + 1
            with open(os.path.join(dump_dir, f"state_{run_real._seq:04d}.json"), "w",
                      encoding="utf-8") as f:
                json.dump(snap, f, ensure_ascii=False, indent=1)

        phase = snap.get("phase", "menu")

        if phase == "combat":
            state = CombatState.from_snapshot(snap)
            # SL / 新战斗检测
            if prev_state is None:
                mem.on_new_combat()
            elif state.turn < prev_state.turn:
                mem.on_sl()  # 回合回退 -> SL
            new_cards = diff_new_cards(prev_state.hand, state.hand) if prev_state else []
            if new_cards:
                mem.observe_new_cards(new_cards)
            prev_state = state

            print("\n" + format_state(state))
            print("  " + mem.describe())
            if is_terminal(state):
                sc = terminal_score(state)
                print(f"  战斗结束: {'胜利' if sc == 1.0 else '失败'}")
                prev_state = None
                time.sleep(2)
                continue

            mcts, root = recommend_combat(state, iterations, mem)
            ranked = mcts.ranked_actions(root)
            print_recommendations(state, ranked)
            if ov:
                from .explanation import explain_combat
                from .overlay import format_combat_subtitle
                best = ranked[0][0] if ranked else None
                ov.push(format_combat_subtitle(state, ranked, explain_combat(state, best, ranked)))

            choice = input("  输入序号执行 / r 重算 / n 重刷 / s 标记SL / q 退出 > ").strip().lower()
            if choice == "q":
                break
            if choice == "s":
                mem.on_sl()
                print("  已标记 SL，回到战斗起点重新确认牌序")
                continue
            if choice in ("r", "n"):
                time.sleep(1)
                continue
            try:
                idx = int(choice)
                action = ranked[idx][0]
            except (ValueError, IndexError):
                print("  无效输入")
                continue
            try:
                res = client.take_action(_action_to_payload(action))
                print(f"  执行 {action.describe(state)} -> {res}")
                time.sleep(1.0)  # autoSpire 出牌异步
            except Exception as e:
                print(f"  执行失败: {e}")

        elif phase == "map":
            deck = _deck_from_snap(snap)
            print("\n== 地图路线推荐 ==")
            options = choose_route(snap)
            for i, o in enumerate(options[:6]):
                node = o["node"]
                print(f"   [{i}] 到 ({node.get('col','?')},{node.get('row','?')})  分{o['score']:.2f}  {o['reason']}")
            if ov:
                from .overlay import format_phase_subtitle
                body = "\n".join(f"[{i}] {o['reason']}" for i, o in enumerate(options[:3]))
                ov.push(format_phase_subtitle("map", body))
            choice = input("  选择路线序号执行 / n 重刷 / q 退出 > ").strip().lower()
            if choice == "q":
                break
            if choice == "n":
                time.sleep(1)
                continue
            try:
                idx = int(choice)
                node = options[idx]["node"]
                client.take_action({"action": "move_to_map_coord",
                                    "col": node.get("col"), "row": node.get("row")})
                print("  已选择该节点")
                time.sleep(1)
            except Exception as e:
                print(f"  执行失败: {e}")

        elif phase == "reward":
            deck = _deck_from_snap(snap)
            res = choose_reward(snap, deck)
            print("\n" + format_reward_result(res))
            if ov:
                from .overlay import format_phase_subtitle
                ov.push(format_phase_subtitle("reward", res.get("reason", "")))
            choice = input("  card<N> 选第N张 / gold 拿金币 / skip 跳过 / q 退出 > ").strip().lower()
            if choice == "q":
                break
            try:
                if choice.startswith("card"):
                    idx = int(choice[4:])
                    client.take_action({"action": "pick_reward", "choice_index": idx, "choice_type": "card"})
                elif choice == "gold":
                    client.take_action({"action": "pick_reward", "choice_index": 0, "choice_type": "gold"})
                elif choice == "skip":
                    client.take_action({"action": "pick_reward", "choice_index": 0, "choice_type": "skip"})
                time.sleep(1)
            except Exception as e:
                print(f"  执行失败: {e}")

        elif phase == "shop":
            deck = _deck_from_snap(snap)
            shop_res = choose_shop(snap, deck)
            print("\n" + format_shop_result(shop_res))
            if ov:
                from .overlay import format_phase_subtitle
                ov.push(format_phase_subtitle("shop", shop_res.get("reason", "")))
            input("  看完后按回车继续（手动购买）/ q 退出 > ").strip()
            time.sleep(1)

        else:
            print(f"  当前阶段: {phase}，等待进入可决策阶段 ...")
            time.sleep(2)


def _deck_from_snap(snap) -> list:
    run = snap.get("run", {}) or {}
    deck_raw = run.get("deck") or run.get("cards") or []
    out = []
    for d in deck_raw:
        if isinstance(d, dict):
            out += [d.get("name", "")] * (d.get("count", 1) or 1)
        else:
            out.append(str(d))
    return out


# ===========================================================================
# 离线模式：分阶段演示
# ===========================================================================
def _silent_combat_snapshot() -> dict:
    return {
        "phase": "combat",
        "run": {"chapter": 1, "floor": 3, "gold": 20,
                "deck": [{"name": "打击", "count": 3}, {"name": "防御", "count": 2},
                         {"name": "中和", "count": 1}, {"name": "生存者", "count": 1}]},
        "combat": {
            "player": {"hp": 70, "max_hp": 70, "block": 0, "energy": 3,
                       "buffs": {}, "relics": []},
            "hand": [
                {"hand_index": 0, "name": "中和", "cost": 0, "damage": 3, "description": "造成3伤害，附加1层虚弱"},
                {"hand_index": 1, "name": "致命毒药", "cost": 1, "description": "施加5点中毒"},
                {"hand_index": 2, "name": "刀刃之舞", "cost": 1, "description": "将3张小刀加入你的手牌"},
                {"hand_index": 3, "name": "生存者", "cost": 1, "block": 8, "description": "获得8格挡，丢弃1张牌"},
                {"hand_index": 4, "name": "打击", "cost": 1, "damage": 6, "description": "造成6点伤害"},
            ],
            "enemies": [
                {"id": 1, "name": "邪教徒", "hp": 45, "max_hp": 45, "block": 0,
                 "intent": "attack", "intent_value": 11, "buffs": {}},
                {"id": 2, "name": "邪教徒", "hp": 45, "max_hp": 45, "block": 0,
                 "intent": "attack", "intent_value": 11, "buffs": {}},
            ],
            "potions": [],
            "draw_pile": 6, "discard_pile": 1, "turn": 1, "seed": 5,
        },
    }


def _map_snapshot() -> dict:
    return {
        "phase": "map",
        "run": {"deck": []},
        "map": {
            "current": {"col": 3, "row": 4},
            "nodes": [
                {"col": 1, "row": 5, "type": "monster"},
                {"col": 3, "row": 5, "type": "elite"},
                {"col": 5, "row": 5, "type": "shop"},
                {"col": 7, "row": 5, "type": "rest"},
                {"col": 3, "row": 6, "type": "treasure"},
            ],
        },
    }


def _reward_snapshot() -> dict:
    return {
        "phase": "reward",
        "run": {"deck": [{"name": "打击", "count": 3}, {"name": "防御", "count": 2},
                         {"name": "中和", "count": 1}]},
        "reward": {
            "gold": 0,
            "cards": [
                {"name": "致命毒药", "rarity": "普通"},
                {"name": "杂技", "rarity": "普通"},
                {"name": "诅咒", "rarity": "普通"},
            ],
        },
    }


def _shop_snapshot() -> dict:
    return {
        "phase": "shop",
        "run": {"gold": 150, "deck": [{"name": "打击", "count": 3}, {"name": "防御", "count": 2},
                                      {"name": "中和", "count": 1}]},
        "shop": {
            "items": [
                {"type": "card", "name": "杂技", "price": 55, "rarity": "普通"},
                {"type": "card", "name": "后空翻", "price": 55, "rarity": "普通"},
                {"type": "card", "name": "致命毒药", "price": 55, "rarity": "普通"},
                {"type": "relic", "name": "蛇之戒指", "price": 130},
                {"type": "remove", "price": 75},
            ],
        },
    }


def run_offline(iterations: int):
    print("== 离线自测模式：选择要演示的阶段 ==")
    while True:
        print("\n1) 战斗 MCTS（静默猎手）  2) SL 牌序记忆  3) 地图路线  4) 奖励选卡  5) 商店购买  q) 退出")
        choice = input("> ").strip().lower()
        if choice == "q":
            break
        if choice == "1":
            _demo_combat(iterations)
        elif choice == "2":
            _demo_sl_memory()
        elif choice == "3":
            print("\n" + format_route(_map_snapshot()))
        elif choice == "4":
            deck = _deck_from_snap(_reward_snapshot())
            print("\n" + format_reward_result(choose_reward(_reward_snapshot(), deck)))
        elif choice == "5":
            deck = _deck_from_snap(_shop_snapshot())
            print("\n" + format_shop_result(choose_shop(_shop_snapshot(), deck)))
        else:
            print("  无效输入")


def format_route(snap: dict) -> str:
    lines = ["== 地图路线推荐 =="]
    options = choose_route(snap)
    for o in options[:6]:
        node = o["node"]
        lines.append(f"   到 ({node.get('col','?')},{node.get('row','?')})  分{o['score']:.2f}  {o['reason']}")
    return "\n".join(lines)


def _demo_combat(iterations: int):
    """离线战斗：可手动执行动作推进，演示静默猎手 MCTS 决策。"""
    state = CombatState.from_snapshot(_silent_combat_snapshot())
    rng = random.Random(state.seed)
    while True:
        print("\n" + format_state(state))
        if is_terminal(state):
            sc = terminal_score(state)
            print(f"== 战斗结束: {'胜利' if sc == 1.0 else '失败'} ==")
            break
        mcts, root = recommend_combat(state, iterations)
        ranked = mcts.ranked_actions(root)
        print_recommendations(state, ranked)
        choice = input("  输入序号执行 / end 结束回合 / q 返回菜单 > ").strip().lower()
        if choice == "q":
            break
        if choice == "end":
            state = enemy_turn(state, rng)
            continue
        try:
            idx = int(choice)
            action = ranked[idx][0]
        except (ValueError, IndexError):
            print("  无效输入")
            continue
        if action.kind == "end_turn":
            state = enemy_turn(state, rng)
        else:
            state = play_player_turn(state, [action], rng)


def _demo_sl_memory():
    """演示 SL 牌序记忆：抽牌观察 + SL 重抽去重，最终得到确定性牌序。"""
    print("== SL 牌序记忆演示 ==")
    mem = DrawOrderMemory()
    real_deck = [("毒刺", 1, 6), ("打击", 1, 6), ("小刀", 0, 4), ("防御", 1, 0), ("生存者", 1, 8)]
    pos_in_real = 0

    def peek_next():
        nonlocal pos_in_real
        if pos_in_real >= len(real_deck):
            return None
        n, c, d = real_deck[pos_in_real]
        pos_in_real += 1
        return n, c, d

    def observe_draws(count):
        for _ in range(count):
            item = peek_next()
            if item is None:
                break
            n, c, d = item
            print(f"    抽到 {n}")
            mem.observe_new_cards([Card(name=n, hand_index=0, cost=c, damage=d)])

    print("  第一次抽牌（不 SL）：")
    observe_draws(3)
    print("  " + mem.describe())

    print("  SL 读档回到战斗开始，重新抽牌（牌序固定）：")
    mem.on_sl()
    pos_in_real = 0
    observe_draws(3)
    print("  " + mem.describe())
    print("  → SL 重抽未重复追加，牌序记忆正确累积")
    print("  MCTS 将按此记忆确定性推演（而非随机抽样）")


# ===========================================================================
def main(argv: Optional[list] = None):
    parser = argparse.ArgumentParser(description="杀戮尖塔2 决策器（AI 教练 · 静默猎手 · MCTS）")
    parser.add_argument("--mode", choices=["offline", "real"], default="offline",
                        help="offline=内置示例自测；real=连接真实游戏")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765, help="autoSpire 端口（客机 8766）")
    parser.add_argument("--iterations", type=int, default=600, help="MCTS 迭代次数")
    parser.add_argument("--model", default=None,
                        help="训练好的评估器权重 (weights.json)。默认用启发式；"
                             "注意：self-play 训练的模型有分布漂移风险，仅在你确认更优时启用。")
    parser.add_argument("--dump", default=None,
                        help="real 模式下把每帧原始 /state 快照写入该目录（用于校准字段映射）")
    parser.add_argument("--overlay", action="store_true",
                        help="启动游戏内悬浮字幕窗（始终置顶半透明，显示推荐+理由）")
    args = parser.parse_args(argv)

    if args.model:
        import os
        from . import network, evaluate
        path = args.model if os.path.exists(args.model) else \
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), args.model)
        params = network.load_params(path)
        from .simulator import set_evaluator
        set_evaluator(lambda st: evaluate.evaluate_with_model(st, params))
        print(f"已启用训练评估器: {path} (kind={params.get('kind')})")

    client = build_client(mode=args.mode, host=args.host, port=args.port)
    if args.mode == "real":
        if args.overlay:
            # tkinter 必须在主线程：主线程建窗并跑 mainloop，决策循环放后台线程
            from .overlay import SubtitleOverlay
            import threading
            ov = SubtitleOverlay()
            if not ov.available:
                print("提示：tkinter 不可用，悬浮字幕未启动（仍可看终端推荐）")
                run_real(client, args.iterations, dump_dir=args.dump, overlay=None)
            else:
                print("悬浮字幕已启动（置顶半透明窗，拖动标题栏移动；关闭窗口退出）")
                t = threading.Thread(
                    target=run_real,
                    args=(client, args.iterations),
                    kwargs={"dump_dir": args.dump, "overlay": ov},
                    daemon=True,
                )
                t.start()
                ov.run()  # 主线程阻塞，跑 tkinter mainloop
        else:
            run_real(client, args.iterations, dump_dir=args.dump, overlay=None)
    else:
        run_offline(args.iterations)


if __name__ == "__main__":
    main()
