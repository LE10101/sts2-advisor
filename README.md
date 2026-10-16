# 杀戮尖塔 2 决策器（AI 教练 · 静默猎手 · MCTS）

一个 **实时决策推荐器**，专为静默猎手（Silent）设计：读取《杀戮尖塔2》游戏状态，用 **蒙特卡洛树搜索（MCTS）** 推演战斗，并给出**路线 / 奖励选卡 / 商店购买**建议。玩家手动执行，或确认后半自动执行。

## 🚀 V6.0 公开网站版（新增）

现已升级为完整的 **Web 应用**，支持公网访问、历史对局复盘、怪物图鉴、LLM分析。

### 快速启动

```bash
# 启动Web应用（本地+局域网+公网）
python web_app.py

# 或使用一键启动脚本（Windows）
启动公网版.bat
```

启动后访问：
- **本机**: http://127.0.0.1:8766
- **局域网**: http://<你的IP>:8766
- **公网**: 使用 localtunnel / ngrok 隧道（见下方）

### 网站功能

| 页面 | 功能 |
|---|---|
| 🏠 首页 | 导航入口 + 游戏连接状态 |
| ⚔️ 当前对局 | 实时战斗推荐、状态面板、敌人意图、手牌、牌序记忆、备选方案 |
| 📊 历史对局 | 所有对局列表，筛选进阶/角色/结果 |
| 📈 对局复盘 | 战略分析、流派识别、牌组评估、改进建议、综合评分 |
| 👹 怪物图鉴 | 20+怪物的固定行为模式、伤害数值、应对策略 |
| 🃏 卡牌图鉴 | 全卡牌效果、费用、类型 |

### 公网暴露方案

**方案1: localtunnel（免费，推荐）**
```bash
npx localtunnel --port 8766 --subdomain sts2-advisor
```

**方案2: ngrok（稳定，需注册）**
```bash
ngrok http 8766
```

**方案3: Cloudflare Tunnel（免费固定域名，需自有域名）**
```bash
cloudflared tunnel --url http://localhost:8766
```

### LLM 大语言模型接入

设置环境变量后启用LLM分析（不设置则使用内置规则分析）：
```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选，兼容其他API
```

支持分析：战斗局面、选卡决策、整局复盘。

---

## 核心能力

| 阶段 | 决策 | 方法 |
|---|---|---|
| **战斗** | 每个候选动作（打某牌→某目标 / 结束回合）按预期收益排序 | MCTS（UCT）+ 战斗模拟器 |
| **SL 牌序** | 利用固定种子机制，SL/抽牌后自动记录真实牌序，按真实牌序确定性推演 | DrawOrderMemory |
| **路线** | 地图上每一步走哪个节点（战斗/精英/事件/商店/篝火/宝箱） | 类型评分 + 前瞻 |
| **奖励** | 战斗胜利三选一选哪张 / 拿金币 / 跳过 | 流派感知价值评分 |
| **商店** | 金币预算内买哪些卡 / 遗物 / 是否删牌 | 性价比贪心 |

## 静默猎手机制支持

- **毒(Poison)**：回合结算递增伤害，催化翻倍，毒雾/腐蚀波等 AOE 上毒
- **小刀(Shiv)**：0 费攻击、打出自消耗，被"精准"等强化
- **弃牌 + Sly**：弃牌触发战术家（回能量）/反射（抽牌），Sly 牌被弃时按原费自动打出
- **敏捷 / 力量 / 虚弱 / 易伤**：完整数值结算
- **能力牌**：幽灵形态（无形）、无尽刀刃、毒雾、精准、淬毒等

## 目录结构

