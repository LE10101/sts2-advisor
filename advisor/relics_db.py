"""
遗物数据库 - 杀戮尖塔2
基于 spire-codex.com 真实数据
包含静默猎手专属和共享遗物，每个遗物包含名称、效果、稀有度、图片URL
"""

# 静默猎手专属遗物 + 常用共享遗物
RELICS = [
    # ========== 静默猎手专属 (Starter) ==========
    {
        "id": "ring_of_the_drake",
        "name": "龙鳞戒指",
        "name_en": "Ring of the Drake",
        "pool": "silent",
        "rarity": "初始",
        "effect": "在前3回合开始时，额外抽2张牌。",
        "description": "静默猎手初始遗物",
        "synergy": "前期过牌，帮助建立节奏",
        "image_url": "https://spire-codex.com/static/images/relics/ring_of_the_drake.webp"
    },

    # ========== 静默猎手专属 (Common) ==========
    {
        "id": "coup_de_grace",
        "name": "致命一击",
        "name_en": "Coup de Grace",
        "pool": "silent",
        "rarity": "普通",
        "effect": "每场战斗中第一次打出攻击牌时，额外造成8点伤害。",
        "description": "攻击流遗物",
        "synergy": "配合高伤害攻击牌，前期提升输出",
        "image_url": "https://spire-codex.com/static/images/relics/coup_de_grace.webp"
    },
    {
        "id": "tough_bandages",
        "name": "结实绷带",
        "name_en": "Tough Bandages",
        "pool": "silent",
        "rarity": "普通",
        "effect": "每回合每弃一张牌，获得3点格挡。",
        "description": "弃牌流核心遗物",
        "synergy": "弃牌流必备，配合计算赌博、早有准备",
        "image_url": "https://spire-codex.com/static/images/relics/tough_bandages.webp"
    },
    {
        "id": "twisted_funnel",
        "name": "扭曲漏斗",
        "name_en": "Twisted Funnel",
        "pool": "silent",
        "rarity": "普通",
        "effect": "每场战斗开始时，给予所有敌人4层中毒。",
        "description": "毒流启动遗物",
        "synergy": "毒流必备，快速启动毒层数",
        "image_url": "https://spire-codex.com/static/images/relics/twisted_funnel.webp"
    },

    # ========== 静默猎手专属 (Uncommon) ==========
    {
        "id": "tingsha",
        "name": " Tibetan 法铃",
        "name_en": "Tingsha",
        "pool": "silent",
        "rarity": "罕见",
        "effect": "你在回合内每弃一张牌，对随机敌人造成3点伤害。",
        "description": "弃牌流伤害遗物",
        "synergy": "弃牌流核心输出，配合大量弃牌",
        "image_url": "https://spire-codex.com/static/images/relics/tingsha.webp"
    },
    {
        "id": "ornamental_fan",
        "name": "装饰扇",
        "name_en": "Ornamental Fan",
        "pool": "silent",
        "rarity": "罕见",
        "effect": "每回合打出3张攻击牌后，获得4点格挡。",
        "description": "攻击流防御遗物",
        "synergy": "Shiv流和多攻击牌流，自动获得格挡",
        "image_url": "https://spire-codex.com/static/images/relics/ornamental_fan.webp"
    },
    {
        "id": "shuriken",
        "name": "手里剑",
        "name_en": "Shuriken",
        "pool": "silent",
        "rarity": "罕见",
        "effect": "每场战斗中每打出3张攻击牌，获得1点力量。",
        "description": "攻击流成长遗物",
        "synergy": "Shiv流和多攻击牌流，持续提升伤害",
        "image_url": "https://spire-codex.com/static/images/relics/shuriken.webp"
    },
    {
        "id": "kunai",
        "name": "苦无",
        "name_en": "Kunai",
        "pool": "silent",
        "rarity": "罕见",
        "effect": "每场战斗中每打出3张技能牌，获得1点敏捷。",
        "description": "技能流成长遗物",
        "synergy": "技能牌多的卡组，持续提升格挡",
        "image_url": "https://spire-codex.com/static/images/relics/kunai.webp"
    },
    {
        "id": "letter_opener",
        "name": "拆信刀",
        "name_en": "Letter Opener",
        "pool": "silent",
        "rarity": "罕见",
        "effect": "每回合打出3张技能牌后，对所有敌人造成5点伤害。",
        "description": "技能流伤害遗物",
        "synergy": "技能牌多的卡组，附加AOE伤害",
        "image_url": "https://spire-codex.com/static/images/relics/letter_opener.webp"
    },

    # ========== 静默猎手专属 (Rare) ==========
    {
        "id": "snecko_eye",
        "name": "蛇眼",
        "name_en": "Snecko Eye",
        "pool": "silent",
        "rarity": "稀有",
        "effect": "每场战斗开始时，获得1点混乱。每回合开始时多抽2张牌。",
        "description": "高风险高回报遗物",
        "synergy": "配合高费牌，混乱可能降低费用",
        "image_url": "https://spire-codex.com/static/images/relics/snecko_eye.webp"
    },
    {
        "id": "wrist_blade",
        "name": "腕刃",
        "name_en": "Wrist Blade",
        "pool": "silent",
        "rarity": "稀有",
        "effect": "你打出的0费牌额外造成3点伤害。",
        "description": "0费牌流遗物",
        "synergy": "Shiv流和0费攻击牌流，大幅提升伤害",
        "image_url": "https://spire-codex.com/static/images/relics/wrist_blade.webp"
    },
    {
        "id": "the_boot",
        "name": "铁靴",
        "name_en": "The Boot",
        "pool": "silent",
        "rarity": "稀有",
        "effect": "如果攻击伤害低于5，则造成5点伤害。",
        "description": "低伤害攻击补强",
        "synergy": "配合多段低伤害攻击，提升最低伤害",
        "image_url": "https://spire-codex.com/static/images/relics/the_boot.webp"
    },

    # ========== 共享遗物 (Common) ==========
    {
        "id": "akabeko",
        "name": "赤牛",
        "name_en": "Akabeko",
        "pool": "shared",
        "rarity": "普通",
        "effect": "每场战斗开始时，获得8点活力。",
        "description": "通用攻击加成",
        "synergy": "前期提升伤害，所有流派通用",
        "image_url": "https://spire-codex.com/static/images/relics/akabeko.webp"
    },
    {
        "id": "bag_of_marbles",
        "name": "弹珠袋",
        "name_en": "Bag of Marbles",
        "pool": "shared",
        "rarity": "普通",
        "effect": "每场战斗开始时，给予所有敌人1层易伤。",
        "description": "通用易伤启动",
        "synergy": "提升全队伤害，Boss战尤其有用",
        "image_url": "https://spire-codex.com/static/images/relics/bag_of_marbles.webp"
    },
    {
        "id": "anchor",
        "name": "船锚",
        "name_en": "Anchor",
        "pool": "shared",
        "rarity": "普通",
        "effect": "每场战斗开始时，获得10点格挡。",
        "description": "通用防御启动",
        "synergy": "前期保命，所有流派通用",
        "image_url": "https://spire-codex.com/static/images/relics/anchor.webp"
    },
    {
        "id": "pen_nib",
        "name": "钢笔尖",
        "name_en": "Pen Nib",
        "pool": "shared",
        "rarity": "普通",
        "effect": "每打出10张攻击牌后，下一张攻击牌伤害翻倍。",
        "description": "攻击流爆发遗物",
        "synergy": "多攻击牌流，周期性爆发伤害",
        "image_url": "https://spire-codex.com/static/images/relics/pen_nib.webp"
    },
    {
        "id": "vajra",
        "name": "金刚杵",
        "name_en": "Vajra",
        "pool": "shared",
        "rarity": "普通",
        "effect": "每场战斗开始时，获得1点力量。",
        "description": "通用力量加成",
        "synergy": "永久提升攻击伤害",
        "image_url": "https://spire-codex.com/static/images/relics/vajra.webp"
    },

    # ========== 共享遗物 (Uncommon) ==========
    {
        "id": "meat_on_the_bone",
        "name": "骨头上的肉",
        "name_en": "Meat on the Bone",
        "pool": "shared",
        "rarity": "罕见",
        "effect": "战斗结束时，如果生命值低于50%，恢复12点生命。",
        "description": "战后恢复遗物",
        "synergy": "低血量时保命，减少回血消耗",
        "image_url": "https://spire-codex.com/static/images/relics/meat_on_the_bone.webp"
    },
    {
        "id": "horn_cleat",
        "name": "角形防滑钉",
        "name_en": "Horn Cleat",
        "pool": "shared",
        "rarity": "罕见",
        "effect": "每场战斗开始时，获得1点敏捷。",
        "description": "通用敏捷加成",
        "synergy": "永久提升格挡效率",
        "image_url": "https://spire-codex.com/static/images/relics/horn_cleat.webp"
    },
    {
        "id": "blood_vial",
        "name": "血瓶",
        "name_en": "Blood Vial",
        "pool": "shared",
        "rarity": "罕见",
        "effect": "每场战斗开始时，恢复2点生命。",
        "description": "战后恢复遗物",
        "synergy": "持续回血，减少回血消耗",
        "image_url": "https://spire-codex.com/static/images/relics/blood_vial.webp"
    },
    {
        "id": "golden_idol",
        "name": "黄金偶像",
        "name_en": "Golden Idol",
        "pool": "shared",
        "rarity": "罕见",
        "effect": "获得25金币。每场战斗开始时，如果金币多于250，获得1点力量。",
        "description": "金币流遗物",
        "synergy": "攒金币获得力量加成",
        "image_url": "https://spire-codex.com/static/images/relics/golden_idol.webp"
    },

    # ========== 共享遗物 (Rare) ==========
    {
        "id": "dead_branch",
        "name": "枯枝",
        "name_en": "Dead Branch",
        "pool": "shared",
        "rarity": "稀有",
        "effect": "每当你消耗一张牌，将一张随机牌加入手牌。",
        "description": "消耗流核心遗物",
        "synergy": "配合大量消耗牌，产生资源循环",
        "image_url": "https://spire-codex.com/static/images/relics/dead_branch.webp"
    },
    {
        "id": "runic_pyramid",
        "name": "符文金字塔",
        "name_en": "Runic Pyramid",
        "pool": "shared",
        "rarity": "稀有",
        "effect": "你不再在回合结束时弃牌。",
        "description": "保留手牌遗物",
        "synergy": "配合需要特定组合的卡组，保留关键牌",
        "image_url": "https://spire-codex.com/static/images/relics/runic_pyramid.webp"
    },
    {
        "id": "ice_cream",
        "name": "冰淇淋",
        "name_en": "Ice Cream",
        "pool": "shared",
        "rarity": "稀有",
        "effect": "能量在回合间保留。",
        "description": "能量保留遗物",
        "synergy": "配合高费爆发牌，攒能量一轮爆发",
        "image_url": "https://spire-codex.com/static/images/relics/ice_cream.webp"
    },
    {
        "id": "bird_faced_urn",
        "name": "鸟面瓮",
        "name_en": "Bird-Faced Urn",
        "pool": "shared",
        "rarity": "稀有",
        "effect": "你每打出一张能力牌，恢复2点生命。",
        "description": "能力牌回血遗物",
        "synergy": "能力牌多的卡组，持续回血",
        "image_url": "https://spire-codex.com/static/images/relics/bird_faced_urn.webp"
    },

    # ========== 共享遗物 (Boss) ==========
    {
        "id": "runic_dome",
        "name": "符文圆顶",
        "name_en": "Runic Dome",
        "pool": "shared",
        "rarity": "Boss",
        "effect": "获得1点能量。你无法看到敌人的意图。",
        "description": "高风险高能量Boss遗物",
        "synergy": "熟悉怪物行动模式时可选，+1能量很强",
        "image_url": "https://spire-codex.com/static/images/relics/runic_dome.webp"
    },
    {
        "id": "slavers_collar",
        "name": "奴隶主项圈",
        "name_en": "Slaver's Collar",
        "pool": "shared",
        "rarity": "Boss",
        "effect": "在精英和Boss战斗中，每回合开始时多抽1张牌。",
        "description": "精英/Boss战过牌",
        "synergy": "提升关键战斗的手牌质量",
        "image_url": "https://spire-codex.com/static/images/relics/slavers_collar.webp"
    },
    {
        "id": "philosophers_stone",
        "name": "贤者之石",
        "name_en": "Philosopher's Stone",
        "pool": "shared",
        "rarity": "Boss",
        "effect": "获得1点能量。所有敌人获得1点力量。",
        "description": "高风险高能量Boss遗物",
        "synergy": "防御足够时可选，+1能量很强",
        "image_url": "https://spire-codex.com/static/images/relics/philosophers_stone.webp"
    },

    # ========== 事件/商店遗物 ==========
    {
        "id": "membership_card",
        "name": "会员卡",
        "name_en": "Membership Card",
        "pool": "shared",
        "rarity": "商店",
        "effect": "商店价格减半。",
        "description": "商店折扣遗物",
        "synergy": "商店流核心，大幅降低购物成本",
        "image_url": "https://spire-codex.com/static/images/relics/membership_card.webp"
    },
    {
        "id": "embers",
        "name": "余烬",
        "name_en": "Embers",
        "pool": "shared",
        "rarity": "事件",
        "effect": "你消耗的牌造成4点伤害。",
        "description": "消耗流伤害遗物",
        "synergy": "配合消耗牌，附加伤害",
        "image_url": "https://spire-codex.com/static/images/relics/embers.webp"
    },
]


