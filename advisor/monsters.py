"""
怪物行为数据库 - 杀戮尖塔2
基于 slaythespire2.gg 真实数据 (Beta v0.111)
章节：密林(Overgrowth)、巢穴(Hive)、荣耀(Glory)、暗港(Underdocks)
"""

MONSTER_DB = [
    # ========== 第一幕：密林 (Overgrowth) ==========
    {
        "id": "inklet",
        "name": "墨宝",
        "act": "密林",
        "type": "普通",
        "hp_min": 11, "hp_max": 17,
        "hp_asc_min": 12, "hp_asc_max": 18,
        "abilities": ["滑溜×1"],
        "moves": [
            {"name": "刺击!", "desc": "普通攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "旋风", "desc": "AOE攻击", "damage": 2, "hits": 0, "intent": "attack"},
            {"name": "锐利凝视", "desc": "施加debuff", "damage": 10, "hits": 0, "intent": "debuff"},
        ],
        "tip": "低血量小怪，滑溜使攻击有几率未命中，优先快速清理"
    },
    {
        "id": "snapping-jaxfruit",
        "name": "闪光贾克斯果",
        "act": "密林",
        "type": "普通",
        "hp_min": 31, "hp_max": 33,
        "hp_asc_min": 34, "hp_asc_max": 36,
        "abilities": [],
        "moves": [
            {"name": "能量球!", "desc": "攻击+充能", "damage": 0, "hits": 1, "intent": "attack"},
        ],
        "tip": "会充能后释放高伤害，注意在充能回合多叠格挡"
    },
    {
        "id": "vine-shambler",
        "name": "藤蔓蹒跚者",
        "act": "密林",
        "type": "普通",
        "hp_min": 61, "hp_max": 61,
        "hp_asc_min": 64, "hp_asc_max": 64,
        "abilities": [],
        "moves": [
            {"name": "紧绕藤蔓!", "desc": "攻击+缠绕", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "挥击", "desc": "普通攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "大啃", "desc": "高伤害攻击", "damage": 0, "hits": 1, "intent": "attack"},
        ],
        "tip": "中等血量，缠绕会限制出牌，优先输出"
    },
    {
        "id": "mawler",
        "name": "蛮兽",
        "act": "密林",
        "type": "普通",
        "hp_min": 72, "hp_max": 72,
        "hp_asc_min": 76, "hp_asc_max": 76,
        "abilities": [],
        "moves": [
            {"name": "狂乱撕扯!", "desc": "多段攻击", "damage": 0, "hits": 0, "intent": "attack"},
            {"name": "怒吼", "desc": "自身增益", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "爪击", "desc": "普通攻击", "damage": 4, "hits": 1, "intent": "attack"},
        ],
        "tip": "怒吼后伤害提升，注意在怒吼后回合保持高格挡"
    },
    {
        "id": "wriggler",
        "name": "扭动虫",
        "act": "密林",
        "type": "普通",
        "hp_min": 17, "hp_max": 21,
        "hp_asc_min": 18, "hp_asc_max": 22,
        "abilities": [],
        "moves": [
            {"name": "污秽啃咬!", "desc": "攻击+施加毒", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "扭动", "desc": "闪避姿态", "damage": 0, "hits": 0, "intent": "defend"},
            {"name": "生成", "desc": "召唤小怪", "damage": 0, "hits": 0, "intent": "buff"},
        ],
        "tip": "会施毒，毒流派可以利用，但注意自身毒层数"
    },
    {
        "id": "fuzzy-wurm-crawler",
        "name": "毛绒伏地虫",
        "act": "密林",
        "type": "弱化",
        "hp_min": 55, "hp_max": 57,
        "hp_asc_min": 58, "hp_asc_max": 59,
        "abilities": [],
        "moves": [
            {"name": "酸液黏球!", "desc": "攻击+施加易伤", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "酸液黏球", "desc": "攻击+施加易伤", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "吸入", "desc": "抽牌/弃牌效果", "damage": 0, "hits": 0, "intent": "debuff"},
        ],
        "tip": "会施加易伤，被易伤后受到伤害增加，注意清理易伤"
    },
    {
        "id": "crossbow-ruby-raider",
        "name": "劫掠者弩手",
        "act": "密林",
        "type": "普通",
        "hp_min": 18, "hp_max": 21,
        "hp_asc_min": 19, "hp_asc_max": 22,
        "abilities": [],
        "moves": [
            {"name": "射击！", "desc": "远程攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "装填", "desc": "下回合高伤害", "damage": 0, "hits": 0, "intent": "buff"},
        ],
        "tip": "装填后射击伤害很高，装填回合多叠格挡或直接击杀"
    },
    {
        "id": "tracker-ruby-raider",
        "name": "劫掠者追踪手",
        "act": "密林",
        "type": "普通",
        "hp_min": 21, "hp_max": 25,
        "hp_asc_min": 22, "hp_asc_max": 26,
        "abilities": [],
        "moves": [
            {"name": "追踪!", "desc": "标记目标", "damage": 0, "hits": 0, "intent": "debuff"},
            {"name": "放狗", "desc": "召唤/攻击", "damage": 0, "hits": 0, "intent": "attack"},
        ],
        "tip": "追踪后会有额外伤害，优先击杀"
    },
    {
        "id": "bygone-effigy",
        "name": "旧日雕像",
        "act": "密林",
        "type": "精英",
        "hp_min": 127, "hp_max": 127,
        "hp_asc_min": 132, "hp_asc_max": 132,
        "abilities": ["缓慢×1"],
        "moves": [
            {"name": "苏醒!", "desc": "从沉睡中苏醒", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "斩击", "desc": "普通攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "斩击", "desc": "普通攻击", "damage": 0, "hits": 1, "intent": "attack"},
        ],
        "tip": "开始时沉睡，前几回合可以自由输出，苏醒后伤害较高"
    },
    {
        "id": "byrdonis",
        "name": "多尼斯异鸟",
        "act": "密林",
        "type": "精英",
        "hp_min": 81, "hp_max": 84,
        "hp_asc_min": 90, "hp_asc_max": 90,
        "abilities": ["领地意识×1"],
        "moves": [
            {"name": "啄击!", "desc": "多段攻击", "damage": 0, "hits": 0, "intent": "attack"},
            {"name": "飞扑", "desc": "高伤害攻击", "damage": 17, "hits": 1, "intent": "attack"},
        ],
        "tip": "领地意识会在你使用特定牌时反击，注意出牌选择"
    },
    {
        "id": "phrog-parasite",
        "name": "异蛙寄生虫",
        "act": "密林",
        "type": "精英",
        "hp_min": 61, "hp_max": 64,
        "hp_asc_min": 66, "hp_asc_max": 68,
        "abilities": ["寄生物×4"],
        "moves": [
            {"name": "感染!", "desc": "施加寄生虫", "damage": 0, "hits": 0, "intent": "debuff"},
            {"name": "甩动", "desc": "普通攻击", "damage": 0, "hits": 1, "intent": "attack"},
        ],
        "tip": "寄生虫会持续造成伤害，快速击杀减少感染次数"
    },
    {
        "id": "ceremonial-beast",
        "name": "仪式兽",
        "act": "密林",
        "type": "Boss",
        "hp_min": 252, "hp_max": 252,
        "hp_asc_min": 262, "hp_asc_max": 262,
        "abilities": [],
        "moves": [
            {"name": "跺地!", "desc": "AOE攻击", "damage": 0, "hits": 0, "intent": "attack"},
            {"name": "横冲直撞", "desc": "高伤害攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "野兽咆哮", "desc": "自身增益+攻击", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "踩踏", "desc": "普通攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "碾碎", "desc": "高伤害攻击", "damage": 0, "hits": 1, "intent": "attack"},
        ],
        "tip": "HP低于150时会眩晕，然后进入限制1张牌的阶段，前期尽量多输出"
    },
    {
        "id": "vantom",
        "name": "墨影幻灵",
        "act": "密林",
        "type": "Boss",
        "hp_min": 173, "hp_max": 173,
        "hp_asc_min": 183, "hp_asc_max": 183,
        "abilities": ["滑溜×8"],
        "moves": [
            {"name": "墨迹!", "desc": "攻击+施加滑溜", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "墨水长枪", "desc": "高伤害攻击", "damage": 6, "hits": 1, "intent": "attack"},
            {"name": "肢解", "desc": "多段攻击", "damage": 26, "hits": 0, "intent": "attack"},
            {"name": "准备", "desc": "充能下回合大招", "damage": 0, "hits": 0, "intent": "buff"},
        ],
        "tip": "滑溜层数高，攻击容易未命中，准备回合后是大招，注意格挡"
    },
    {
        "id": "living-fog",
        "name": "同族神官",
        "act": "密林",
        "type": "Boss",
        "hp_min": 190, "hp_max": 190,
        "hp_asc_min": 199, "hp_asc_max": 199,
        "abilities": [],
        "moves": [
            {"name": "脆弱球!", "desc": "施加脆弱", "damage": 0, "hits": 0, "intent": "debuff"},
            {"name": "虚弱球", "desc": "施加虚弱", "damage": 0, "hits": 0, "intent": "debuff"},
            {"name": "灵魂光束", "desc": "高伤害攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "黑暗仪式", "desc": "自身增益", "damage": 0, "hits": 0, "intent": "buff"},
        ],
        "tip": "会持续施加debuff，注意清理debuff或快速击杀"
    },

    # ========== 第二幕：巢穴 (Hive) ==========
    {
        "id": "corpse-slug",
        "name": "尸体蛞蝓",
        "act": "巢穴",
        "type": "普通",
        "hp_min": 0, "hp_max": 0,
        "hp_asc_min": 0, "hp_asc_max": 0,
        "abilities": ["饥饿×4"],
        "moves": [
            {"name": "鞭打!", "desc": "普通攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "扑上", "desc": "高伤害攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "黏液", "desc": "施加debuff", "damage": 0, "hits": 0, "intent": "debuff"},
        ],
        "tip": "饥饿会随回合增加伤害，不要拖太久"
    },
    {
        "id": "myte",
        "name": "异螨",
        "act": "巢穴",
        "type": "普通",
        "hp_min": 61, "hp_max": 67,
        "hp_asc_min": 64, "hp_asc_max": 69,
        "abilities": [],
        "moves": [
            {"name": "浓毒!", "desc": "施加大量毒", "damage": 0, "hits": 0, "intent": "debuff"},
            {"name": "啃咬", "desc": "普通攻击", "damage": 13, "hits": 1, "intent": "attack"},
            {"name": "吸吮", "desc": "吸血攻击", "damage": 4, "hits": 1, "intent": "attack"},
        ],
        "tip": "会施毒，毒流派可以反制，但注意自身毒层数"
    },
    {
        "id": "slumbering-beetle",
        "name": "熟睡甲虫",
        "act": "巢穴",
        "type": "普通",
        "hp_min": 86, "hp_max": 86,
        "hp_asc_min": 89, "hp_asc_max": 89,
        "abilities": ["覆甲×15", "熟睡×3"],
        "moves": [
            {"name": "打鼾!", "desc": "睡眠中", "damage": 0, "hits": 0, "intent": "sleep"},
            {"name": "出击", "desc": "高伤害攻击", "damage": 0, "hits": 1, "intent": "attack"},
        ],
        "tip": "前3回合熟睡，可以自由输出，覆甲提供高格挡，苏醒后伤害很高"
    },
    {
        "id": "spiny-toad",
        "name": "棘刺蟾蜍",
        "act": "巢穴",
        "type": "普通",
        "hp_min": 116, "hp_max": 119,
        "hp_asc_min": 121, "hp_asc_max": 124,
        "abilities": [],
        "moves": [
            {"name": "伸出尖刺!", "desc": "获得荆棘", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "尖刺爆破", "desc": "AOE攻击", "damage": 0, "hits": 0, "intent": "attack"},
            {"name": "吐舌", "desc": "普通攻击", "damage": 0, "hits": 1, "intent": "attack"},
        ],
        "tip": "有荆棘时攻击会反伤，用多段攻击或法术牌"
    },
    {
        "id": "ovicopter",
        "name": "直飞产卵虫",
        "act": "巢穴",
        "type": "普通",
        "hp_min": 124, "hp_max": 130,
        "hp_asc_min": 126, "hp_asc_max": 132,
        "abilities": [],
        "moves": [
            {"name": "产卵!", "desc": "召唤虫卵", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "猛砸", "desc": "高伤害攻击", "damage": 16, "hits": 1, "intent": "attack"},
            {"name": "嫩化", "desc": "施加易伤", "damage": 7, "hits": 0, "intent": "debuff"},
            {"name": "高营养糊糊", "desc": "治疗/增益", "damage": 0, "hits": 0, "intent": "buff"},
        ],
        "tip": "会产卵召唤小怪，优先击杀虫卵或快速击杀本体"
    },
    {
        "id": "decimillipede-segment",
        "name": "残杀千足虫",
        "act": "巢穴",
        "type": "精英",
        "hp_min": 40, "hp_max": 46,
        "hp_asc_min": 46, "hp_asc_max": 52,
        "abilities": ["接续×25"],
        "moves": [
            {"name": "扭动!", "desc": "多段攻击", "damage": 0, "hits": 0, "intent": "attack"},
            {"name": "胀大", "desc": "自身增益", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "冲撞", "desc": "高伤害攻击", "damage": 0, "hits": 1, "intent": "attack"},
        ],
        "tip": "多段攻击，每段伤害不高但总伤害可观，接续会分裂，注意AOE"
    },
    {
        "id": "entomancer",
        "name": "蜂群术士",
        "act": "巢穴",
        "type": "精英",
        "hp_min": 145, "hp_max": 145,
        "hp_asc_min": 165, "hp_asc_max": 165,
        "abilities": ["人体蜂房×2"],
        "moves": [
            {"name": "喷射信息素!", "desc": "施加debuff", "damage": 0, "hits": 0, "intent": "debuff"},
            {"name": "蜜——蜂——！", "desc": "召唤蜂群", "damage": 3, "hits": 0, "intent": "buff"},
            {"name": "矛击！", "desc": "普通攻击", "damage": 18, "hits": 1, "intent": "attack"},
        ],
        "tip": "会召唤蜂群小怪，注意清理，人体蜂房会持续生成小怪"
    },
    {
        "id": "infested-prism",
        "name": "感染棱柱",
        "act": "巢穴",
        "type": "精英",
        "hp_min": 200, "hp_max": 200,
        "hp_asc_min": 215, "hp_asc_max": 215,
        "abilities": ["活力火花×1"],
        "moves": [
            {"name": "刺击!", "desc": "普通攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "辐射", "desc": "AOE攻击", "damage": 0, "hits": 0, "intent": "attack"},
            {"name": "旋风", "desc": "多段攻击", "damage": 0, "hits": 0, "intent": "attack"},
            {"name": "脉动", "desc": "自身增益", "damage": 0, "hits": 0, "intent": "buff"},
        ],
        "tip": "高血量精英，活力火花会回复生命，注意持续输出"
    },
    {
        "id": "crusher",
        "name": "碾碎爪",
        "act": "巢穴",
        "type": "Boss",
        "hp_min": 209, "hp_max": 209,
        "hp_asc_min": 219, "hp_asc_max": 219,
        "abilities": ["后方攻击×1", "蟹之怒×1"],
        "moves": [
            {"name": "撕扯!", "desc": "多段攻击", "damage": 0, "hits": 0, "intent": "attack"},
            {"name": "巨化打击", "desc": "高伤害攻击", "damage": 4, "hits": 1, "intent": "attack"},
            {"name": "虫蛰", "desc": "攻击+施毒", "damage": 6, "hits": 1, "intent": "attack"},
            {"name": "适应", "desc": "获得格挡/增益", "damage": 0, "hits": 0, "intent": "defend"},
            {"name": "戒备打击", "desc": "攻击+格挡", "damage": 12, "hits": 1, "intent": "attack"},
        ],
        "tip": "蟹之怒会在低血量时增加伤害，后期注意保持高格挡"
    },
    {
        "id": "rocket",
        "name": "火箭",
        "act": "巢穴",
        "type": "Boss",
        "hp_min": 199, "hp_max": 199,
        "hp_asc_min": 209, "hp_asc_max": 209,
        "abilities": ["后方攻击×1", "蟹之怒×1", "遭到包围×1"],
        "moves": [
            {"name": "瞄准十字!", "desc": "标记目标", "damage": 0, "hits": 0, "intent": "debuff"},
            {"name": "精准光束", "desc": "高伤害攻击", "damage": 18, "hits": 1, "intent": "attack"},
            {"name": "蓄能", "desc": "充能", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "激光", "desc": "AOE攻击", "damage": 31, "hits": 0, "intent": "attack"},
            {"name": "重新充能", "desc": "恢复能量", "damage": 0, "hits": 0, "intent": "buff"},
        ],
        "tip": "蓄能后激光伤害很高，蓄能回合多叠格挡"
    },

    # ========== 第三幕：荣耀 (Glory) ==========
    {
        "id": "cubex-construct",
        "name": "立柱构造体",
        "act": "荣耀",
        "type": "普通",
        "hp_min": 65, "hp_max": 65,
        "hp_asc_min": 70, "hp_asc_max": 70,
        "abilities": ["人工制品×1"],
        "moves": [
            {"name": "蓄能!", "desc": "充能", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "重复轰击", "desc": "多段攻击", "damage": 0, "hits": 0, "intent": "attack"},
            {"name": "排出", "desc": "释放充能", "damage": 0, "hits": 0, "intent": "attack"},
        ],
        "tip": "人工制品会抵消第一次debuff，蓄能后伤害递增"
    },
    {
        "id": "fabricator",
        "name": "组装师",
        "act": "荣耀",
        "type": "普通",
        "hp_min": 150, "hp_max": 150,
        "hp_asc_min": 155, "hp_asc_max": 155,
        "abilities": [],
        "moves": [
            {"name": "组装!", "desc": "召唤构造体", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "组装打击", "desc": "攻击", "damage": 18, "hits": 1, "intent": "attack"},
            {"name": "瓦解", "desc": "施加debuff", "damage": 11, "hits": 0, "intent": "debuff"},
        ],
        "tip": "会召唤小怪，优先清理或快速击杀本体"
    },
    {
        "id": "globe-head",
        "name": "电球头",
        "act": "荣耀",
        "type": "普通",
        "hp_min": 148, "hp_max": 148,
        "hp_asc_min": 158, "hp_asc_max": 158,
        "abilities": ["流电×6"],
        "moves": [
            {"name": "生成闪电!", "desc": "召唤闪电", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "电击掌", "desc": "攻击+感电", "damage": 0, "hits": 1, "intent": "attack"},
        ],
        "tip": "流电会在受到攻击时反击，用单次高伤害攻击"
    },
    {
        "id": "flail-knight",
        "name": "连枷骑士",
        "act": "荣耀",
        "type": "精英",
        "hp_min": 101, "hp_max": 101,
        "hp_asc_min": 108, "hp_asc_max": 108,
        "abilities": [],
        "moves": [
            {"name": "战争吟唱!", "desc": "自身增益", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "连枷", "desc": "多段攻击", "damage": 0, "hits": 0, "intent": "attack"},
            {"name": "撞击", "desc": "普通攻击", "damage": 0, "hits": 1, "intent": "attack"},
        ],
        "tip": "战争吟唱后伤害提升，注意在吟唱后保持格挡"
    },
    {
        "id": "magi-knight",
        "name": "魔法骑士",
        "act": "荣耀",
        "type": "精英",
        "hp_min": 82, "hp_max": 82,
        "hp_asc_min": 89, "hp_asc_max": 89,
        "abilities": [],
        "moves": [
            {"name": "强力护盾!", "desc": "获得大量格挡", "damage": 0, "hits": 0, "intent": "defend"},
            {"name": "抑制", "desc": "施加debuff", "damage": 0, "hits": 0, "intent": "debuff"},
            {"name": "魔法炸弹", "desc": "AOE攻击", "damage": 0, "hits": 0, "intent": "attack"},
            {"name": "撞击", "desc": "普通攻击", "damage": 0, "hits": 1, "intent": "attack"},
        ],
        "tip": "会获得高格挡，抑制会限制出牌，注意爆发输出"
    },
    {
        "id": "mecha-knight",
        "name": "机甲骑士",
        "act": "荣耀",
        "type": "精英",
        "hp_min": 300, "hp_max": 300,
        "hp_asc_min": 320, "hp_asc_max": 320,
        "abilities": ["人工制品×3"],
        "moves": [
            {"name": "冲锋!", "desc": "高伤害攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "喷火器", "desc": "AOE攻击", "damage": 0, "hits": 0, "intent": "attack"},
            {"name": "举起蓄力", "desc": "充能", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "重斩", "desc": "超高伤害攻击", "damage": 0, "hits": 1, "intent": "attack"},
        ],
        "tip": "高血量精英，举起蓄力后重斩伤害极高，蓄力回合必须满格挡"
    },
    {
        "id": "queen",
        "name": "女王",
        "act": "荣耀",
        "type": "Boss",
        "hp_min": 400, "hp_max": 400,
        "hp_asc_min": 419, "hp_asc_max": 419,
        "abilities": [],
        "moves": [
            {"name": "屏障!", "desc": "获得格挡", "damage": 0, "hits": 0, "intent": "defend"},
            {"name": "你是我的了", "desc": "控制效果", "damage": 0, "hits": 0, "intent": "debuff"},
            {"name": "为我尽力燃烧吧", "desc": "施加燃烧", "damage": 0, "hits": 0, "intent": "debuff"},
            {"name": "将头砍下", "desc": "高伤害攻击", "damage": 3, "hits": 1, "intent": "attack"},
            {"name": "处决", "desc": "斩杀攻击", "damage": 15, "hits": 1, "intent": "attack"},
        ],
        "tip": "高血量Boss，会控制和燃烧，注意清理debuff，处决对低血量威胁大"
    },

    # ========== 第四幕：暗港 (Underdocks) ==========
    {
        "id": "calcified-cultist",
        "name": "钙化邪教徒",
        "act": "暗港",
        "type": "普通",
        "hp_min": 38, "hp_max": 41,
        "hp_asc_min": 39, "hp_asc_max": 42,
        "abilities": [],
        "moves": [
            {"name": "念咒!", "desc": "自身增益", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "黑暗打击", "desc": "攻击", "damage": 0, "hits": 1, "intent": "attack"},
        ],
        "tip": "念咒会增加力量，优先快速击杀"
    },
    {
        "id": "gremlin-merc",
        "name": "地精佣兵",
        "act": "暗港",
        "type": "普通",
        "hp_min": 47, "hp_max": 49,
        "hp_asc_min": 51, "hp_asc_max": 53,
        "abilities": ["意外×1"],
        "moves": [
            {"name": "拿来!", "desc": "偷取/攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "双重猛击", "desc": "两段攻击", "damage": 0, "hits": 2, "intent": "attack"},
            {"name": "嘿嘿", "desc": "闪避姿态", "damage": 0, "hits": 0, "intent": "defend"},
        ],
        "tip": "意外会有随机效果，双重猛击注意格挡"
    },
    {
        "id": "terror-eel",
        "name": "骇鳗",
        "act": "暗港",
        "type": "精英",
        "hp_min": 140, "hp_max": 140,
        "hp_asc_min": 150, "hp_asc_max": 150,
        "abilities": ["尖叫×70"],
        "moves": [
            {"name": "撞击!", "desc": "普通攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "撕扯", "desc": "多段攻击", "damage": 0, "hits": 0, "intent": "attack"},
            {"name": "恐吓", "desc": "施加恐惧", "damage": 0, "hits": 0, "intent": "debuff"},
        ],
        "tip": "尖叫层数极高，攻击容易未命中，用必中攻击或法术"
    },
    {
        "id": "soul-fysh",
        "name": "灵魂异鱼",
        "act": "暗港",
        "type": "Boss",
        "hp_min": 211, "hp_max": 211,
        "hp_asc_min": 221, "hp_asc_max": 221,
        "abilities": [],
        "moves": [
            {"name": "呼唤!", "desc": "召唤灵魂", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "排气", "desc": "施加debuff", "damage": 0, "hits": 0, "intent": "debuff"},
            {"name": "凝视", "desc": "标记目标", "damage": 0, "hits": 0, "intent": "debuff"},
            {"name": "消逝", "desc": "消失/无敌", "damage": 0, "hits": 0, "intent": "defend"},
            {"name": "尖叫", "desc": "AOE攻击", "damage": 0, "hits": 0, "intent": "attack"},
        ],
        "tip": "会消逝无敌，注意输出时机，呼唤会召唤小怪"
    },
    {
        "id": "waterfall-giant",
        "name": "瀑布巨兽",
        "act": "暗港",
        "type": "Boss",
        "hp_min": 240, "hp_max": 240,
        "hp_asc_min": 250, "hp_asc_max": 250,
        "abilities": [],
        "moves": [
            {"name": "增压!", "desc": "充能", "damage": 0, "hits": 0, "intent": "buff"},
            {"name": "践踏", "desc": "AOE攻击", "damage": 0, "hits": 0, "intent": "attack"},
            {"name": "撞击", "desc": "普通攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "虹吸", "desc": "吸血攻击", "damage": 0, "hits": 1, "intent": "attack"},
            {"name": "压力炮", "desc": "高伤害攻击", "damage": 0, "hits": 1, "intent": "attack"},
        ],
        "tip": "增压后压力炮伤害极高，增压回合必须满格挡"
    },
]


def get_monster_by_name(name: str) -> dict:
    """根据名称查找怪物"""
    for m in MONSTER_DB:
        if m["name"] == name or name in m["name"]:
            return m
    return None


def get_monsters_by_act(act: str) -> list:
    """按章节筛选怪物"""
    return [m for m in MONSTER_DB if m["act"] == act]


def get_monsters_by_type(mtype: str) -> list:
    """按类型筛选怪物"""
    return [m for m in MONSTER_DB if m["type"] == mtype]


def search_monsters(query: str) -> list:
    """搜索怪物"""
    query = query.lower()
    return [m for m in MONSTER_DB if query in m["name"].lower() or query in m.get("tip", "").lower()]


# 自动为每个怪物添加图片URL（来自spire-codex CDN）
SPIRE_CODEX_MONSTER_BASE = "https://spire-codex.com/static/images/monsters"
for _monster in MONSTER_DB:
    _mid = _monster["id"].lower().replace("-", "_")
    _monster["image_url"] = f"{SPIRE_CODEX_MONSTER_BASE}/{_mid}.webp"
    _monster["sprite_url"] = f"https://spire-codex.com/static/images/monsters/{_mid}.webp"


# 怪物统计
MONSTER_STATS = {
    "total": len(MONSTER_DB),
    "act1": len([m for m in MONSTER_DB if m["act"] == "密林"]),
    "act2": len([m for m in MONSTER_DB if m["act"] == "巢穴"]),
    "act3": len([m for m in MONSTER_DB if m["act"] == "荣耀"]),
    "act4": len([m for m in MONSTER_DB if m["act"] == "暗港"]),
    "normal": len([m for m in MONSTER_DB if m["type"] == "普通"]),
    "elite": len([m for m in MONSTER_DB if m["type"] == "精英"]),
    "boss": len([m for m in MONSTER_DB if m["type"] == "Boss"]),
}