```
sts2_advisor/
├── run.py                  # 入口
├── advisor/
│   ├── client.py           # autoSpire HTTP 客户端（offline / real）
│   ├── model.py            # 战斗状态 / 卡牌 / 敌人 / 动作（容错解析）
│   ├── cards.py            # 卡牌效果库（静默猎手主流牌 + 关键词回退）
│   ├── simulator.py        # 战斗模拟器（毒/小刀/弃牌/Sly/能力）
│   ├── drawmemory.py       # SL 牌序记忆（自动记录真实牌序）
│   ├── policy.py           # MCTS rollout 默认策略
│   ├── mcts.py             # MCTS（UCT）决策核心
│   ├── cardvalue.py        # 卡牌价值评分（流派感知）
│   ├── evaluate.py         # 状态评估器（多特征加权 + 可加载训练模型）
│   ├── prune.py            # 支配剪枝（目标裁剪 + 去重）
│   ├── explanation.py      # 决策理由生成（为什么这么选）
│   ├── overlay.py          # 游戏内悬浮字幕（置顶半透明窗，显示推荐+理由）
│   ├── network.py          # 轻量 MLP / 逻辑回归评估网络（纯 Python）
│   ├── sampling.py         # self-play 采样器（生成评估器训练样本）
│   ├── route.py            # 地图路线决策
│   ├── reward.py           # 奖励选卡决策
│   ├── shop.py             # 商店购买决策
│   └── cli.py              # 命令行主循环（多阶段路由）
├── scripts/
│   ├── train_evaluator.py  # 训练并保存状态评估器（weights.json）
│   └── calibrate.py        # 真实局快照字段校准报告
└── tests/                  # test_mcts.py（V1）+ test_v2.py（V2）+ test_v3.py（V3）+ bench_prune.py
```

## 快速开始

仅依赖 Python 标准库，无需第三方包。

```bash
# 1) 离线自测：选择演示 战斗 / SL牌序 / 路线 / 奖励 / 商店
python3 run.py --mode offline

# 2) 接入真实游戏
python3 run.py --mode real --port 8765

# 2b) 真实游戏 + 游戏内悬浮字幕（置顶半透明窗，显示推荐+理由）
python3 run.py --mode real --overlay

# 3) 跑全部测试
python3 tests/test_mcts.py && python3 tests/test_v2.py && python3 tests/test_v3.py
```

## V4：性能优化 + 可训练评估器 + 真实局校准

**① rollout 性能降本（`simulator.py` / `cards.py`）**
- `effects_for_card` 结果缓存：卡牌效果解析是每步结算/剪枝的热点，命中后省去重复解析
- rollout 动态早停：评估值连续稳定且明显定局（大优/大劣）时提前返回，省去注定胜负对局的白跑步数
- 实测 600 次 MCTS 迭代从约 0.5s 级降到 0.19~0.23s（约 2 倍）

**② 可训练状态评估器（`network.py` / `sampling.py` / `scripts/train_evaluator.py`）**
- self-play 采样：随机战斗对局，每个中间状态用多次 rollout 平均作监督标签（避免单局结局的归属偏差）
- 纯 Python 实现 MLP（9→16→1）与逻辑回归，无第三方依赖；numpy 可用时可选加速
- 训练：`python3 scripts/train_evaluator.py --games 300`，产出 `advisor/weights.json`
- **默认仍用启发式**：训练模型存在分布漂移风险（self-play 采样分布与真实状态不一致时外推差），
  刻意不自动覆盖可靠启发式。确认模型更优后再显式启用：`python3 run.py --model advisor/weights.json`

**③ autoSpire 真实局校准（`cli.py --dump` / `scripts/calibrate.py`）**
- 跑真实局前用 `python3 run.py --mode real --dump dump`，把每帧原始 /state 快照存盘
- 之后 `python3 scripts/calibrate.py dump` 输出各阶段字段命中率 / 解析成败 / 缺失字段，
  用于现场校准字段映射（把缺失项反馈给我即可调整）



常用参数：`--mode offline|real`、`--host`、`--port`（客机 8766）、`--iterations`（MCTS 迭代数，默认 600）。

## SL 牌序记忆怎么用

杀戮尖塔的牌堆顺序由种子固定。这个工具自动利用这一点：

