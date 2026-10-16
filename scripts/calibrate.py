"""autoSpire 真实局字段校准报告。

用法：
    python3 scripts/calibrate.py [dump目录]   # 默认 ./dump

先用 ``python3 run.py --mode real --dump dump`` 跑一次真实局，把每帧原始 /state
快照存到 dump/，再用本脚本分析：各阶段关键字段是否被我们解析到、缺了什么。

输出按 phase 汇总：字段命中率、解析成败、缺失的关键字段，方便现场校准。
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from advisor.model import _pick  # noqa: E402

# 各阶段我们要读的关键字段（点分路径，容忍缺中间节点）
KEY_FIELDS = {
    "combat": ["combat.hand", "combat.enemies", "combat.player", "combat.draw_pile",
               "combat.discard_pile", "combat.turn"],
    "map": ["map", "nodes", "routes"],
    "reward": ["rewards", "cards", "gold", "skip"],
    "shop": ["shop", "gold", "merchant", "cards", "relics"],
    "menu": [],
}


def field_present(snap, path):
    """沿点分路径检查字段是否存在（容忍缺中间节点）。"""
    cur = snap
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def analyze_file(path):
    with open(path, encoding="utf-8") as f:
        snap = json.load(f)
    phase = snap.get("phase", "?")
    report = {"phase": phase}
    # 阶段级字段
    keys = KEY_FIELDS.get(phase, [])
    hits = {k: field_present(snap, k) for k in keys}
    report["fields"] = hits
    # 尝试解析战斗状态
    if phase == "combat":
        try:
            from advisor.model import CombatState
            st = CombatState.from_snapshot(snap)
            report["parse_ok"] = True
            report["parsed"] = (f"HP={st.player_hp}/{st.max_hp} 能量={st.energy} "
                                f"手牌{len(st.hand)} 敌人{len(st.enemies)} "
                                f"抽牌堆{st.draw_pile} 回合{st.turn}")
            # 检查敌方关键子字段
            missing_enemy = []
            for i, e in enumerate(st.enemies[:3]):
                if e.hp == 0 and e.max_hp == 0:
                    missing_enemy.append(f"enemy[{i}].hp 为0")
                if e.intent == "unknown":
                    missing_enemy.append(f"enemy[{i}].intent 未识别")
            if missing_enemy:
                report["warnings"] = missing_enemy
        except Exception as ex:
            report["parse_ok"] = False
            report["error"] = str(ex)
    else:
        report["parse_ok"] = None
    return report


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else "dump"
    files = sorted(glob.glob(os.path.join(d, "*.json")))
    if not files:
        print(f"在 {d}/ 下没找到快照。先跑： python3 run.py --mode real --dump {d}")
        return
    print(f"分析 {len(files)} 帧快照，按 phase 汇总：\n")
    by_phase = {}
    for fp in files:
        try:
            r = analyze_file(fp)
        except Exception as ex:
            print(f"  {os.path.basename(fp)}: 读取失败 {ex}")
            continue
        by_phase.setdefault(r["phase"], []).append(r)

    for phase, reps in by_phase.items():
        n = len(reps)
        ok = sum(1 for r in reps if r.get("parse_ok"))
        print(f"== phase={phase}  ({n} 帧, 战斗解析成功 {ok}) ==")
        # 字段命中
        fields = [k for k in reps[0].get("fields", {})]
        for k in fields:
            hit = sum(1 for r in reps if r.get("fields", {}).get(k))
            print(f"    {k:16s} 命中 {hit}/{n}")
        # 警告 / 示例
        for r in reps:
            if r.get("warnings"):
                print(f"    警告: {'; '.join(r['warnings'])}")
            if r.get("parsed") and n <= 6:
                print(f"    示例: {r['parsed']}")
            if r.get("error"):
                print(f"    错误: {r['error']}")
        print()

    # 缺 phase 覆盖提示
    covered = set(by_phase)
    expected = set(KEY_FIELDS) - {"menu"}
    missing_phase = expected - covered
    if missing_phase:
        print("注意：以下阶段尚未采集到快照（跑过相应环节后会自动出现在 dump）：",
              ", ".join(sorted(missing_phase)))
    print("\n校准完成。若 combat 字段命中低或解析失败，请把上述缺失字段反馈给我调整解析。")


if __name__ == "__main__":
    main()
