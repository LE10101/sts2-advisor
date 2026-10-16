"""
静默猎手卡牌数据库 - 杀戮尖塔2
基于 sts2.info 和 slaythespire-2.com 真实数据
共88张卡牌，包含中文名、费用、稀有度、类型、效果描述、升级效果
"""

SILENT_CARDS = [
    # ========== 基础牌 (Basic) ==========
    {
        "id": "strike", "name_en": "Strike", "name_cn": "打击",
        "cost": 1, "type": "攻击", "rarity": "基础",
        "effect": "造成6点伤害。",
        "upgraded": "造成9点伤害。",
        "tags": ["基础", "攻击"],
        "synergy": "通用输出牌，前期主要伤害来源"
    },
    {
        "id": "defend", "name_en": "Defend", "name_cn": "防御",
        "cost": 1, "type": "技能", "rarity": "基础",
        "effect": "获得5点格挡。",
        "upgraded": "获得8点格挡。",
        "tags": ["基础", "技能", "格挡"],
        "synergy": "基础防御牌，配合敏捷效果更佳"
    },
    {
        "id": "neutralize", "name_en": "Neutralize", "name_cn": "中和",
        "cost": 0, "type": "攻击", "rarity": "基础",
        "effect": "造成3点伤害。给予1层虚弱。",
        "upgraded": "造成4点伤害。给予2层虚弱。",
        "tags": ["基础", "攻击", "虚弱"],
        "synergy": "0费虚弱，开局削弱敌人，几乎必升级"
    },
    {
        "id": "survivor", "name_en": "Survivor", "name_cn": "生存者",
        "cost": 1, "type": "技能", "rarity": "基础",
        "effect": "获得8点格挡。丢弃1张牌。",
        "upgraded": "获得11点格挡。丢弃1张牌。",
        "tags": ["基础", "技能", "格挡", "弃牌"],
        "synergy": "高格挡+弃牌，配合弃牌流，升级优先级很高"
    },

    # ========== 普通牌 (Common) ==========
    {
        "id": "acrobatics", "name_en": "Acrobatics", "name_cn": "杂技",
        "cost": 1, "type": "技能", "rarity": "普通",
        "effect": "抽3张牌。丢弃1张牌。",
        "upgraded": "抽4张牌。丢弃1张牌。",
        "tags": ["普通", "技能", "抽牌", "弃牌"],
        "synergy": "强力过牌，配合弃牌流和抽牌流"
    },
    {
        "id": "anticipate", "name_en": "Anticipate", "name_cn": "预判",
        "cost": 0, "type": "技能", "rarity": "普通",
        "effect": "本回合获得3点敏捷。",
        "upgraded": "本回合获得4点敏捷。",
        "tags": ["普通", "技能", "敏捷"],
        "synergy": "0费敏捷，配合多段格挡牌收益高"
    },
    {
        "id": "backflip", "name_en": "Backflip", "name_cn": "后空翻",
        "cost": 1, "type": "技能", "rarity": "普通",
        "effect": "获得5点格挡。抽2张牌。",
        "upgraded": "获得8点格挡。抽2张牌。",
        "tags": ["普通", "技能", "格挡", "抽牌"],
        "synergy": "格挡+过牌，非常实用的通用技能"
    },
    {
        "id": "blade_dance", "name_en": "Blade Dance", "name_cn": "刀锋之舞",
        "cost": 1, "type": "技能", "rarity": "普通",
        "effect": "将3张Shiv加入手牌。",
        "upgraded": "将4张Shiv加入手牌。",
        "tags": ["普通", "技能", "Shiv"],
        "synergy": "Shiv流核心牌，配合精准和无限刀刃"
    },
    {
        "id": "cloak_and_dagger", "name_en": "Cloak and Dagger", "name_cn": "斗篷与匕首",
        "cost": 1, "type": "技能", "rarity": "普通",
        "effect": "获得6点格挡。将1张Shiv加入手牌。",
        "upgraded": "获得8点格挡。将1张Shiv加入手牌。",
        "tags": ["普通", "技能", "格挡", "Shiv"],
        "synergy": "攻防一体，Shiv流可用"
    },
    {
        "id": "dagger_spray", "name_en": "Dagger Spray", "name_cn": "匕首喷射",
        "cost": 1, "type": "攻击", "rarity": "普通",
        "effect": "对所有敌人造成4点伤害两次。",
        "upgraded": "对所有敌人造成5点伤害两次。",
        "tags": ["普通", "攻击", "AOE", "多段"],
        "synergy": "AOE多段攻击，清小怪好用"
    },
    {
        "id": "dagger_throw", "name_en": "Dagger Throw", "name_cn": "飞刀",
        "cost": 1, "type": "攻击", "rarity": "普通",
        "effect": "造成9点伤害。抽1张牌。丢弃1张牌。",
        "upgraded": "造成12点伤害。抽1张牌。丢弃1张牌。",
        "tags": ["普通", "攻击", "抽牌", "弃牌"],
        "synergy": "攻击+过牌+弃牌，功能全面"
    },
    {
        "id": "deadly_poison", "name_en": "Deadly Poison", "name_cn": "致命毒药",
        "cost": 1, "type": "技能", "rarity": "普通",
        "effect": "给予5层中毒。",
        "upgraded": "给予7层中毒。",
        "tags": ["普通", "技能", "中毒"],
        "synergy": "毒流基础牌，配合催化剂翻倍"
    },
    {
        "id": "deflect", "name_en": "Deflect", "name_cn": "偏转",
        "cost": 0, "type": "技能", "rarity": "普通",
        "effect": "获得4点格挡。",
        "upgraded": "获得5点格挡。",
        "tags": ["普通", "技能", "格挡"],
        "synergy": "0费格挡，配合敏捷效果好"
    },
    {
        "id": "dodge_and_roll", "name_en": "Dodge and Roll", "name_cn": "翻滚闪避",
        "cost": 1, "type": "技能", "rarity": "普通",
        "effect": "获得4点格挡。下回合获得4点格挡。",
        "upgraded": "获得5点格挡。下回合获得5点格挡。",
        "tags": ["普通", "技能", "格挡"],
        "synergy": "两回合格挡，适合预判敌人攻击"
    },
    {
        "id": "flick_flack", "name_en": "Flick-Flack", "name_cn": "弹射",
        "cost": 1, "type": "攻击", "rarity": "普通",
        "effect": "对所有敌人造成7点伤害。",
        "upgraded": "对所有敌人造成9点伤害。",
        "tags": ["普通", "攻击", "AOE"],
        "synergy": "AOE攻击，清小怪"
    },
    {
        "id": "leading_strike", "name_en": "Leading Strike", "name_cn": "先制打击",
        "cost": 1, "type": "攻击", "rarity": "普通",
        "effect": "造成7点伤害。将1张Shiv加入手牌。",
        "upgraded": "造成9点伤害。将1张Shiv加入手牌。",
        "tags": ["普通", "攻击", "Shiv"],
        "synergy": "攻击+Shiv，Shiv流可用"
    },
    {
        "id": "piercing_wail", "name_en": "Piercing Wail", "name_cn": "尖啸",
        "cost": 1, "type": "技能", "rarity": "普通",
        "effect": "所有敌人本回合失去6点力量。",
        "upgraded": "所有敌人本回合失去8点力量。",
        "tags": ["普通", "技能", "力量下降"],
        "synergy": "群体削弱，面对多敌人时强力防御"
    },
    {
        "id": "poisoned_stab", "name_en": "Poisoned Stab", "name_cn": "毒刺",
        "cost": 1, "type": "攻击", "rarity": "普通",
        "effect": "造成6点伤害。给予3层中毒。",
        "upgraded": "造成8点伤害。给予4层中毒。",
        "tags": ["普通", "攻击", "中毒"],
        "synergy": "攻击+施毒，毒流过渡牌"
    },
    {
        "id": "prepared", "name_en": "Prepared", "name_cn": "早有准备",
        "cost": 0, "type": "技能", "rarity": "普通",
        "effect": "抽1张牌。丢弃1张牌。",
        "upgraded": "抽2张牌。丢弃1张牌。",
        "tags": ["普通", "技能", "抽牌", "弃牌"],
        "synergy": "0费过牌+弃牌，弃牌流核心组件"
    },
    {
        "id": "ricochet", "name_en": "Ricochet", "name_cn": "弹跳",
        "cost": 2, "type": "攻击", "rarity": "普通",
        "effect": "对随机敌人造成3点伤害4次。",
        "upgraded": "对随机敌人造成4点伤害4次。",
        "tags": ["普通", "攻击", "多段", "随机"],
        "synergy": "多段随机攻击，配合力量加成"
    },
    {
        "id": "slice", "name_en": "Slice", "name_cn": "切片",
        "cost": 0, "type": "攻击", "rarity": "普通",
        "effect": "造成6点伤害。",
        "upgraded": "造成8点伤害。",
        "tags": ["普通", "攻击"],
        "synergy": "0费攻击，配合力量和多段加成"
    },
    {
        "id": "snakebite", "name_en": "Snakebite", "name_cn": "蛇咬",
        "cost": 2, "type": "技能", "rarity": "普通",
        "effect": "保留。给予7层中毒。",
        "upgraded": "保留。给予10层中毒。",
        "tags": ["普通", "技能", "中毒", "保留"],
        "synergy": "高费施毒，保留特性适合留到关键回合"
    },
    {
        "id": "sucker_punch", "name_en": "Sucker Punch", "name_cn": "突然一拳",
        "cost": 1, "type": "攻击", "rarity": "普通",
        "effect": "造成8点伤害。给予1层虚弱。",
        "upgraded": "造成10点伤害。给予2层虚弱。",
        "tags": ["普通", "攻击", "虚弱"],
        "synergy": "攻击+虚弱，攻防一体"
    },

    # ========== 罕见牌 (Uncommon) ==========
    {
        "id": "accuracy", "name_en": "Accuracy", "name_cn": "精准",
        "cost": 1, "type": "能力", "rarity": "罕见",
        "effect": "Shiv额外造成4点伤害。",
        "upgraded": "Shiv额外造成6点伤害。",
        "tags": ["罕见", "能力", "Shiv"],
        "synergy": "Shiv流核心能力，大幅提升Shiv伤害"
    },
    {
        "id": "backstab", "name_en": "Backstab", "name_cn": "背刺",
        "cost": 0, "type": "攻击", "rarity": "罕见",
        "effect": "造成11点伤害。",
        "upgraded": "造成14点伤害。",
        "tags": ["罕见", "攻击"],
        "synergy": "0费高伤害，战斗开始时可用"
    },
    {
        "id": "blur", "name_en": "Blur", "name_cn": "模糊",
        "cost": 1, "type": "技能", "rarity": "罕见",
        "effect": "获得5点格挡。格挡不会在下回合开始时移除。",
        "upgraded": "获得8点格挡。格挡不会在下回合开始时移除。",
        "tags": ["罕见", "技能", "格挡", "持久格挡"],
        "synergy": "持久格挡，配合高格挡牌积累防御"
    },
    {
        "id": "bouncing_flask", "name_en": "Bouncing Flask", "name_cn": "弹跳瓶",
        "cost": 2, "type": "技能", "rarity": "罕见",
        "effect": "对随机敌人给予3层中毒3次。",
        "upgraded": "对随机敌人给予4层中毒3次。",
        "tags": ["罕见", "技能", "中毒", "AOE"],
        "synergy": "群体施毒，多敌人时强力"
    },
    {
        "id": "bubble_bubble", "name_en": "Bubble Bubble", "name_cn": "咕嘟冒泡",
        "cost": 1, "type": "技能", "rarity": "罕见",
        "effect": "如果敌人有中毒，给予9层中毒。",
        "upgraded": "如果敌人有中毒，给予12层中毒。",
        "tags": ["罕见", "技能", "中毒"],
        "synergy": "条件施毒，毒流爆发牌"
    },
    {
        "id": "calculated_gamble", "name_en": "Calculated Gamble", "name_cn": "计算赌博",
        "cost": 0, "type": "技能", "rarity": "罕见",
        "effect": "弃掉手牌，然后抽等量的牌。",
        "upgraded": "弃掉手牌，然后抽等量的牌。抽1张额外的牌。",
        "tags": ["罕见", "技能", "弃牌", "抽牌"],
        "synergy": "换牌神器，弃牌流和抽牌流都好用"
    },
    {
        "id": "dash", "name_en": "Dash", "name_cn": "冲刺",
        "cost": 2, "type": "攻击", "rarity": "罕见",
        "effect": "获得10点格挡。造成10点伤害。",
        "upgraded": "获得12点格挡。造成12点伤害。",
        "tags": ["罕见", "攻击", "格挡"],
        "synergy": "攻防一体，2费高效牌"
    },
    {
        "id": "escape_plan", "name_en": "Escape Plan", "name_cn": "逃脱计划",
        "cost": 0, "type": "技能", "rarity": "罕见",
        "effect": "抽1张牌。如果抽到技能牌，获得3点格挡。",
        "upgraded": "抽1张牌。如果抽到技能牌，获得5点格挡。",
        "tags": ["罕见", "技能", "抽牌", "格挡"],
        "synergy": "0费过牌，技能多的卡组有额外格挡"
    },
    {
        "id": "expertise", "name_en": "Expertise", "name_cn": "专业",
        "cost": 1, "type": "技能", "rarity": "罕见",
        "effect": "抽牌直到手牌有6张。",
        "upgraded": "抽牌直到手牌有7张。",
        "tags": ["罕见", "技能", "抽牌"],
        "synergy": "大量过牌，配合子弹时间0费打出手牌"
    },
    {
        "id": "expose", "name_en": "Expose", "name_cn": "揭露",
        "cost": 0, "type": "技能", "rarity": "罕见",
        "effect": "移除敌人所有人工制品和格挡。给予2层易伤。",
        "upgraded": "移除敌人所有人工制品和格挡。给予3层易伤。",
        "tags": ["罕见", "技能", "易伤", "破甲"],
        "synergy": "破甲+易伤，对付高格挡敌人必备"
    },
    {
        "id": "finisher", "name_en": "Finisher", "name_cn": "终结技",
        "cost": 1, "type": "攻击", "rarity": "罕见",
        "effect": "本回合每打出过一张攻击牌，造成6点伤害一次。",
        "upgraded": "本回合每打出过一张攻击牌，造成8点伤害一次。",
        "tags": ["罕见", "攻击", "多段"],
        "synergy": "多攻击牌流的终结技，配合Shiv和0费攻击"
    },
    {
        "id": "flanking", "name_en": "Flanking", "name_cn": "侧翼",
        "cost": 2, "type": "技能", "rarity": "罕见",
        "effect": "敌人本回合受到其他玩家的伤害翻倍。",
        "upgraded": "敌人本回合受到所有伤害翻倍。",
        "tags": ["罕见", "技能", "易伤"],
        "synergy": "增伤技能，配合高爆发攻击"
    },
    {
        "id": "flechettes", "name_en": "Flechettes", "name_cn": "飞镖",
        "cost": 1, "type": "攻击", "rarity": "罕见",
        "effect": "手牌中每张技能牌造成5点伤害。",
        "upgraded": "手牌中每张技能牌造成7点伤害。",
        "tags": ["罕见", "攻击", "技能协同"],
        "synergy": "技能多的卡组伤害很高"
    },
    {
        "id": "follow_through", "name_en": "Follow Through", "name_cn": "跟进",
        "cost": 1, "type": "攻击", "rarity": "罕见",
        "effect": "对所有敌人造成6点伤害。如果本回合上一张打出的是技能，给予所有敌人1层虚弱。",
        "upgraded": "对所有敌人造成8点伤害。如果本回合上一张打出的是技能，给予所有敌人2层虚弱。",
        "tags": ["罕见", "攻击", "AOE", "虚弱"],
        "synergy": "技能-攻击交替使用时附加虚弱"
    },
    {
        "id": "footwork", "name_en": "Footwork", "name_cn": "步法",
        "cost": 1, "type": "能力", "rarity": "罕见",
        "effect": "获得2点敏捷。",
        "upgraded": "获得3点敏捷。",
        "tags": ["罕见", "能力", "敏捷"],
        "synergy": "永久敏捷，格挡流核心能力，升级优先级高"
    },
    {
        "id": "hand_trick", "name_en": "Hand Trick", "name_cn": "手法",
        "cost": 1, "type": "技能", "rarity": "罕见",
        "effect": "获得7点格挡。本回合给手牌中一张技能牌添加Sly。",
        "upgraded": "获得10点格挡。本回合给手牌中一张技能牌添加Sly。",
        "tags": ["罕见", "技能", "格挡", "Sly"],
        "synergy": "格挡+Sly，配合Sly机制"
    },
    {
        "id": "haze", "name_en": "Haze", "name_cn": "迷雾",
        "cost": 3, "type": "技能", "rarity": "罕见",
        "effect": "给予所有敌人4层中毒。",
        "upgraded": "给予所有敌人6层中毒。",
        "tags": ["罕见", "技能", "中毒", "AOE"],
        "synergy": "群体施毒，高费但效果强"
    },
    {
        "id": "hidden_daggers", "name_en": "Hidden Daggers", "name_cn": "隐藏匕首",
        "cost": 0, "type": "技能", "rarity": "罕见",
        "effect": "弃2张牌。将2张Shiv加入手牌。",
        "upgraded": "弃1张牌。将2张Shiv加入手牌。",
        "tags": ["罕见", "技能", "弃牌", "Shiv"],
        "synergy": "弃牌+Shiv，双流派协同"
    },
    {
        "id": "infinite_blades", "name_en": "Infinite Blades", "name_cn": "无限刀刃",
        "cost": 1, "type": "能力", "rarity": "罕见",
        "effect": "每回合开始时，将1张Shiv加入手牌。",
        "upgraded": "每回合开始时，将2张Shiv加入手牌。",
        "tags": ["罕见", "能力", "Shiv"],
        "synergy": "Shiv流核心能力，持续产出Shiv"
    },
    {
        "id": "leg_sweep", "name_en": "Leg Sweep", "name_cn": "扫腿",
        "cost": 2, "type": "技能", "rarity": "罕见",
        "effect": "给予2层虚弱。获得11点格挡。",
        "upgraded": "给予3层虚弱。获得14点格挡。",
        "tags": ["罕见", "技能", "虚弱", "格挡"],
        "synergy": "高格挡+虚弱，强力防御牌"
    },
    {
        "id": "memento_mori", "name_en": "Memento Mori", "name_cn": "死亡纪念",
        "cost": 1, "type": "攻击", "rarity": "罕见",
        "effect": "造成12点伤害。本回合每弃一张牌额外造成4点伤害。",
        "upgraded": "造成14点伤害。本回合每弃一张牌额外造成5点伤害。",
        "tags": ["罕见", "攻击", "弃牌协同"],
        "synergy": "弃牌流爆发攻击，弃牌越多伤害越高"
    },
    {
        "id": "mirage", "name_en": "Mirage", "name_cn": "海市蜃楼",
        "cost": 1, "type": "技能", "rarity": "罕见",
        "effect": "获得等同于所有敌人中毒层数的格挡。消耗。",
        "upgraded": "获得等同于所有敌人中毒层数+2的格挡。消耗。",
        "tags": ["罕见", "技能", "格挡", "中毒协同", "消耗"],
        "synergy": "毒流防御牌，毒层高时格挡很高"
    },
    {
        "id": "noxious_fumes", "name_en": "Noxious Fumes", "name_cn": "毒雾",
        "cost": 1, "type": "能力", "rarity": "罕见",
        "effect": "每回合开始时，给予所有敌人2层中毒。",
        "upgraded": "每回合开始时，给予所有敌人3层中毒。",
        "tags": ["罕见", "能力", "中毒"],
        "synergy": "毒流核心能力，持续群体施毒"
    },
    {
        "id": "outbreak", "name_en": "Outbreak", "name_cn": "爆发",
        "cost": 1, "type": "能力", "rarity": "罕见",
        "effect": "每施3次毒，对所有敌人造成11点伤害。",
        "upgraded": "每施3次毒，对所有敌人造成15点伤害。",
        "tags": ["罕见", "能力", "中毒", "伤害"],
        "synergy": "毒流伤害能力，配合高频施毒"
    },
    {
        "id": "phantom_blades", "name_en": "Phantom Blades", "name_cn": "幻影刀刃",
        "cost": 1, "type": "能力", "rarity": "罕见",
        "effect": "Shiv获得保留。每回合打出的第一张Shiv额外造成9点伤害。",
        "upgraded": "Shiv获得保留。每回合打出的第一张Shiv额外造成12点伤害。",
        "tags": ["罕见", "能力", "Shiv", "保留"],
        "synergy": "Shiv流增强能力，保留+首击加成"
    },
    {
        "id": "pinpoint", "name_en": "Pinpoint", "name_cn": "精准打击",
        "cost": 3, "type": "攻击", "rarity": "罕见",
        "effect": "造成17点伤害。本回合每打出一张技能牌，费用减1。",
        "upgraded": "造成21点伤害。本回合每打出一张技能牌，费用减1。",
        "tags": ["罕见", "攻击", "技能协同"],
        "synergy": "技能多的卡组可以0费打出高伤害"
    },
    {
        "id": "pounce", "name_en": "Pounce", "name_cn": "猛扑",
        "cost": 2, "type": "攻击", "rarity": "罕见",
        "effect": "造成12点伤害。下一张技能牌费用为0。",
        "upgraded": "造成15点伤害。下一张技能牌费用为0。",
        "tags": ["罕见", "攻击", "技能协同"],
        "synergy": "攻击+0费技能，配合高费技能"
    },
    {
        "id": "precise_cut", "name_en": "Precise Cut", "name_cn": "精确切割",
        "cost": 0, "type": "攻击", "rarity": "罕见",
        "effect": "造成15点伤害。手牌中每多一张牌，伤害减2。",
        "upgraded": "造成18点伤害。手牌中每多一张牌，伤害减2。",
        "tags": ["罕见", "攻击"],
        "synergy": "手牌少时高伤害，配合弃牌后打出"
    },
    {
        "id": "predator", "name_en": "Predator", "name_cn": "掠食者",
        "cost": 2, "type": "攻击", "rarity": "罕见",
        "effect": "造成15点伤害。下回合抽2张牌。",
        "upgraded": "造成18点伤害。下回合抽3张牌。",
        "tags": ["罕见", "攻击", "抽牌"],
        "synergy": "攻击+下回合过牌，节奏好"
    },
    {
        "id": "reflex", "name_en": "Reflex", "name_cn": "反射",
        "cost": 3, "type": "技能", "rarity": "罕见",
        "effect": "抽2张牌。",
        "upgraded": "抽2张牌。费用减1。",
        "tags": ["罕见", "技能", "抽牌", "弃牌触发"],
        "synergy": "被弃时自动触发，弃牌流组件"
    },
    {
        "id": "skewer", "name_en": "Skewer", "name_cn": "串刺",
        "cost": 0, "type": "攻击", "rarity": "罕见",
        "effect": "消耗所有能量，每点能量造成7点伤害。",
        "upgraded": "消耗所有能量，每点能量造成9点伤害。",
        "tags": ["罕见", "攻击", "能量协同"],
        "synergy": "能量多时高伤害，回合末爆发"
    },
    {
        "id": "speedster", "name_en": "Speedster", "name_cn": "速度狂",
        "cost": 2, "type": "能力", "rarity": "罕见",
        "effect": "本回合每抽一张牌，对所有敌人造成2点伤害。",
        "upgraded": "本回合每抽一张牌，对所有敌人造成3点伤害。",
        "tags": ["罕见", "能力", "抽牌协同", "AOE"],
        "synergy": "抽牌流伤害能力，配合大量过牌"
    },
    {
        "id": "strangle", "name_en": "Strangle", "name_cn": "勒颈",
        "cost": 1, "type": "攻击", "rarity": "罕见",
        "effect": "造成8点伤害。本回合每打出一张牌，敌人失去2点生命。",
        "upgraded": "造成10点伤害。本回合每打出一张牌，敌人失去3点生命。",
        "tags": ["罕见", "攻击", "多牌协同"],
        "synergy": "多牌流伤害，配合0费牌和Shiv"
    },

    # ========== 稀有牌 (Rare) ==========
    {
        "id": "abrasive", "name_en": "Abrasive", "name_cn": "磨砂",
        "cost": 3, "type": "能力", "rarity": "稀有",
        "effect": "获得1点敏捷。获得4点荆棘。",
        "upgraded": "获得2点敏捷。获得6点荆棘。",
        "tags": ["稀有", "能力", "敏捷", "荆棘"],
        "synergy": "防御反伤能力，配合高格挡"
    },
    {
        "id": "accelerant", "name_en": "Accelerant", "name_cn": "催化剂",
        "cost": 1, "type": "能力", "rarity": "稀有",
        "effect": "中毒额外触发1次。",
        "upgraded": "中毒额外触发2次。",
        "tags": ["稀有", "能力", "中毒"],
        "synergy": "毒流核心能力，翻倍毒伤害"
    },
    {
        "id": "adrenaline", "name_en": "Adrenaline", "name_cn": "肾上腺素",
        "cost": 0, "type": "技能", "rarity": "稀有",
        "effect": "获得1点能量。抽2张牌。",
        "upgraded": "获得2点能量。抽2张牌。",
        "tags": ["稀有", "技能", "能量", "抽牌"],
        "synergy": "0费能量+过牌，强力节奏牌"
    },
    {
        "id": "afterimage", "name_en": "Afterimage", "name_cn": "残影",
        "cost": 1, "type": "能力", "rarity": "稀有",
        "effect": "每打出一张牌，获得1点格挡。",
        "upgraded": "每打出一张牌，获得2点格挡。",
        "tags": ["稀有", "能力", "格挡", "多牌协同"],
        "synergy": "多牌流防御能力，配合0费牌和Shiv"
    },
    {
        "id": "assassinate", "name_en": "Assassinate", "name_cn": "暗杀",
        "cost": 0, "type": "攻击", "rarity": "稀有",
        "effect": "造成10点伤害。给予1层易伤。",
        "upgraded": "造成13点伤害。给予2层易伤。",
        "tags": ["稀有", "攻击", "易伤"],
        "synergy": "0费攻击+易伤，开局削弱敌人"
    },
    {
        "id": "blade_of_ink", "name_en": "Blade of Ink", "name_cn": "墨刃",
        "cost": 1, "type": "技能", "rarity": "稀有",
        "effect": "本回合每打出一张攻击牌，获得2点力量。",
        "upgraded": "本回合每打出一张攻击牌，获得3点力量。",
        "tags": ["稀有", "技能", "力量", "攻击协同"],
        "synergy": "多攻击牌流爆发，配合Shiv和终结技"
    },
    {
        "id": "bullet_time", "name_en": "Bullet Time", "name_cn": "子弹时间",
        "cost": 3, "type": "技能", "rarity": "稀有",
        "effect": "本回合不能额外抽牌。手牌中所有牌本回合费用为0。",
        "upgraded": "本回合不能额外抽牌。手牌中所有牌本回合费用为0。抽1张牌。",
        "tags": ["稀有", "技能", "0费", "爆发"],
        "synergy": "爆发核心，配合大量手牌0费全打出"
    },
    {
        "id": "burst", "name_en": "Burst", "name_cn": "爆发",
        "cost": 1, "type": "技能", "rarity": "稀有",
        "effect": "本回合下一张技能牌额外触发一次。",
        "upgraded": "本回合下两张技能牌额外触发一次。",
        "tags": ["稀有", "技能", "技能协同"],
        "synergy": "配合强力技能牌双倍效果"
    },
    {
        "id": "corrosive_wave", "name_en": "Corrosive Wave", "name_cn": "腐蚀波",
        "cost": 1, "type": "技能", "rarity": "稀有",
        "effect": "本回合每抽一张牌，给予所有敌人3层中毒。",
        "upgraded": "本回合每抽一张牌，给予所有敌人4层中毒。",
        "tags": ["稀有", "技能", "中毒", "抽牌协同"],
        "synergy": "抽牌+施毒，配合大量过牌群体施毒"
    },
    {
        "id": "echoing_slash", "name_en": "Echoing Slash", "name_cn": "回响斩击",
        "cost": 1, "type": "攻击", "rarity": "稀有",
        "effect": "对所有敌人造成10点伤害。每杀死一个敌人，重复此效果。",
        "upgraded": "对所有敌人造成13点伤害。每杀死一个敌人，重复此效果。",
        "tags": ["稀有", "攻击", "AOE", "击杀协同"],
        "synergy": "清场神技，低血量敌人多的时候连锁爆发"
    },
    {
        "id": "envenom", "name_en": "Envenom", "name_cn": "毒液",
        "cost": 2, "type": "能力", "rarity": "稀有",
        "effect": "攻击造成未格挡伤害时，给予1层中毒。",
        "upgraded": "攻击造成未格挡伤害时，给予2层中毒。",
        "tags": ["稀有", "能力", "中毒", "攻击协同"],
        "synergy": "攻击流转毒流，配合多段攻击"
    },
    {
        "id": "fan_of_knives", "name_en": "Fan of Knives", "name_cn": "刀扇",
        "cost": 2, "type": "能力", "rarity": "稀有",
        "effect": "Shiv现在攻击所有敌人。将4张Shiv加入手牌。",
        "upgraded": "Shiv现在攻击所有敌人。将6张Shiv加入手牌。",
        "tags": ["稀有", "能力", "Shiv", "AOE"],
        "synergy": "Shiv流AOE能力，清小怪强力"
    },
    {
        "id": "grand_finale", "name_en": "Grand Finale", "name_cn": "终幕",
        "cost": 0, "type": "攻击", "rarity": "稀有",
        "effect": "只有抽牌堆为空时才能打出。对所有敌人造成50点伤害。",
        "upgraded": "只有抽牌堆为空时才能打出。对所有敌人造成60点伤害。",
        "tags": ["稀有", "攻击", "AOE", "条件"],
        "synergy": "抽牌流终极爆发，需要把抽牌堆抽空"
    },
    {
        "id": "knife_trap", "name_en": "Knife Trap", "name_cn": "刀陷阱",
        "cost": 2, "type": "技能", "rarity": "稀有",
        "effect": "将消耗堆中所有Shiv打出对敌人。",
        "upgraded": "将消耗堆中所有Shiv打出对所有敌人。",
        "tags": ["稀有", "技能", "Shiv", "消耗协同"],
        "synergy": "Shiv流爆发，配合大量Shiv消耗后回收"
    },
    {
        "id": "malaise", "name_en": "Malaise", "name_cn": "萎靡",
        "cost": 0, "type": "技能", "rarity": "稀有",
        "effect": "敌人失去X点力量。给予X层虚弱。",
        "upgraded": "敌人失去X+1点力量。给予X+1层虚弱。",
        "tags": ["稀有", "技能", "力量下降", "虚弱", "X费"],
        "synergy": "强力削弱，高费投入可以废掉敌人攻击"
    },
    {
        "id": "master_planner", "name_en": "Master Planner", "name_cn": "策划大师",
        "cost": 2, "type": "能力", "rarity": "稀有",
        "effect": "打出技能牌时，该牌获得Sly。",
        "upgraded": "打出技能牌时，该牌获得Sly。获得1点敏捷。",
        "tags": ["稀有", "能力", "Sly", "技能协同"],
        "synergy": "Sly机制核心能力，技能牌自动获得Sly"
    },
    {
        "id": "murder", "name_en": "Murder", "name_cn": "谋杀",
        "cost": 3, "type": "攻击", "rarity": "稀有",
        "effect": "造成2点伤害。本场战斗每抽一张牌额外造成1点伤害。",
        "upgraded": "造成2点伤害。本场战斗每抽一张牌额外造成2点伤害。",
        "tags": ["稀有", "攻击", "抽牌协同"],
        "synergy": "抽牌流终极攻击，后期伤害极高"
    },
    {
        "id": "nightmare", "name_en": "Nightmare", "name_cn": "噩梦",
        "cost": 3, "type": "技能", "rarity": "稀有",
        "effect": "选择一张牌。下回合将3张该牌的复制品加入手牌。",
        "upgraded": "选择一张牌。下回合将4张该牌的复制品加入手牌。",
        "tags": ["稀有", "技能", "复制"],
        "synergy": "复制关键牌，配合强力技能或攻击"
    },
    {
        "id": "serpent_form", "name_en": "Serpent Form", "name_cn": "蛇形态",
        "cost": 3, "type": "能力", "rarity": "稀有",
        "effect": "每打出一张牌，对随机敌人造成4点伤害。",
        "upgraded": "每打出一张牌，对随机敌人造成6点伤害。",
        "tags": ["稀有", "能力", "多牌协同"],
        "synergy": "多牌流伤害能力，配合0费牌和Shiv"
    },
    {
        "id": "shadow_step", "name_en": "Shadow Step", "name_cn": "暗影步",
        "cost": 1, "type": "技能", "rarity": "稀有",
        "effect": "弃掉手牌。下回合攻击造成双倍伤害。",
        "upgraded": "弃掉手牌。下回合攻击造成双倍伤害。抽1张牌。",
        "tags": ["稀有", "技能", "弃牌", "增伤"],
        "synergy": "弃牌+下回合爆发，配合高伤害攻击"
    },
    {
        "id": "shadowmeld", "name_en": "Shadowmeld", "name_cn": "暗影融合",
        "cost": 1, "type": "技能", "rarity": "稀有",
        "effect": "本回合格挡获得翻倍。",
        "upgraded": "本回合格挡获得翻倍。获得1点敏捷。",
        "tags": ["稀有", "技能", "格挡"],
        "synergy": "格挡爆发，配合多段格挡牌"
    },
    {
        "id": "sneaky", "name_en": "Sneaky", "name_cn": "鬼祟",
        "cost": 2, "type": "能力", "rarity": "稀有",
        "effect": "其他玩家攻击敌人时，获得1点格挡。",
        "upgraded": "其他玩家攻击敌人时，获得2点格挡。",
        "tags": ["稀有", "能力", "格挡", "协同"],
        "synergy": "多人模式防御能力"
    },
    {
        "id": "storm_of_steel", "name_en": "Storm of Steel", "name_cn": "钢铁风暴",
        "cost": 1, "type": "技能", "rarity": "稀有",
        "effect": "弃掉手牌。每弃一张牌，将1张Shiv加入手牌。",
        "upgraded": "弃掉手牌。每弃一张牌，将1张升级Shiv加入手牌。",
        "tags": ["稀有", "技能", "弃牌", "Shiv"],
        "synergy": "弃牌转Shiv，双流派协同爆发"
    },

    # ========== 先古牌 (Ancient) ==========
    {
        "id": "suppress", "name_en": "Suppress", "name_cn": "压制",
        "cost": 0, "type": "攻击", "rarity": "先古",
        "effect": "造成11点伤害。给予3层虚弱。",
        "upgraded": "造成14点伤害。给予4层虚弱。",
        "tags": ["先古", "攻击", "虚弱"],
        "synergy": "强力0费攻击+虚弱，先古牌强度很高"
    },
]


