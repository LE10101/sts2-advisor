# 杀戮尖塔2 决策器（AI 教练 · 静默猎手）

面向《杀戮尖塔2》静默猎手角色的实时 AI 决策教练。战斗阶段用 MCTS 推荐出牌，支持 SL 看牌序自动记忆并按真实牌序确定性推演，外加地图路线 / 奖励选卡 / 商店购买的三阶段决策建议，可接入真实游戏（autoSpire mod 的本地 HTTP 接口），带游戏内悬浮字幕。

## 功能总览

| 模块 | 功能 |
|---|---|
| **战斗 MCTS** | UCT 树搜索，对每个候选动作按预期胜率排序 |
| **SL 牌序记忆** | 帧间手牌差异检测新抽牌，SL 时自动重置重新确认 |
| **静默猎手专属** | 毒/小刀/弃牌/Sly/敏捷 四大机制精确建模，40+ 张卡效果表 |
| **状态评估器** | 9 维特征加权线性评估（V3），可替换为训练的 MLP（V4） |
| **支配剪枝** | 同牌多目标只保留 top-2，候选聚焦 |
| **路线决策** | 节点类型评分 + 血量自适应 + 前瞻 |
| **奖励选卡** | 流派感知卡牌价值评分，三选一/金币/跳过 |
| **商店购买** | 预算内性价比贪心：卡牌/遗物/删牌 |
| **决策理由** | 自然语言解释为什么这么选 |
| **悬浮字幕** | 置顶半透明窗，实时显示推荐+理由（tkinter 版 + 浏览器版双方案） |
| **autoSpire 接入** | HTTP 接口读状态/提交动作，真实游戏联动 |

## 快速开始

仅依赖 Python 标准库，无需第三方包。

```bash
# 1) 离线自测：选择演示 战斗 / 路线 / 奖励 / 商店
python run.py --mode offline

# 2) 接入真实游戏
python run.py --mode real --port 8765

# 2b) 真实游戏 + 游戏内悬浮字幕（自动选择 tkinter 或浏览器版）
python run.py --mode real --overlay

# 3) 跑全部测试
python tests/test_mcts.py && python tests/test_v2.py && python tests/test_v3.py
```

## 接入真实游戏（autoSpire）

1. 在 Steam 创意工坊订阅 autoSpire mod
2. 启动《杀戮尖塔2》，确认 mod 加载成功（日志显示 autoSpire mod initialized）
3. 运行 `python run.py --mode real --overlay`
4. 决策器自动连接 127.0.0.1:8765，按阶段给出推荐

**第一次校准**：`python run.py --mode real --dump dump` 跑几分钟，然后 `python scripts/calibrate.py dump` 把字段报告给我，我来更新字段映射。

## 悬浮字幕（双方案）

`--overlay` 会自动选择可用的字幕方案：

1. **tkinter 悬浮窗**（优先）：独立置顶半透明窗口，浮在游戏画面上方，可拖动。需要 Python 带完整 Tcl/Tk（python.org 官方安装包默认带）。
2. **浏览器字幕**（回退）：tkinter 不可用时自动启动本地 HTTP 服务，浏览器打开 `http://127.0.0.1:8766`，把浏览器窗口置顶放在游戏旁边。完全不依赖第三方库。

两种方案显示内容相同：Top3 推荐动作 + 胜率 + 决策理由，按阶段自动切换（战斗/路线/奖励/商店）。

## 训练自定义评估器

```bash
python scripts/train_evaluator.py --games 100 --out weights.json
python run.py --mode real --model weights.json
```

## 目录结构

```
sts2_advisor/
├── run.py                  # 入口
├── requirements.txt        # 仅标准库
├── advisor/
│   ├── client.py           # autoSpire HTTP 客户端 + 离线客户端
│   ├── model.py            # 战斗状态数据模型（容错解析）
│   ├── cards.py            # 静默猎手卡牌效果库
│   ├── simulator.py        # 战斗模拟器（毒/Shiv/弃牌/Sly/能力）
│   ├── mcts.py             # MCTS（UCT）
│   ├── policy.py           # rollout 策略（贪心/随机）
│   ├── drawmemory.py       # SL 牌序记忆
│   ├── evaluate.py         # V3 多特征评估器
│   ├── prune.py            # V3 支配剪枝
│   ├── network.py          # V4 MLP/逻辑回归
│   ├── sampling.py         # self-play 采样
│   ├── cardvalue.py        # 卡牌价值评分（流派感知）
│   ├── route.py            # 地图路线决策
│   ├── reward.py           # 奖励选卡决策
│   ├── shop.py             # 商店购买决策
│   ├── explanation.py      # 决策理由生成
│   ├── overlay.py          # 游戏内悬浮字幕
│   └── cli.py              # 命令行主循环
├── scripts/
│   ├── train_evaluator.py  # 训练评估器
│   └── calibrate.py        # autoSpire 字段校准
└── tests/
    ├── test_mcts.py        # V1 测试
    ├── test_v2.py          # V2 测试
    └── test_v3.py          # V3 测试
```

## 已知近似与扩展方向

- 卡牌效果表覆盖主流 S/A/B 级卡，其余用描述关键词回退
- 敌人 AI 简化为 intent_damage 直接攻击，未建模复杂行为
- 遗物/药水效果未完整建模
- 可扩展：C++ 核心提速、LLM 战略层、更多角色