1. 正常开打，决策器每帧对比手牌差异，把**抽到的牌按顺序**记入记忆。
2. 在游戏里 **SL 读档**（回档），决策器检测到回合回退后回到战斗起点重新确认——因为牌序固定，重抽的牌会与记忆匹配，**不会重复记录**。
3. 多次 SL 可逐步摸清整个牌堆的真实顺序；之后 MCTS 就**按真实牌序确定性推演**，不再随机猜。
4. 战斗中也可以手动输入 `s` 手动标记一次 SL。

真实模式下，每帧会在界面显示当前牌序记忆进度（如 `牌序记忆：毒刺6 → 打击6 → 小刀4 …`）。

## 接入真实游戏（autoSpire）

1. Steam 安装《杀戮尖塔 2》。
2. 从 [autoSpire Releases](https://lobehub.com/mcp/lightending-autospire) 下载 zip，把 `autoSpire/` 解压到 `<Steam库>\...\Slay the Spire 2\mods\autoSpire\`。
3. 启动游戏，确认日志 `[autoSpire] autoSpire mod initialized!`（默认端口 8765 主机 / 8766 客机）。
4. 运行 `python3 run.py --mode real --port 8765`。

> 本项目只用了 autoSpire 的 HTTP 接口（`GET /state`、`POST /action`），不依赖其 MCP 适配器，纯 `urllib` 即可。

## 模拟口径与已知近似

"够用"的决策推演引擎，目标是把**相对强弱排序做对**：

- 弃牌为随机弃 N 张；复杂特殊牌（按技能数/攻击数计伤、X 费、复制等）用启发式近似
- 敌人只按当前 intent 结算一轮；buff 衰减为简化规则
- 未收录的卡牌走"描述关键词回退"；强度表未收录的卡给中性分
- SL 记忆依赖 autoSpire 暴露手牌新牌信息（伤害/格挡/描述），若真实快照字段有出入需校准

## 测试

- `tests/test_mcts.py`：V1 战斗核心（解析/动作/结算/收敛）
- `tests/test_v2.py`：V2（静默猎手机制 / SL 记忆 / 价值评分 / 路线 / 奖励 / 商店）
- `tests/test_v3.py`：V3（评估器特征与单调性 / 剪枝正确性 / 收敛）
- `tests/bench_prune.py`：剪枝开/关性能对比

运行 `python3 tests/test_v2.py && python3 tests/test_v3.py` 全部通过。

## V3 优化：状态评估器 + 支配剪枝

**状态评估器（`evaluate.py`）**
- 把战斗状态打成一个 [0,1] 期望胜率分，特征含：我方 HP、敌人已削弱程度、敌人即将威胁、我方格挡、毒潜力、无形、力量、敏捷、存活敌人数
- `state_features()` 同时输出特征向量——这是未来训练 MLP 评估器的输入（用自玩样本回归）
- 默认权重为启发式；实测加入"毒潜力"特征后，MCTS 会主动优先叠毒（符合静默猎手毒流）

**支配剪枝（`prune.py`）**
- 裁剪明显劣势的候选动作：同张牌打多目标只保留 top-2（击杀 > 高威胁 > 残血）；同名牌同目标去重
- 候选数低于阈值时直接跳过（小状态零开销）
- 效果：大状态（10 牌 4 敌）候选从 29 减到 15，4 敌场景保留率约 0.43
- 价值定位：主要提升**搜索聚焦与决策质量**（同样迭代数下树更深、更专注），整体墙钟提速受 rollout 深度主导而有限——真正的提速另需 rollout 降本 / 并行 / C++ 扩展

## 后续扩展

- 补全静默猎手全部 88 张牌效果与强度表（当前覆盖主流 S/A/B 级）
- 遗物数据库（商店买遗物、流派评估）
- 药水决策（战斗里用不用药水）
- 把 MCTS 核心改写为 C++ 扩展提速（可练 C++）
- 牌序记忆跨会话持久化、决策日志复盘