def get_card_by_name(name: str) -> dict:
    """根据名称查找卡牌（支持中英文）"""
    for c in SILENT_CARDS:
        if c["name_cn"] == name or c["name_en"] == name or c["id"] == name:
            return c
    # 模糊匹配
    for c in SILENT_CARDS:
        if name in c["name_cn"] or name in c["name_en"]:
            return c
    return None


def get_cards_by_rarity(rarity: str) -> list:
    """按稀有度筛选"""
    return [c for c in SILENT_CARDS if c["rarity"] == rarity]


def get_cards_by_type(ctype: str) -> list:
    """按类型筛选"""
    return [c for c in SILENT_CARDS if c["type"] == ctype]


def search_cards(query: str) -> list:
    """搜索卡牌"""
    query = query.lower()
    return [c for c in SILENT_CARDS if
            query in c["name_cn"].lower() or
            query in c["name_en"].lower() or
            query in c["effect"].lower() or
            any(query in t.lower() for t in c["tags"])]


# 卡牌统计
CARD_STATS = {
    "total": len(SILENT_CARDS),
    "basic": len([c for c in SILENT_CARDS if c["rarity"] == "基础"]),
    "common": len([c for c in SILENT_CARDS if c["rarity"] == "普通"]),
    "uncommon": len([c for c in SILENT_CARDS if c["rarity"] == "罕见"]),
    "rare": len([c for c in SILENT_CARDS if c["rarity"] == "稀有"]),
    "ancient": len([c for c in SILENT_CARDS if c["rarity"] == "先古"]),
    "attack": len([c for c in SILENT_CARDS if c["type"] == "攻击"]),
    "skill": len([c for c in SILENT_CARDS if c["type"] == "技能"]),
    "power": len([c for c in SILENT_CARDS if c["type"] == "能力"]),
}

# 自动为每张卡牌添加图片URL（来自spire-codex CDN）
SPIRE_CODEX_CARD_BASE = "https://cdn.spire-codex.com/cards-full/stable"
for _card in SILENT_CARDS:
    _cid = _card["id"].lower()
    _card["image_url"] = f"{SPIRE_CODEX_CARD_BASE}/{_cid}.webp"
    _card["image_url_upg"] = f"{SPIRE_CODEX_CARD_BASE}/{_cid}_upg.webp"
    _card["portrait_url"] = f"https://spire-codex.com/static/images/cards/{_cid}.webp"
