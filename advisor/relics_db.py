"""
遗物数据库 - 杀戮尖塔2
基于 sts2.urarawin.com 中文资料库 和 slaythespire2.gg 修正
包含静默猎手专属和常用共享遗物
"""

RELICS = [
    # ========== 静默猎手专属 ==========
    {
        "id": "ring_of_the_serpent",
        "name": "长蛇戒指",
        "name_en": "Ring of the Serpent",
        "pool": "silent",
        "rarity": "初始",
        "effect": "在战斗开始时的前3个回合，你额外抽2张牌。",
        "description": "静默猎手初始遗物",
        "synergy": "前期过牌加成，帮助建立节奏",
        "image_url": "https://spire-codex.com/static/images/relics/ring_of_the_serpent.webp"
    },
    {
        "id": "snake_skull",
        "name": "异蛇头骨",
        "name_en": "Snake Skull",
        "pool": "silent",
        "rarity": "普通",
        "effect": "每当你给予敌人中毒时，所给予的中毒层数增加1层。",
        "description": "毒流核心遗物",
        "synergy": "毒流必备，大幅提升毒叠加速度",
        "image_url": "https://spire-codex.com/static/images/relics/snake_skull.webp"
    },
    {
        "id": "tough_bandages",
        "name": "结实绷带",
        "name_en": "Tough Bandages",
        "pool": "silent",
        "rarity": "稀有",
        "effect": "你每在你的回合丢弃一张牌，就获得3点格挡。",
        "description": "弃牌流核心遗物",
        "synergy": "弃牌流必备，配合计算赌博、早有准备",
        "image_url": "https://spire-codex.com/static/images/relics/tough_bandages.webp"
    },
    {
        "id": "twisted_funnel",
        "name": "扭曲漏斗",
        "name_en": "Twisted Funnel",
        "pool": "silent",
        "rarity": "罕见",
        "effect": "在每场战斗开始时，给予所有敌人4层中毒。",
        "description": "毒流启动遗物",
        "synergy": "毒流启动，快速给所有敌人上毒",
        "image_url": "https://spire-codex.com/static/images/relics/twisted_funnel.webp"
    },
    {
        "id": "tingsha",
        "name": "铜钹",
        "name_en": "Tingsha",
        "pool": "silent",
        "rarity": "罕见",
        "effect": "你每在你的回合丢弃一张牌，就对一名随机敌人造成3点伤害。",
        "description": "弃牌流伤害遗物",
        "synergy": "弃牌流核心输出，配合大量弃牌",
        "image_url": "https://spire-codex.com/static/images/relics/tingsha.webp"
    },
    {
        "id": "ornamental_fan",
        "name": "精致折扇",
        "name_en": "Ornamental Fan",
        "pool": "shared",
        "rarity": "罕见",
        "effect": "你每在同一回合内打出3张攻击牌，就获得4点格挡。",
        "description": "攻击流防御遗物",
        "synergy": "Shiv流和多攻击牌流，自动获得格挡",
        "image_url": "https://spire-codex.com/static/images/relics/ornamental_fan.webp"
    },
    {
        "id": "shuriken",
        "name": "手里剑",
        "name_en": "Shuriken",
        "pool": "shared",
        "rarity": "稀有",
        "effect": "你每在同一回合内打出3张攻击牌，获得1点力量。",
        "description": "攻击流成长遗物",
        "synergy": "Shiv流和多攻击牌流，持续提升伤害",
        "image_url": "https://spire-codex.com/static/images/relics/shuriken.webp"
    },
    {
        "id": "kunai",
        "name": "苦无",
        "name_en": "Kunai",
        "pool": "shared",
        "rarity": "稀有",
        "effect": "你每在同一回合内打出3张攻击牌，就获得1点敏捷。",
        "description": "攻击流防御成长遗物",
        "synergy": "多攻击牌流，持续提升格挡效率",
        "image_url": "https://spire-codex.com/static/images/relics/kunai.webp"
    },
    {
        "id": "letter_opener",
        "name": "开信刀",
        "name_en": "Letter Opener",
        "pool": "shared",
        "rarity": "罕见",
        "effect": "你每在同一回合内打出3张技能牌，就对所有敌人造成5点伤害。",
        "description": "技能流伤害遗物",
        "synergy": "技能牌多的卡组，附加AOE伤害",
        "image_url": "https://spire-codex.com/static/images/relics/letter_opener.webp"
    },
    {
        "id": "snecko_eye",
        "name": "异蛇之眼",
        "name_en": "Snecko Eye",
        "pool": "shared",
        "rarity": "古代",
        "effect": "每回合多抽2张牌。每场战斗开始时获得混乱效果。",
        "description": "高风险高回报遗物",
        "synergy": "配合高费牌，混乱可能降低费用",
        "image_url": "https://spire-codex.com/static/images/relics/snecko_eye.webp"
    },
    {
        "id": "spiral_dart",
        "name": "螺线飞镖",
        "name_en": "Spiral Dart",
        "pool": "silent",
        "rarity": "稀有",
        "effect": "你每打出一张小刀，就在本回合获得1点敏捷。",
        "description": "Shiv流核心遗物",
        "synergy": "Shiv流必备，大量小刀快速叠敏捷",
        "image_url": "https://spire-codex.com/static/images/relics/spiral_dart.webp"
    },
    {
        "id": "paper_crane",
        "name": "纸鹤",
        "name_en": "Paper Crane",
        "pool": "silent",
        "rarity": "稀有",
        "effect": "有虚弱状态的敌人造成的伤害降低40%而非25%。",
        "description": "虚弱流防御遗物",
        "synergy": "配合虚弱牌，大幅降低敌人伤害",
        "image_url": "https://spire-codex.com/static/images/relics/paper_crane.webp"
    },
    {
        "id": "ninja_scroll",
        "name": "忍术卷轴",
        "name_en": "Ninja Scroll",
        "pool": "silent",
        "rarity": "商店",
        "effect": "每场战斗开始时，将3张小刀加入你的手牌。",
        "description": "Shiv流启动遗物",
        "synergy": "Shiv流启动，快速获得小刀",
        "image_url": "https://spire-codex.com/static/images/relics/ninja_scroll.webp"
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

    # ========== 共享遗物 - 普通 ==========
    {
        "id": "anchor",
        "name": "锚",
        "name_en": "Anchor",
        "pool": "shared",
        "rarity": "普通",
        "effect": "每场战斗开始时获得10点格挡。",
        "description": "通用防御启动",
        "synergy": "前期保命，所有流派通用",
        "image_url": "https://spire-codex.com/static/images/relics/anchor.webp"
    },
    {
        "id": "bag_of_marbles",
        "name": "弹珠袋",
        "name_en": "Bag of Marbles",
        "pool": "shared",
        "rarity": "普通",
        "effect": "在每场战斗开始时，给予所有敌人1层易伤。",
        "description": "通用易伤启动",
        "synergy": "提升全队伤害，Boss战尤其有用",
        "image_url": "https://spire-codex.com/static/images/relics/bag_of_marbles.webp"
    },
    {
        "id": "vajra",
        "name": "金刚杵",
        "name_en": "Vajra",
        "pool": "shared",
        "rarity": "普通",
        "effect": "在每场战斗开始时，获得1点力量。",
        "description": "通用力量加成",
        "synergy": "永久提升攻击伤害",
        "image_url": "https://spire-codex.com/static/images/relics/vajra.webp"
    },
    {
        "id": "blood_vial",
        "name": "小血瓶",
        "name_en": "Blood Vial",
        "pool": "shared",
        "rarity": "普通",
        "effect": "在每场战斗开始时，回复2点生命。",
        "description": "战后恢复遗物",
        "synergy": "持续回血，减少回血消耗",
        "image_url": "https://spire-codex.com/static/images/relics/blood_vial.webp"
    },
    {
        "id": "pen_nib",
        "name": "钢笔尖",
        "name_en": "Pen Nib",
        "pool": "shared",
        "rarity": "罕见",
        "effect": "你每打出的第10张攻击牌将会造成双倍伤害。",
        "description": "攻击流爆发遗物",
        "synergy": "多攻击牌流，周期性爆发伤害",
        "image_url": "https://spire-codex.com/static/images/relics/pen_nib.webp"
    },
    {
        "id": "red_mask",
        "name": "红面具",
        "name_en": "Red Mask",
        "pool": "shared",
        "rarity": "普通",
        "effect": "在每场战斗开始时，给予所有敌人1层虚弱。",
        "description": "通用虚弱启动",
        "synergy": "降低敌人伤害，配合纸鹤效果更好",
        "image_url": "https://spire-codex.com/static/images/relics/red_mask.webp"
    },
    {
        "id": "oddly_smooth_stone",
        "name": "意外光滑的石头",
        "name_en": "Oddly Smooth Stone",
        "pool": "shared",
        "rarity": "普通",
        "effect": "在每场战斗开始时，获得1点敏捷。",
        "description": "通用敏捷加成",
        "synergy": "永久提升格挡效率",
        "image_url": "https://spire-codex.com/static/images/relics/oddly_smooth_stone.webp"
    },
    {
        "id": "potion_belt",
        "name": "药水腰带",
        "name_en": "Potion Belt",
        "pool": "shared",
        "rarity": "普通",
        "effect": "拾起时，获得2个药水栏位。",
        "description": "药水栏位扩充",
        "synergy": "携带更多药水，增加容错",
        "image_url": "https://spire-codex.com/static/images/relics/potion_belt.webp"
    },
    {
        "id": "royal_pillow",
        "name": "皇家枕头",
        "name_en": "Royal Pillow",
        "pool": "shared",
        "rarity": "普通",
        "effect": "在休息时，额外回复15点生命。",
        "description": "休息回血加成",
        "synergy": "提升休息处回血效率",
        "image_url": "https://spire-codex.com/static/images/relics/royal_pillow.webp"
    },

    # ========== 共享遗物 - 罕见 ==========
    {
        "id": "akabeko",
        "name": "赤牛",
        "name_en": "Akabeko",
        "pool": "shared",
        "rarity": "罕见",
        "effect": "在每场战斗开始时，获得8点活力。",
        "description": "通用攻击加成",
        "synergy": "前期提升伤害，所有流派通用",
        "image_url": "https://spire-codex.com/static/images/relics/akabeko.webp"
    },
    {
        "id": "meat_on_the_bone",
        "name": "带骨肉",
        "name_en": "Meat on the Bone",
        "pool": "shared",
        "rarity": "稀有",
        "effect": "如果你在战斗结束时生命值等于或低于50%，回复12点生命。",
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
        "effect": "在每场战斗开始时，获得1点敏捷。",
        "description": "通用敏捷加成",
        "synergy": "永久提升格挡效率",
        "image_url": "https://spire-codex.com/static/images/relics/horn_cleat.webp"
    },
    {
        "id": "mercury_hourglass",
        "name": "水银沙漏",
        "name_en": "Mercury Hourglass",
        "pool": "shared",
        "rarity": "罕见",
        "effect": "在你的回合开始时，对所有敌人造成3点伤害。",
        "description": "回合开始AOE",
        "synergy": "持续输出，多敌人战尤其有用",
        "image_url": "https://spire-codex.com/static/images/relics/mercury_hourglass.webp"
    },
    {
        "id": "tuning_fork",
        "name": "音叉",
        "name_en": "Tuning Fork",
        "pool": "shared",
        "rarity": "罕见",
        "effect": "你每打出10张技能牌，获得7点格挡。",
        "description": "技能流防御遗物",
        "synergy": "技能牌多的卡组，周期性获得格挡",
        "image_url": "https://spire-codex.com/static/images/relics/tuning_fork.webp"
    },
    {
        "id": "orichalcum",
        "name": "奥利哈钢",
        "name_en": "Orichalcum",
        "pool": "shared",
        "rarity": "罕见",
        "effect": "如果你在回合结束时没有任何格挡，获得6点格挡。",
        "description": "回合末防御保底",
        "synergy": "攻击流/弃牌流，回合末自动获得格挡",
        "image_url": "https://spire-codex.com/static/images/relics/orichalcum.webp"
    },
    {
        "id": "nunchaku",
        "name": "双截棍",
        "name_en": "Nunchaku",
        "pool": "shared",
        "rarity": "罕见",
        "effect": "你每打出10张攻击牌，获得1点能量。",
        "description": "攻击流能量遗物",
        "synergy": "多攻击牌流，周期性获得能量",
        "image_url": "https://spire-codex.com/static/images/relics/nunchaku.webp"
    },

    # ========== 共享遗物 - 稀有 ==========
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
        "rarity": "古代",
        "effect": "你在回合结束时不再自动丢弃所有手牌。",
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
        "effect": "多余的能量可以留到下一回合。",
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
    {
        "id": "pocketwatch",
        "name": "怀表",
        "name_en": "Pocketwatch",
        "pool": "shared",
        "rarity": "稀有",
        "effect": "当你在本回合打出的牌少于等于3张时，则在你的下个回合开始时额外抽3张牌。",
        "description": "少牌流过牌遗物",
        "synergy": "配合高费少牌卡组，下回合大量过牌",
        "image_url": "https://spire-codex.com/static/images/relics/pocketwatch.webp"
    },
    {
        "id": "unceasing_top",
        "name": "不休陀螺",
        "name_en": "Unceasing Top",
        "pool": "shared",
        "rarity": "稀有",
        "effect": "在你的回合，当你没有手牌时，抽一张牌。",
        "description": "空手牌过牌遗物",
        "synergy": "弃牌流/消耗流，空手牌时自动补牌",
        "image_url": "https://spire-codex.com/static/images/relics/unceasing_top.webp"
    },
    {
        "id": "girya",
        "name": "壶铃",
        "name_en": "Girya",
        "pool": "shared",
        "rarity": "稀有",
        "effect": "你现在能在休息处获得力量。（最多3次）",
        "description": "休息处力量成长",
        "synergy": "攻击流，在休息处叠力量",
        "image_url": "https://spire-codex.com/static/images/relics/girya.webp"
    },
    {
        "id": "shovel",
        "name": "铲子",
        "name_en": "Shovel",
        "pool": "shared",
        "rarity": "稀有",
        "effect": "现在你可以在休息处挖掘遗物。",
        "description": "休息处挖遗物",
        "synergy": "增加遗物获取途径",
        "image_url": "https://spire-codex.com/static/images/relics/shovel.webp"
    },

    # ========== 共享遗物 - Boss/古代 ==========
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
        "rarity": "古代",
        "effect": "在每回合开始时获得1点能量。所有敌人初始获得1点力量。",
        "description": "高风险高能量Boss遗物",
        "synergy": "防御足够时可选，+1能量很强",
        "image_url": "https://spire-codex.com/static/images/relics/philosophers_stone.webp"
    },
    {
        "id": "ectoplasm",
        "name": "灵体外质",
        "name_en": "Ectoplasm",
        "pool": "shared",
        "rarity": "古代",
        "effect": "你不能再获得任何金币。在回合开始时获得1点能量。",
        "description": "金币换能量",
        "synergy": "不需要金币的卡组，+1能量很强",
        "image_url": "https://spire-codex.com/static/images/relics/ectoplasm.webp"
    },
    {
        "id": "black_star",
        "name": "黑星",
        "name_en": "Black Star",
        "pool": "shared",
        "rarity": "古代",
        "effect": "精英敌人在被打败时多掉落一件遗物。",
        "description": "精英遗物翻倍",
        "synergy": "多打精英，快速积累遗物",
        "image_url": "https://spire-codex.com/static/images/relics/black_star.webp"
    },

    # ========== 共享遗物 - 商店/事件 ==========
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
    {
        "id": "art_of_war",
        "name": "孙子兵法",
        "name_en": "Art of War",
        "pool": "shared",
        "rarity": "稀有",
        "effect": "如果你在本回合中没有打出过攻击牌，则在下一回合额外获得1点能量。",
        "description": "少攻击流能量",
        "synergy": "技能/能力流，不打攻击牌时获得能量",
        "image_url": "https://spire-codex.com/static/images/relics/art_of_war.webp"
    },
    {
        "id": "bag_of_preparation",
        "name": "准备背包",
        "name_en": "Bag of Preparation",
        "pool": "shared",
        "rarity": "普通",
        "effect": "在每场战斗开始时，额外抽2张牌。",
        "description": "战斗开始过牌",
        "synergy": "前期过牌，帮助建立节奏",
        "image_url": "https://spire-codex.com/static/images/relics/bag_of_preparation.webp"
    },
    {
        "id": "lantern",
        "name": "灯笼",
        "name_en": "Lantern",
        "pool": "shared",
        "rarity": "古代",
        "effect": "在每场战斗的第一回合获得1点能量。",
        "description": "首回合能量加成",
        "synergy": "首回合爆发，快速建立优势",
        "image_url": "https://spire-codex.com/static/images/relics/lantern.webp"
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
    "ancient": len([r for r in RELICS if r["rarity"] == "古代"]),
    "boss": len([r for r in RELICS if r["rarity"] == "Boss"]),
}
