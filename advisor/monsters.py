"""
杀戮尖塔2 怪物行为数据库
怪物行为是固定的，可以通过查资料补全
数据来源：游戏内观察 + STS2 Wiki + Reddit社区
"""
from __future__ import annotations

# 怪物行为数据库
# 每个怪物包含：名称、HP范围、出现章节、行为模式列表
# 行为模式：名称、描述、伤害、段数、类型(attack/buff/debuff/defend)
MONSTER_DB = [
    {
        "id": "jaw_worm",
        "name": "颚虫",
        "hp_min": 40, "hp_max": 46,
        "act": "Act 1",
        "moves": [
            {"name": "撕咬", "desc": "造成伤害", "damage": 11, "hits": 1, "type": "attack"},
            {"name": "嚎叫", "desc": "获得3点力量和3点格挡", "damage": 0, "type": "buff"},
            {"name": "蜷缩", "desc": "获得6点格挡", "damage": 0, "type": "defend"},
        ]
    },
    {
        "id": "cultist",
        "name": "邪教徒",
        "hp_min": 48, "hp_max": 56,
        "act": "Act 1",
        "moves": [
            {"name": "仪式", "desc": "获得3点力量（首回合必用）", "damage": 0, "type": "buff"},
            {"name": "黑暗打击", "desc": "造成伤害", "damage": 6, "hits": 1, "type": "attack"},
        ]
    },
    {
        "id": "acid_slime_m",
        "name": "酸液史莱姆（中）",
        "hp_min": 28, "hp_max": 32,
        "act": "Act 1",
        "moves": [
            {"name": "酸液喷射", "desc": "造成伤害并施加1层虚弱", "damage": 7, "hits": 1, "type": "attack"},
            {"name": "分裂", "desc": "死亡时分裂为两只小史莱姆", "damage": 0, "type": "special"},
        ]
    },
    {
        "id": "spike_slime_m",
        "name": "尖刺史莱姆（中）",
        "hp_min": 28, "hp_max": 32,
        "act": "Act 1",
        "moves": [
            {"name": "猛烈撞击", "desc": "造成伤害", "damage": 8, "hits": 1, "type": "attack"},
            {"name": "分裂", "desc": "死亡时分裂为两只小史莱姆", "damage": 0, "type": "special"},
        ]
    },
    {
        "id": "lagavulin",
        "name": "拉格武林",
        "hp_min": 109, "hp_max": 112,
        "act": "Act 1 (精英)",
        "moves": [
            {"name": "沉睡", "desc": "前3回合沉睡，受到攻击后觉醒", "damage": 0, "type": "special"},
            {"name": "虹吸", "desc": "造成伤害并降低玩家1点能量", "damage": 18, "hits": 1, "type": "attack"},
            {"name": "咆哮", "desc": "获得力量并攻击", "damage": 0, "type": "buff"},
        ]
    },
    {
        "id": "sentry",
        "name": "哨兵",
        "hp_min": 38, "hp_max": 42,
        "act": "Act 1",
        "moves": [
            {"name": "光束", "desc": "造成伤害", "damage": 9, "hits": 1, "type": "attack"},
            {"name": "眩晕", "desc": "将眩晕牌加入弃牌堆", "damage": 0, "type": "debuff"},
        ]
    },
    {
        "id": "gremlin_nob",
        "name": "哥布林首领",
        "hp_min": 82, "hp_max": 86,
        "act": "Act 1 (精英)",
        "moves": [
            {"name": "怒吼", "desc": "获得2点力量（玩家使用技能牌后）", "damage": 0, "type": "buff"},
            {"name": "猛击", "desc": "造成伤害", "damage": 14, "hits": 1, "type": "attack"},
            {"name": "冲撞", "desc": "造成大量伤害", "damage": 6, "hits": 3, "type": "attack"},
        ]
    },
    {
        "id": "slime_boss",
        "name": "史莱姆Boss",
        "hp_min": 140, "hp_max": 140,
        "act": "Act 1 (Boss)",
        "moves": [
            {"name": "猛击", "desc": "造成伤害", "damage": 35, "hits": 1, "type": "attack"},
            {"name": "分裂", "desc": "HP低于50%时分裂为两只中史莱姆", "damage": 0, "type": "special"},
        ]
    },
    {
        "id": "the_guardian",
        "name": "守护者",
        "hp_min": 230, "hp_max": 240,
        "act": "Act 1 (Boss)",
        "moves": [
            {"name": "猛烈攻击", "desc": "造成伤害", "damage": 32, "hits": 1, "type": "attack"},
            {"name": "防御模式", "desc": "获得大量格挡并切换形态", "damage": 0, "type": "defend"},
            {"name": "旋风斩", "desc": "造成多段伤害", "damage": 9, "hits": 4, "type": "attack"},
            {"name": "充能", "desc": "下回合造成双倍伤害", "damage": 0, "type": "buff"},
        ]
    },
    {
        "id": "hexaghost",
        "name": "六面鬼",
        "hp_min": 250, "hp_max": 264,
        "act": "Act 1 (Boss)",
        "moves": [
            {"name": "激活", "desc": "首回合激活6个灵体", "damage": 0, "type": "special"},
            {"name": "灼烧", "desc": "造成6点伤害×6次", "damage": 6, "hits": 6, "type": "attack"},
            {"name": "分裂", "desc": "灵体数量减少时伤害降低", "damage": 0, "type": "special"},
            {"name": "充能", "desc": "下回合造成大量伤害", "damage": 0, "type": "buff"},
        ]
    },
    # Act 2 怪物
    {
        "id": "chosen",
        "name": "被选中者",
        "hp_min": 54, "hp_max": 58,
        "act": "Act 2",
        "moves": [
            {"name": "诅咒", "desc": "将诅咒牌加入手牌", "damage": 0, "type": "debuff"},
            {"name": "刺击", "desc": "造成伤害", "damage": 12, "hits": 1, "type": "attack"},
        ]
    },
    {
        "id": "byrd",
        "name": "飞鸟",
        "hp_min": 25, "hp_max": 29,
        "act": "Act 2",
        "moves": [
            {"name": "啄击", "desc": "造成3点伤害×3次", "damage": 3, "hits": 3, "type": "attack"},
            {"name": "飞行", "desc": "获得5点格挡", "damage": 0, "type": "defend"},
        ]
    },
    {
        "id": "snake_plant",
        "name": "蛇草",
        "hp_min": 75, "hp_max": 79,
        "act": "Act 2",
        "moves": [
            {"name": "藤蔓鞭打", "desc": "造成伤害并施加易伤", "damage": 7, "hits": 2, "type": "attack"},
            {"name": "生长", "desc": "获得力量", "damage": 0, "type": "buff"},
        ]
    },
    {
        "id": "centurion",
        "name": "百夫长",
        "hp_min": 76, "hp_max": 80,
        "act": "Act 2",
        "moves": [
            {"name": "重击", "desc": "造成伤害", "damage": 16, "hits": 1, "type": "attack"},
            {"name": "防御", "desc": "获得格挡", "damage": 0, "type": "defend"},
        ]
    },
    {
        "id": "mystic",
        "name": "神秘者",
        "hp_min": 48, "hp_max": 52,
        "act": "Act 2",
        "moves": [
            {"name": "治愈", "desc": "治疗自己和盟友", "damage": 0, "type": "buff"},
            {"name": "冲击", "desc": "造成伤害", "damage": 12, "hits": 1, "type": "attack"},
        ]
    },
    # Act 2 Boss
    {
        "id": "champ",
        "name": "冠军",
        "hp_min": 420, "hp_max": 420,
        "act": "Act 2 (Boss)",
        "moves": [
            {"name": "处决", "desc": "造成大量伤害", "damage": 28, "hits": 1, "type": "attack"},
            {"name": "愤怒", "desc": "HP低于50%时获得力量和敏捷", "damage": 0, "type": "buff"},
            {"name": "防御姿态", "desc": "获得格挡", "damage": 0, "type": "defend"},
            {"name": "猛烈冲撞", "desc": "造成多段伤害", "damage": 8, "hits": 3, "type": "attack"},
        ]
    },
    {
        "id": "automaton",
        "name": "自动机",
        "hp_min": 300, "hp_max": 320,
        "act": "Act 2 (Boss)",
        "moves": [
            {"name": "光束炮", "desc": "造成伤害并施加易伤", "damage": 25, "hits": 1, "type": "attack"},
            {"name": "部署", "desc": "召唤球体", "damage": 0, "type": "special"},
            {"name": "过载", "desc": "下回合造成双倍伤害", "damage": 0, "type": "buff"},
        ]
    },
    # 静默猎手相关特殊怪物
    {
        "id": "gremlin",
        "name": "哥布林",
        "hp_min": 12, "hp_max": 16,
        "act": "Act 1",
        "moves": [
            {"name": "刺击", "desc": "造成伤害", "damage": 5, "hits": 1, "type": "attack"},
        ]
    },
    {
        "id": "fungi_beast",
        "name": "真菌兽",
        "hp_min": 22, "hp_max": 28,
        "act": "Act 1",
        "moves": [
            {"name": "孢子", "desc": "施加虚弱", "damage": 0, "type": "debuff"},
            {"name": "猛击", "desc": "造成伤害", "damage": 6, "hits": 1, "type": "attack"},
        ]
    },
    {
        "id": "looter",
        "name": "掠夺者",
        "hp_min": 44, "hp_max": 48,
        "act": "Act 1",
        "moves": [
            {"name": "逃跑", "desc": "几回合后逃跑并偷走金币", "damage": 0, "type": "special"},
            {"name": "刺击", "desc": "造成伤害", "damage": 10, "hits": 1, "type": "attack"},
        ]
    },
]


def get_monster_by_name(name: str) -> dict | None:
    """按名称查找怪物"""
    for m in MONSTER_DB:
        if m["name"] in name or name in m["name"]:
            return m
    return None


def get_monsters_by_act(act: str) -> list[dict]:
    """按章节获取怪物列表"""
    return [m for m in MONSTER_DB if act.lower() in m.get("act", "").lower()]