def get_relic_by_name(name: str) -> dict:
    """根据名称查找遗物"""
    for r in RELICS:
        if r["name"] == name or r["name_en"] == name or r["id"] == name:
            return r
    for r in RELICS:
        if name in r["name"] or name in r["name_en"]:
            return r
    return None


def get_relics_by_pool(pool: str) -> list:
    """按角色池筛选"""
    return [r for r in RELICS if r["pool"] == pool]


def get_relics_by_rarity(rarity: str) -> list:
    """按稀有度筛选"""
    return [r for r in RELICS if r["rarity"] == rarity]


def search_relics(query: str) -> list:
    """搜索遗物"""
    query = query.lower()
    return [r for r in RELICS if
            query in r["name"].lower() or
            query in r["name_en"].lower() or
            query in r["effect"].lower() or
            query in r.get("synergy", "").lower()]


# 遗物统计
RELIC_STATS = {
    "total": len(RELICS),
    "silent": len([r for r in RELICS if r["pool"] == "silent"]),
    "shared": len([r for r in RELICS if r["pool"] == "shared"]),
    "starter": len([r for r in RELICS if r["rarity"] == "初始"]),
    "common": len([r for r in RELICS if r["rarity"] == "普通"]),
    "uncommon": len([r for r in RELICS if r["rarity"] == "罕见"]),
    "rare": len([r for r in RELICS if r["rarity"] == "稀有"]),
    "boss": len([r for r in RELICS if r["rarity"] == "Boss"]),
}
