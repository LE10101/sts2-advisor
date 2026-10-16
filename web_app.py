"""
STS2 Advisor Web Application - 公开网站版
功能：当前对局决策器、历史对局、复盘分析、怪物行为、牌序显示、LLM分析、多用户
"""
import json
import os
import time
import hashlib
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, Response, session, send_from_directory

from advisor.client import Sts2AgentClient as AutoSpireClient
from advisor.model import CombatState
from advisor.mcts import MCTS
from advisor.policy import greedy_policy
from advisor.explanation import explain_combat
from advisor.drawmemory import DrawOrderMemory
from advisor.route import choose_route
from advisor.reward import choose_reward
from advisor.shop import choose_shop
from advisor.storage import RunRecorder
from advisor.analysis import analyze_run, generate_replay_narrative
from advisor.llm import get_llm
from advisor import cloud_db
from advisor import auth

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "sts2_advisor_secret_key_change_in_production")

# 初始化用户数据库
auth.init_users_db(cloud_db.DB_PATH)

# 运行模式：local（直连游戏API）/ cloud（云端，接收agent推送）
MODE = os.environ.get("STS2_MODE", "local")

# ============ 全局状态 ============
client = AutoSpireClient(host="127.0.0.1", port=8080)
draw_memory = DrawOrderMemory()
mcts = MCTS(default_policy=greedy_policy, seed=42)

# 状态缓存（去重用）
_state_cache = {"hash": "", "data": None, "time": 0}
_recommendation_cache = {"hash": "", "data": None, "time": 0}


# ============ 工具函数 ============
def state_hash(snap):
    d = snap.get("data", snap)
    keys = ["screen", "turn", "player_hp", "energy", "hand", "enemies"]
    relevant = {k: d.get(k) for k in keys if k in d}
    if "combat" in d:
        c = d["combat"]
        relevant["combat"] = {
            "player": {k: c.get("player", {}).get(k) for k in ["current_hp", "block", "energy"]},
            "hand": [c.get("name") for c in c.get("hand", [])],
            "enemies": [{k: e.get(k) for k in ["name", "current_hp", "intent"]} for e in c.get("enemies", [])]
        }
    return hashlib.md5(json.dumps(relevant, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def get_game_state():
    try:
        snap = client.get_state()
        h = state_hash(snap)
        now = time.time()
        if h == _state_cache["hash"] and now - _state_cache["time"] < 2:
            return _state_cache["data"], False
        _state_cache["hash"] = h
        _state_cache["data"] = snap
        _state_cache["time"] = now
        return snap, True
    except Exception as e:
        return {"error": str(e), "screen": "disconnected"}, False


def get_combat_recommendation(snap):
    h = state_hash(snap)
    now = time.time()
    if h == _recommendation_cache["hash"] and now - _recommendation_cache["time"] < 3:
        return _recommendation_cache["data"]

    d = snap.get("data", snap)
    combat_snap = d.get("combat", d)
    state = CombatState.from_snapshot(combat_snap)
    draw_memory.observe_new_cards(state.hand)

    root = mcts.search(state, iterations=500)
    ranked = mcts.ranked_actions(root)
    best = ranked[0][0] if ranked else None
    reason = explain_combat(state, best, ranked)

    known_order = []
    for i in range(draw_memory.known_length()):
        c = draw_memory.peek(i)
        if c:
            known_order.append(c.name)

    result = {
        "best": action_to_dict(best, state) if best else None,
        "ranked": [{"action": action_to_dict(a, state), "value": v, "visits": n} for a, v, n in ranked[:5]],
        "reason": reason,
        "state": state_to_dict(state),
        "draw_order": known_order
    }
    _recommendation_cache["hash"] = h
    _recommendation_cache["data"] = result
    _recommendation_cache["time"] = now
    return result


def action_to_dict(action, state):
    if action.kind == "end_turn":
        return {"kind": "end_turn", "label": "结束回合"}
    if action.kind == "play_card" and action.card:
        target = "自己"
        if action.target_index >= 0 and action.target_index < len(state.enemies):
            target = state.enemies[action.target_index].name
        return {
            "kind": "play_card", "card": action.card.name,
            "cost": action.card.cost, "target": target,
            "label": f"打[{action.card.name}]\u2192{target}"
        }
    return {"kind": action.kind, "label": action.kind}


def state_to_dict(state):
    return {
        "hp": state.player_hp, "max_hp": state.player_max_hp,
        "block": state.player_block, "energy": state.energy,
        "hand": [{"name": c.name, "cost": c.cost, "playable": c.playable} for c in state.hand],
        "enemies": [{
            "name": e.name, "hp": e.hp, "max_hp": e.max_hp,
            "block": e.block, "poison": e.poison,
            "intent_type": e.intent_type, "intent_damage": e.intent_total_damage,
            "is_aoe": e.is_aoe
        } for e in state.enemies],
        "turn": state.turn
    }


def _get_user_id():
    user = auth.current_user()
    if user:
        return user["user_id"]
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        user = auth.verify_token(token)
        if user:
            return user["user_id"]
    return 0


# ============ PWA支持 ============
@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json", mimetype="application/manifest+json")

@app.route("/service-worker.js")
def service_worker():
    return send_from_directory("static", "service-worker.js", mimetype="application/javascript")

@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)

# ============ 页面路由 ============
@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

@app.route("/login")
def login_page():
    return render_template_string(LOGIN_HTML)

@app.route("/register")
def register_page():
    return render_template_string(REGISTER_HTML)

@app.route("/live")
def live():
    return render_template_string(LIVE_HTML)

@app.route("/history")
def history():
    return render_template_string(HISTORY_HTML)

@app.route("/monsters")
def monsters():
    return render_template_string(MONSTERS_HTML)

@app.route("/cards")
def cards():
    return render_template_string(CARDS_HTML)

@app.route("/replay/<run_id>")
def replay(run_id):
    return render_template_string(REPLAY_HTML, run_id=run_id)


# ============ API接口 ============
@app.route("/api/status")
def api_status():
    user_id = _get_user_id()
    if MODE == "cloud":
        live = cloud_db.get_live_state(user_id=user_id)
        if live and live["age_seconds"] < 30:
            return jsonify({"connected": True, "screen": live.get("screen", "unknown"), "mode": "cloud", "age": int(live["age_seconds"])})
        return jsonify({"connected": False, "screen": "waiting_for_agent", "mode": "cloud"})
    snap, changed = get_game_state()
    return jsonify({"connected": "error" not in snap, "screen": snap.get("screen", "unknown"), "mode": "local"})


@app.route("/api/recommend")
def api_recommend():
    user_id = _get_user_id()
    if MODE == "cloud":
        live = cloud_db.get_live_state(user_id=user_id)
        if live and live.get("recommendation"):
            return jsonify(live["recommendation"])
        return jsonify({"phase": "waiting", "message": "等待本地agent推送游戏状态...", "mode": "cloud"})
    snap, changed = get_game_state()
    if "error" in snap:
        return jsonify({"error": snap["error"]})
    screen = snap.get("data", snap).get("screen", "")
    if screen == "COMBAT":
        result = get_combat_recommendation(snap)
        result["phase"] = "combat"
    elif screen == "MAP":
        result = {"phase": "map", "recommendation": choose_route(snap)}
    elif screen == "REWARD":
        result = {"phase": "reward", "recommendation": choose_reward(snap)}
    elif screen == "SHOP":
        result = {"phase": "shop", "recommendation": choose_shop(snap)}
    else:
        result = {"phase": screen, "message": "等待游戏阶段..."}
    return jsonify(result)


@app.route("/api/history")
def api_history():
    user_id = _get_user_id()
    runs = cloud_db.list_runs(limit=50, user_id=user_id)
    return jsonify({"runs": runs})


@app.route("/api/history/<run_id>")
def api_history_detail(run_id):
    user_id = _get_user_id()
    data = cloud_db.get_run(run_id, user_id=user_id)
    if not data:
        return jsonify({"error": "对局不存在"}), 404
    return jsonify(data)


@app.route("/api/analysis/<run_id>")
def api_analysis(run_id):
    user_id = _get_user_id()
    data = cloud_db.get_run(run_id, user_id=user_id)
    if not data:
        return jsonify({"error": "对局不存在"}), 404
    analysis = analyze_run(data)
    narrative = generate_replay_narrative(data)
    return jsonify({"analysis": analysis, "narrative": narrative})


@app.route("/api/monsters")
def api_monsters():
    from advisor.monsters import MONSTER_DB
    return jsonify({"monsters": MONSTER_DB})


@app.route("/api/monsters/<monster_id>")
def api_monster_detail(monster_id):
    """怪物详情API"""
    from advisor.monsters import MONSTER_DB
    for m in MONSTER_DB:
        if m.get("id") == monster_id or m.get("name") == monster_id:
            return jsonify({"monster": m})
    return jsonify({"error": "怪物未找到"}), 404


@app.route("/api/cards")
def api_cards():
    from advisor.cards_db import SILENT_CARDS, CARD_STATS
    return jsonify({"cards": SILENT_CARDS, "stats": CARD_STATS})


@app.route("/api/cards/<card_name>")
def api_card_detail(card_name):
    """卡牌详情API"""
    from advisor.cards_db import get_card_by_name
    c = get_card_by_name(card_name)
    if c:
        return jsonify({"card": c})
    return jsonify({"error": "卡牌未找到"}), 404


# ============ 遗物API ============
@app.route("/relics")
def relics():
    return render_template_string(RELICS_HTML)

@app.route("/api/relics")
def api_relics():
    from advisor.relics_db import RELICS, RELIC_STATS
    return jsonify({"relics": RELICS, "stats": RELIC_STATS})

@app.route("/api/relics/<relic_name>")
def api_relic_detail(relic_name):
    """遗物详情API"""
    from advisor.relics_db import get_relic_by_name
    r = get_relic_by_name(relic_name)
    if r:
        return jsonify({"relic": r})
    return jsonify({"error": "遗物未找到"}), 404


# ============ 使用指南页面 ============
@app.route("/guide")
def guide():
    return render_template_string(GUIDE_HTML)

GUIDE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/game-theme.css">
<title>使用指南 - STS2决策器</title>
<style>
.container{max-width:800px;margin:0 auto;padding:30px 20px;}
h1{font-family:'Cinzel',serif;color:var(--gold);font-size:32px;margin-bottom:8px;text-shadow:0 2px 10px rgba(0,0,0,.5);}
.subtitle{color:var(--text-gray);font-size:14px;margin-bottom:30px;}
.step-card{background:linear-gradient(135deg,#2a2018 0%,#1a1410 100%);border:2px solid #4a3a25;border-radius:12px;padding:24px;margin-bottom:20px;border-left:4px solid var(--gold);}
.step-card h2{font-family:'Cinzel',serif;color:var(--gold);font-size:22px;margin-bottom:12px;}
.step-card p{color:var(--text-white);font-size:15px;line-height:1.8;margin-bottom:10px;}
.step-card code{background:var(--bg-dark);padding:2px 8px;border-radius:4px;color:var(--green-light);font-size:13px;}
.step-card ul{margin-left:20px;color:var(--text-white);font-size:14px;line-height:2;}
.step-card .tip{background:rgba(90,154,90,.15);padding:12px 16px;border-radius:8px;color:var(--green-light);font-size:13px;margin-top:12px;border-left:3px solid var(--green);}
.download-btn{display:inline-block;padding:12px 24px;background:linear-gradient(180deg,var(--gold-dark) 0%,#8a6820 100%);color:#1a1410;text-decoration:none;border-radius:6px;font-weight:bold;font-size:16px;margin-top:10px;border:2px solid var(--gold);}
.download-btn:hover{background:linear-gradient(180deg,var(--gold) 0%,var(--gold-dark) 100%);}
.feature-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-top:16px;}
.feature-item{background:var(--bg-dark);padding:14px;border-radius:8px;font-size:13px;color:var(--text-gray);border:1px solid var(--panel-border);}
.feature-item strong{color:var(--gold);display:block;margin-bottom:6px;font-size:14px;}
</style></head>
<body>
<div class="game-nav"><div class="nav-inner">
  <a href="/" class="nav-brand">STS2决策器</a>
  <a href="/live">当前对局</a>
  <a href="/history">历史对局</a>
  <a href="/monsters">怪物图鉴</a>
  <a href="/cards">卡牌图鉴</a>
  <a href="/relics">遗物图鉴</a>
  <a href="/guide" class="active">使用指南</a>
  <a href="/download">下载</a>
</div></div>
<div class="guide-container">
  <h1>📖 使用指南</h1>
  <p class="subtitle">三步上手，用AI辅助你打好每一局静默猎手</p>

  <div class="step-card">
    <h2>第一步：安装游戏mod</h2>
    <p>决策器需要通过 <strong>STS2 AI Agent mod</strong> 读取游戏状态。</p>
    <ul>
      <li>下载 STS2 AI Agent mod（GitHub: CharTyr/STS2-Agent）</li>
      <li>将 <code>STS2AIAgent.dll</code> 放入游戏目录的 <code>mods</code> 文件夹</li>
      <li>游戏路径：<code>Steam\\steamapps\\common\\Slay the Spire 2\\mods\\</code></li>
      <li>启动游戏，在mod列表中启用 STS2 AI Agent</li>
    </ul>
    <div class="tip">💡 mod会在后台启动HTTP服务（端口8080），决策器通过它读取游戏状态</div>
  </div>

  <div class="step-card">
    <h2>第二步：运行本地Agent</h2>
    <p>下载本地端程序，它会自动连接游戏并把数据推送到云端。</p>
    <ul>
      <li>下载 <a href="/static/STS2决策器-本地端.zip" style="color:#4fc3f7;">STS2决策器-本地端.zip</a></li>
      <li>解压到任意目录</li>
      <li>双击运行 <code>启动决策器.bat</code></li>
      <li>脚本会自动检查Python环境、连接游戏mod、启动Agent</li>
    </ul>
    <div class="tip">💡 确保游戏已经启动并进入主菜单，Agent才能连接成功</div>
  </div>

  <div class="step-card">
    <h2>第三步：打开网页决策</h2>
    <p>在浏览器中打开本网站，即可查看实时决策推荐。</p>
    <ul>
      <li><strong>当前对局</strong>：实时出牌推荐、怪物行为、牌序记忆</li>
      <li><strong>历史对局</strong>：查看所有对局记录和战略复盘</li>
      <li><strong>怪物图鉴</strong>：所有怪物的固定行为模式和应对策略</li>
      <li><strong>卡牌图鉴</strong>：静默猎手全卡牌效果和流派搭配</li>
      <li><strong>遗物图鉴</strong>：全遗物效果和稀有度</li>
    </ul>
    <div class="tip">💡 建议把网站添加到桌面（PWA），以后点图标就能打开</div>
  </div>

  <div class="step-card">
    <h2>功能说明</h2>
    <div class="feature-grid">
      <div class="feature-item"><strong>⚔️ 战斗决策</strong>MCTS算法实时推荐最优出牌顺序</div>
      <div class="feature-item"><strong>👹 怪物行为</strong>显示每只怪物的固定行动模式</div>
      <div class="feature-item"><strong>🃏 牌序记忆</strong>SL后自动记住抽牌顺序</div>
      <div class="feature-item"><strong>🗺️ 路线指导</strong>推荐地图最优路径</div>
      <div class="feature-item"><strong>🎁 奖励选择</strong>选卡/遗物/药水推荐</div>
      <div class="feature-item"><strong>🛒 商店购买</strong>评估商店物品性价比</div>
      <div class="feature-item"><strong>📊 战略复盘</strong>对局结束后分析流派和改进建议</div>
      <div class="feature-item"><strong>🤖 LLM分析</strong>接入大语言模型深度分析</div>
    </div>
  </div>

  <div class="step-card">
    <h2>常见问题</h2>
    <p><strong>Q: Agent连接失败怎么办？</strong><br>A: 检查游戏是否已启动、mod是否已启用、端口8080是否被占用。</p>
    <p><strong>Q: 网页显示"游戏未连接"？</strong><br>A: 确保本地Agent正在运行，且游戏已进入战斗或地图界面。</p>
    <p><strong>Q: 如何安装为App？</strong><br>A: 在Chrome/Edge中打开网站，点击地址栏的安装图标，或在菜单中选择"安装应用"。</p>
    <p><strong>Q: 数据会丢失吗？</strong><br>A> 对局历史自动同步到云端，换设备登录账号即可查看。</p>
  </div>

  <div class="step-card">
    <h2>下载资源</h2>
    <p>需要的所有文件都在这里：</p>
    <a href="/static/STS2决策器-本地端.zip" class="download-btn">📥 下载本地端 (50KB)</a>
    <a href="/static/使用指南.md" class="download-btn" style="background:#2d4a6a;color:#4fc3f7;margin-left:10px;">📄 下载使用指南</a>
  </div>
</div>
</body></html>"""


# ============ 下载页面 ============
@app.route("/download")
def download():
    return render_template_string(DOWNLOAD_HTML)

DOWNLOAD_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/game-theme.css">
<title>下载 - STS2决策器</title>
<style>
.container{max-width:800px;margin:0 auto;padding:30px 20px;}
h1{font-family:'Cinzel',serif;color:var(--gold);font-size:32px;margin-bottom:8px;text-shadow:0 2px 10px rgba(0,0,0,.5);}
.subtitle{color:var(--text-gray);font-size:14px;margin-bottom:30px;}
.download-card{background:linear-gradient(135deg,#2a2018 0%,#1a1410 100%);border:2px solid #4a3a25;border-radius:16px;padding:32px;margin-bottom:20px;text-align:center;}
.download-card .icon{font-size:64px;margin-bottom:16px;filter:drop-shadow(0 4px 8px rgba(0,0,0,.5));}
.download-card h2{font-family:'Cinzel',serif;color:var(--gold);font-size:24px;margin-bottom:8px;}
.download-card p{color:var(--text-gray);font-size:14px;margin-bottom:20px;}
.download-card .size{color:var(--green-light);font-size:13px;margin-bottom:16px;}
.btn-primary{display:inline-block;padding:14px 32px;background:linear-gradient(180deg,var(--gold-dark) 0%,#8a6820 100%);color:#1a1410;text-decoration:none;border-radius:8px;font-weight:bold;font-size:18px;border:2px solid var(--gold);}
.btn-primary:hover{background:linear-gradient(180deg,var(--gold) 0%,var(--gold-dark) 100%);}
.btn-secondary{display:inline-block;padding:12px 24px;background:transparent;color:var(--gold);text-decoration:none;border:1px solid var(--gold-dark);border-radius:6px;font-size:15px;margin-top:10px;}
.btn-secondary:hover{border-color:var(--gold);background:rgba(212,168,75,.1);}
.file-list{text-align:left;margin-top:20px;padding:16px;background:var(--bg-dark);border-radius:8px;border:1px solid var(--panel-border);}
.file-list h3{color:var(--gold);font-size:14px;margin-bottom:10px;}
.file-list ul{list-style:none;font-size:13px;color:var(--text-gray);line-height:2;}
.file-list li::before{content:"📄 ";}
.install-card{background:linear-gradient(135deg,#2a2018 0%,#1a1410 100%);border:2px solid #4a3a25;border-radius:12px;padding:24px;margin-bottom:20px;}
.install-card h2{font-family:'Cinzel',serif;color:var(--gold);font-size:20px;margin-bottom:12px;}
.install-card ol{margin-left:20px;color:var(--text-white);font-size:14px;line-height:2;}
.install-card .platform{display:inline-block;padding:4px 10px;background:var(--bg-dark);border-radius:4px;font-size:12px;color:var(--text-gray);margin-right:6px;border:1px solid var(--panel-border);}
</style></head>
<body>
<div class="game-nav"><div class="nav-inner">
  <a href="/" class="nav-brand">STS2决策器</a>
  <a href="/live">当前对局</a>
  <a href="/history">历史对局</a>
  <a href="/monsters">怪物图鉴</a>
  <a href="/cards">卡牌图鉴</a>
  <a href="/relics">遗物图鉴</a>
  <a href="/guide">使用指南</a>
  <a href="/download" class="active">下载</a>
</div></div>
<div class="download-container">
  <h1>📥 下载中心</h1>
  <p class="subtitle">下载本地端程序，一键启动AI决策辅助</p>

  <div class="download-card">
    <div class="icon">🎮</div>
    <h2>STS2 决策器 - 本地端</h2>
    <p>包含本地Agent、启动脚本、使用指南，解压即用</p>
    <div class="size">文件大小：约 50 KB · 格式：ZIP</div>
    <a href="/static/STS2决策器-本地端.zip" class="btn-primary">立即下载</a>
    <div class="file-list">
      <h3>压缩包内容：</h3>
      <ul>
        <li>cloud_agent.py - 本地云端推送Agent</li>
        <li>advisor/ - 决策器核心模块（MCTS、模拟器、卡牌库等）</li>
        <li>启动决策器.bat - 一键启动脚本</li>
        <li>使用指南.md - 详细使用说明</li>
        <li>mod安装说明.txt - STS2 AI Agent mod安装指南</li>
      </ul>
    </div>
  </div>

  <div class="download-card" style="text-align:left;">
    <h2 style="text-align:center;">📄 单独下载</h2>
    <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-top:16px;">
      <a href="/static/使用指南.md" class="btn-secondary">使用指南.md</a>
      <a href="/static/STS2决策器-本地端.zip" class="btn-secondary">本地端.zip</a>
    </div>
  </div>

  <div class="install-card">
    <h2>📱 安装为App（PWA）</h2>
    <p style="color:#8899aa;font-size:14px;margin-bottom:12px;">把网站安装到电脑/手机桌面，像App一样使用：</p>
    <ol>
      <li><span class="platform">Chrome/Edge</span> 点击地址栏右侧的安装图标（📥），或菜单 → "安装 STS2决策器"</li>
      <li><span class="platform">Safari (iOS)</span> 点击分享按钮 → "添加到主屏幕"</li>
      <li><span class="platform">Android</span> 菜单 → "添加到主屏幕" 或 "安装应用"</li>
      <li>安装后桌面会出现图标，点击直接打开决策器</li>
    </ol>
  </div>

  <div class="install-card">
    <h2>⚡ 快速开始</h2>
    <ol>
      <li>下载并解压本地端压缩包</li>
      <li>确保游戏已安装 STS2 AI Agent mod 并启动</li>
      <li>双击运行 <code style="background:#0f1923;padding:2px 6px;border-radius:4px;color:#66bb6a;">启动决策器.bat</code></li>
      <li>打开本网站，进入"当前对局"查看实时推荐</li>
    </ol>
    <p style="margin-top:16px;"><a href="/guide" style="color:#4fc3f7;">查看完整使用指南 →</a></p>
  </div>
</div>
</body></html>"""


# ============ 用户认证API ============
@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.json or {}
    result = auth.register(data.get("username", ""), data.get("password", ""))
    if result["ok"]:
        session["token"] = result["token"]
        session["user_id"] = result["user_id"]
        session["username"] = result["username"]
    return jsonify(result)


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.json or {}
    result = auth.login(data.get("username", ""), data.get("password", ""))
    if result["ok"]:
        session["token"] = result["token"]
        session["user_id"] = result["user_id"]
        session["username"] = result["username"]
    return jsonify(result)


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    token = session.get("token", "")
    if token:
        auth.logout(token)
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/me")
def api_me():
    user = auth.current_user()
    if user:
        return jsonify({"logged_in": True, "user": user})
    return jsonify({"logged_in": False})


# ============ Agent推送API ============
@app.route("/api/agent/state", methods=["POST"])
def api_agent_state():
    user_id = _get_user_id()
    data = request.json or {}
    cloud_db.update_live_state(
        data.get("screen", "unknown"), data.get("phase", "unknown"),
        data.get("state", {}), data.get("recommendation", {}), user_id=user_id
    )
    return jsonify({"ok": True, "received": True, "user_id": user_id})


@app.route("/api/agent/run", methods=["POST"])
def api_agent_run():
    user_id = _get_user_id()
    data = request.json or {}
    run_id = cloud_db.save_run(data, user_id=user_id)
    return jsonify({"ok": True, "run_id": run_id, "user_id": user_id})


@app.route("/api/agent/decision", methods=["POST"])
def api_agent_decision():
    user_id = _get_user_id()
    data = request.json or {}
    cloud_db.save_decision(
        data.get("run_id", ""), data.get("floor", 0), data.get("phase", ""),
        data.get("action", ""), data.get("reason", ""), data.get("value", 0), user_id=user_id
    )
    return jsonify({"ok": True})


@app.route("/api/llm_analyze", methods=["POST"])
def api_llm_analyze():
    data = request.json or {}
    llm = get_llm()
    analysis_type = data.get("type", "combat")
    if analysis_type == "combat":
        result = llm.analyze_combat(data.get("state", {}), data.get("recommendation", {}))
    elif analysis_type == "run":
        run_data = cloud_db.get_run(data.get("run_id", ""), user_id=_get_user_id())
        result = llm.analyze_run(run_data) if run_data else "对局不存在"
    else:
        result = "不支持的分析类型"
    return jsonify({"analysis": result, "llm_enabled": llm.enabled,
                    "model": llm.model if llm.enabled else "规则分析（未配置API Key）"})


# ============ 页面模板 ============
INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#1a1410">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="STS2决策器">
<link rel="manifest" href="/manifest.json">
<link rel="apple-touch-icon" href="/static/icon-192.png">
<link rel="icon" type="image/png" href="/static/icon-192.png">
<link rel="stylesheet" href="/static/game-theme.css">
<title>STS2 决策器 - 静默猎手AI教练</title>
<style>
/* 首页专属样式 */
.hero { text-align:center; padding:50px 20px 30px; }
.hero h1 { font-family:'Cinzel',serif; font-size:42px; color:var(--gold); text-shadow:0 2px 20px rgba(0,0,0,.7),0 0 40px rgba(212,168,75,.3); margin-bottom:12px; }
.hero p { color:var(--text-gray); font-size:16px; max-width:600px; margin:0 auto; }
.hero .subtitle { color:var(--gold-dark); font-size:14px; margin-top:8px; letter-spacing:2px; }
.card-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:20px; max-width:1200px; margin:30px auto; padding:0 20px; }
.feature-card { background:linear-gradient(135deg,#2a2018 0%,#1a1410 100%); border:2px solid #4a3a25; border-radius:12px; padding:28px 24px; cursor:pointer; transition:all .3s; text-decoration:none; color:inherit; display:block; position:relative; overflow:hidden; }
.feature-card::before { content:''; position:absolute; top:0; left:0; right:0; height:4px; background:linear-gradient(90deg,transparent,var(--gold),transparent); opacity:0; transition:opacity .3s; }
.feature-card:hover { border-color:var(--gold); transform:translateY(-4px); box-shadow:0 8px 30px rgba(212,168,75,.2); }
.feature-card:hover::before { opacity:1; }
.feature-card .icon { font-size:40px; margin-bottom:16px; filter:drop-shadow(0 2px 4px rgba(0,0,0,.5)); }
.feature-card h3 { font-family:'Cinzel',serif; color:var(--gold); font-size:20px; margin-bottom:10px; }
.feature-card p { color:var(--text-gray); font-size:14px; line-height:1.7; }
.feature-card .status { display:inline-block; padding:4px 12px; border-radius:20px; font-size:12px; margin-top:14px; font-weight:700; }
.feature-card .status.online { background:rgba(90,154,90,.2); color:var(--green-light); border:1px solid var(--green); }
.feature-card .status.offline { background:rgba(201,74,74,.2); color:var(--red-light); border:1px solid var(--red); }
.user-menu { display:flex; align-items:center; gap:12px; }
.user-menu a { color:var(--gold); text-decoration:none; font-size:14px; padding:6px 14px; border:1px solid var(--gold-dark); border-radius:4px; transition:all .2s; }
.user-menu a:hover { background:rgba(212,168,75,.1); border-color:var(--gold); }
.user-menu .username { color:var(--green-light); font-size:14px; }
/* 首次访问弹窗 */
.welcome-modal { display:none; position:fixed; inset:0; background:rgba(0,0,0,.85); z-index:1000; align-items:center; justify-content:center; padding:20px; }
.welcome-modal.show { display:flex; }
.welcome-box { background:linear-gradient(135deg,#2a2018 0%,#1a1410 100%); border:3px solid var(--gold-dark); border-radius:12px; padding:36px; max-width:520px; width:100%; box-shadow:0 20px 60px rgba(0,0,0,.7),0 0 40px rgba(212,168,75,.15); }
.welcome-box h2 { font-family:'Cinzel',serif; color:var(--gold); font-size:26px; margin-bottom:20px; text-align:center; }
.step-item { display:flex; gap:16px; margin-bottom:18px; align-items:flex-start; }
.step-num { background:linear-gradient(135deg,var(--gold) 0%,var(--gold-dark) 100%); color:var(--bg-dark); width:32px; height:32px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:16px; flex-shrink:0; }
.step-text { color:var(--text-white); font-size:14px; line-height:1.7; }
.step-text strong { color:var(--gold-light); }
.welcome-box .close-btn { width:100%; padding:14px; background:linear-gradient(180deg,var(--gold-dark) 0%,#8a6820 100%); color:#1a1410; border:2px solid var(--gold); border-radius:6px; font-size:16px; font-weight:700; cursor:pointer; margin-top:10px; font-family:'Kreon',serif; }
.welcome-box .close-btn:hover { background:linear-gradient(180deg,var(--gold) 0%,var(--gold-dark) 100%); }
.welcome-box .skip-link { display:block; text-align:center; color:var(--text-dim); font-size:12px; margin-top:14px; cursor:pointer; text-decoration:underline; }
</style>
</head>
<body>
<!-- 导航栏 -->
<div class="game-nav"><div class="nav-inner">
  <a href="/" class="nav-brand">⚔️ STS2决策器</a>
  <a href="/live">当前对局</a>
  <a href="/history">历史对局</a>
  <a href="/monsters">怪物图鉴</a>
  <a href="/cards">卡牌图鉴</a>
  <a href="/relics">遗物图鉴</a>
  <a href="/guide">使用指南</a>
  <a href="/download">下载</a>
</div></div>

<!-- 主标题 -->
<div class="game-title">
  <h1>STS2 决策器</h1>
  <p>杀戮尖塔2 · 静默猎手AI教练</p>
  <div class="user-menu" id="userMenu" style="margin-top:16px;justify-content:center;display:flex;"><a href="/login">登录</a><a href="/register">注册</a></div>
</div>

<!-- 游戏内图鉴主菜单样式 - 四张羊皮纸卡片 -->
<div class="codex-menu">
  <a class="codex-menu-card brown" href="/cards">
    <div class="icon">🃏</div>
    <h3>卡牌总览</h3>
    <p>静默猎手全卡牌<br>效果 · 升级 · 流派</p>
  </a>
  <a class="codex-menu-card blue" href="/relics">
    <div class="icon">🏺</div>
    <h3>遗物收集</h3>
    <p>全遗物效果<br>稀有度 · 适配</p>
  </a>
  <a class="codex-menu-card green" href="/monsters">
    <div class="icon">👹</div>
    <h3>怪物图鉴</h3>
    <p>怪物行为模式<br>伤害 · 应对策略</p>
  </a>
  <a class="codex-menu-card red" href="/live">
    <div class="icon">⚔️</div>
    <h3>当前对局</h3>
    <p>实时AI决策<br>牌序 · 路线指导</p>
  </a>
</div>

<!-- 其他功能 -->
<div style="max-width:900px;margin:0 auto;padding:0 20px 40px;">
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;">
    <a href="/history" style="display:block;padding:16px;background:linear-gradient(135deg,#1e1a14,#141210);border:1px solid var(--border-dark);border-radius:6px;text-align:center;text-decoration:none;color:var(--text-cream);transition:all .2s;" onmouseover="this.style.borderColor='var(--gold)';this.style.color='var(--gold-light)'" onmouseout="this.style.borderColor='var(--border-dark)';this.style.color='var(--text-cream)'">
      <div style="font-size:24px;margin-bottom:6px;">📊</div>
      <div style="font-size:14px;font-weight:600;">历史对局</div>
    </a>
    <a href="/guide" style="display:block;padding:16px;background:linear-gradient(135deg,#1e1a14,#141210);border:1px solid var(--border-dark);border-radius:6px;text-align:center;text-decoration:none;color:var(--text-cream);transition:all .2s;" onmouseover="this.style.borderColor='var(--gold)';this.style.color='var(--gold-light)'" onmouseout="this.style.borderColor='var(--border-dark)';this.style.color='var(--text-cream)'">
      <div style="font-size:24px;margin-bottom:6px;">📖</div>
      <div style="font-size:14px;font-weight:600;">使用指南</div>
    </a>
    <a href="/download" style="display:block;padding:16px;background:linear-gradient(135deg,#1e1a14,#141210);border:1px solid var(--border-dark);border-radius:6px;text-align:center;text-decoration:none;color:var(--text-cream);transition:all .2s;" onmouseover="this.style.borderColor='var(--gold)';this.style.color='var(--gold-light)'" onmouseout="this.style.borderColor='var(--border-dark)';this.style.color='var(--text-cream)'">
      <div style="font-size:24px;margin-bottom:6px;">📥</div>
      <div style="font-size:14px;font-weight:600;">下载本地端</div>
    </a>
  </div>
  <div style="text-align:center;margin-top:16px;">
    <span class="status" id="liveStatus" style="display:inline-block;padding:4px 12px;border-radius:3px;font-size:12px;background:rgba(184,64,64,.15);color:var(--red-light);border:1px solid var(--red);">检测游戏连接...</span>
  </div>
</div>

<!-- 首次访问弹窗 -->
<div class="welcome-modal" id="welcomeModal">
  <div class="welcome-box">
    <h2>👋 欢迎使用 STS2 决策器</h2>
    <div class="step-item"><div class="step-num">1</div><div class="step-text"><strong>安装游戏mod</strong><br>下载并安装 STS2 AI Agent mod，让决策器能读取游戏状态</div></div>
    <div class="step-item"><div class="step-num">2</div><div class="step-text"><strong>运行本地Agent</strong><br>下载本地端压缩包，运行启动脚本，自动连接游戏</div></div>
    <div class="step-item"><div class="step-num">3</div><div class="step-text"><strong>打开网页决策</strong><br>在本网站查看实时推荐、怪物行为、牌序记忆和战略复盘</div></div>
    <button class="close-btn" onclick="closeWelcome()">我知道了，开始使用</button>
    <span class="skip-link" onclick="closeWelcome()">不再显示</span>
  </div>
</div>

<div class="footer">STS2 Advisor v11.0 · 基于MCTS+评估器 · 数据来自STS2 AI Agent mod · 游戏风格UI</div>
<script>
fetch('/api/auth/me').then(r=>r.json()).then(d=>{
  const menu=document.getElementById('userMenu');
  if(d.logged_in){menu.innerHTML='<span class="username">'+d.user.username+'</span><a href="#" onclick="logout()">登出</a>';}
});
function logout(){fetch('/api/auth/logout',{method:'POST'}).then(()=>location.href='/');}
fetch('/api/status').then(r=>r.json()).then(d=>{
  const el=document.getElementById('liveStatus');
  if(d.connected){el.textContent='游戏已连接';el.className='status online';}
  else{el.textContent='游戏未连接';el.className='status offline';}
});
if('serviceWorker' in navigator){navigator.serviceWorker.register('/service-worker.js').catch(()=>{});}
function closeWelcome(){document.getElementById('welcomeModal').classList.remove('show');localStorage.setItem('sts2_welcome_shown','1');}
if(!localStorage.getItem('sts2_welcome_shown')){setTimeout(()=>document.getElementById('welcomeModal').classList.add('show'),500);}
</script>
</body>
</html>"""

LOGIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/game-theme.css">
<title>登录 - STS2决策器</title>
<style>
.login-wrap{max-width:420px;margin:60px auto;padding:0 20px;}
.login-box{background:linear-gradient(135deg,#2a2018,#1a120c);border:2px solid var(--gold-dark);border-radius:8px;padding:36px;box-shadow:0 20px 60px rgba(0,0,0,.6);}
.login-box h1{font-family:'Cinzel',serif;color:var(--gold);text-align:center;margin-bottom:8px;font-size:28px;}
.login-box .subtitle{text-align:center;color:var(--text-gray);margin-bottom:28px;font-size:14px;}
.error{background:rgba(184,64,64,.15);border:1px solid var(--red);color:var(--red-light);padding:10px 14px;border-radius:4px;margin-bottom:16px;font-size:13px;}
</style></head>
<body>
<div class="game-nav"><div class="nav-inner">
  <a href="/" class="nav-brand">⚔️ STS2决策器</a>
  <a href="/live">当前对局</a><a href="/history">历史对局</a>
  <a href="/monsters">怪物图鉴</a><a href="/cards">卡牌图鉴</a>
  <a href="/relics">遗物图鉴</a><a href="/guide">使用指南</a><a href="/download">下载</a>
</div></div>
<div class="login-wrap">
  <div class="login-box">
    <h1>⚔️ 登录</h1>
    <div class="subtitle">STS2 决策器 · 静默猎手AI教练</div>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="POST" action="/login">
      <div class="form-group"><label>用户名</label><input type="text" name="username" required placeholder="输入用户名"></div>
      <div class="form-group"><label>密码</label><input type="password" name="password" required placeholder="输入密码"></div>
      <button type="submit" class="btn primary" style="width:100%;margin-top:10px;">登 录</button>
    </form>
    <div style="text-align:center;margin-top:20px;font-size:13px;color:var(--text-gray);">
      还没有账号？<a href="/register" style="color:var(--gold);">立即注册</a>
    </div>
  </div>
</div>
</body></html>"""

REGISTER_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/game-theme.css">
<title>注册 - STS2决策器</title>
<style>
.register-wrap{max-width:420px;margin:60px auto;padding:0 20px;}
.register-box{background:linear-gradient(135deg,#2a2018,#1a120c);border:2px solid var(--gold-dark);border-radius:8px;padding:36px;box-shadow:0 20px 60px rgba(0,0,0,.6);}
.register-box h1{font-family:'Cinzel',serif;color:var(--gold);text-align:center;margin-bottom:8px;font-size:28px;}
.register-box .subtitle{text-align:center;color:var(--text-gray);margin-bottom:28px;font-size:14px;}
.error{background:rgba(184,64,64,.15);border:1px solid var(--red);color:var(--red-light);padding:10px 14px;border-radius:4px;margin-bottom:16px;font-size:13px;}
</style></head>
<body>
<div class="game-nav"><div class="nav-inner">
  <a href="/" class="nav-brand">⚔️ STS2决策器</a>
  <a href="/live">当前对局</a><a href="/history">历史对局</a>
  <a href="/monsters">怪物图鉴</a><a href="/cards">卡牌图鉴</a>
  <a href="/relics">遗物图鉴</a><a href="/guide">使用指南</a><a href="/download">下载</a>
</div></div>
<div class="register-wrap">
  <div class="register-box">
    <h1>📜 注册</h1>
    <div class="subtitle">创建账号，云端同步你的对局数据</div>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="POST" action="/register">
      <div class="form-group"><label>用户名</label><input type="text" name="username" required placeholder="3-20个字符"></div>
      <div class="form-group"><label>密码</label><input type="password" name="password" required placeholder="至少6个字符"></div>
      <div class="form-group"><label>确认密码</label><input type="password" name="password2" required placeholder="再次输入密码"></div>
      <button type="submit" class="btn primary" style="width:100%;margin-top:10px;">注 册</button>
    </form>
    <div style="text-align:center;margin-top:20px;font-size:13px;color:var(--text-gray);">
      已有账号？<a href="/login" style="color:var(--gold);">直接登录</a>
    </div>
  </div>
</div>
</body></html>"""

LIVE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/game-theme.css">
<title>当前对局 - STS2决策器</title>
<style>
.live-container{max-width:1200px;margin:0 auto;padding:20px;}
.status-panel{background:linear-gradient(135deg,#2a2018,#1a120c);border:2px solid #4a3a25;border-radius:8px;padding:20px;margin-bottom:16px;}
.status-row{display:flex;gap:20px;flex-wrap:wrap;align-items:center;}
.status-item{display:flex;align-items:center;gap:8px;font-size:15px;}
.status-item .icon{font-size:22px;}
.status-item.hp{color:var(--red-light);}
.status-item.gold{color:var(--gold);}
.status-item.floor{color:var(--blue-light);}
.phase-badge{padding:4px 12px;border-radius:3px;font-size:13px;font-weight:600;}
.phase-combat{background:rgba(184,64,64,.2);color:var(--red-light);border:1px solid var(--red);}
.phase-map{background:rgba(74,122,184,.2);color:var(--blue-light);border:1px solid var(--blue);}
.phase-reward{background:rgba(90,138,74,.2);color:var(--green-light);border:1px solid var(--green);}
.phase-shop{background:rgba(201,162,39,.2);color:var(--gold);border:1px solid var(--gold);}
.recommendation{background:linear-gradient(135deg,#2a2018,#1a120c);border:2px solid var(--gold-dark);border-radius:8px;padding:20px;margin-bottom:16px;}
.recommendation h3{font-family:'Cinzel',serif;color:var(--gold);font-size:18px;margin-bottom:12px;}
.rec-item{padding:10px 14px;background:rgba(201,162,39,.08);border-left:3px solid var(--gold);border-radius:0 4px 4px 0;margin-bottom:8px;font-size:14px;color:var(--text-cream);}
.rec-item .score{float:right;color:var(--gold);font-weight:700;}
.monster-panel{background:linear-gradient(135deg,#2a2018,#1a120c);border:2px solid #4a3a25;border-radius:8px;padding:16px;margin-bottom:16px;}
.monster-panel h4{color:var(--red-light);margin-bottom:10px;font-size:15px;}
.monster-intent{display:inline-block;padding:4px 10px;background:rgba(184,64,64,.15);border-radius:3px;font-size:13px;color:var(--red-light);margin-right:8px;}
.deck-panel{background:linear-gradient(135deg,#2a2018,#1a120c);border:2px solid #4a3a25;border-radius:8px;padding:16px;}
.deck-panel h4{color:var(--gold);margin-bottom:10px;font-size:15px;}
.draw-pile{display:flex;flex-wrap:wrap;gap:6px;}
.draw-card{padding:4px 10px;background:var(--bg-deepest);border:1px solid #3a2f20;border-radius:3px;font-size:12px;color:var(--text-cream);}
.disconnected{text-align:center;padding:80px 20px;color:var(--text-dim);}
.disconnected .icon{font-size:64px;margin-bottom:16px;}
.disconnected h2{color:var(--gold);margin-bottom:8px;}
</style></head>
<body>
<div class="game-nav"><div class="nav-inner">
  <a href="/" class="nav-brand">⚔️ STS2决策器</a>
  <a href="/live" class="active">当前对局</a><a href="/history">历史对局</a>
  <a href="/monsters">怪物图鉴</a><a href="/cards">卡牌图鉴</a>
  <a href="/relics">遗物图鉴</a><a href="/guide">使用指南</a><a href="/download">下载</a>
</div></div>
<div class="page-header"><h1>⚔️ 当前对局</h1><p>实时战斗决策 · 怪物行为 · 牌序记忆</p></div>
<div class="live-container" id="liveContent">
  <div class="disconnected"><div class="icon">🎮</div><h2>等待游戏连接...</h2><p>请确保游戏已启动，本地Agent正在运行</p><p style="margin-top:10px;font-size:13px;">每3秒自动刷新</p></div>
</div>
<script>
let lastHash='';
function refresh(){
  fetch('/api/live').then(r=>r.json()).then(d=>{
    if(d.error||!d.connected){
      document.getElementById('liveContent').innerHTML='<div class="disconnected"><div class="icon">🎮</div><h2>等待游戏连接...</h2><p>请确保游戏已启动，本地Agent正在运行</p></div>';
      return;
    }
    const hash=JSON.stringify(d).length+d.phase+d.floor;
    if(hash===lastHash)return;lastHash=hash;
    let html='';
    html+='<div class="status-panel"><div class="status-row">';
    html+='<span class="phase-badge phase-'+d.phase+'">'+d.phase_name+'</span>';
    html+='<span class="status-item hp"><span class="icon">❤️</span>'+(d.hp||0)+'/'+(d.max_hp||70)+'</span>';
    html+='<span class="status-item gold"><span class="icon">🪙</span>'+(d.gold||0)+'</span>';
    html+='<span class="status-item floor"><span class="icon">🏔️</span>楼层 '+(d.floor||0)+'</span>';
    html+='<span class="status-item"><span class="icon">🃏</span>'+(d.deck_size||0)+'张</span>';
    html+='</div></div>';
    if(d.monsters&&d.monsters.length){
      html+='<div class="monster-panel"><h4>👹 敌人 ('+d.monsters.length+')</h4>';
      d.monsters.forEach(m=>{
        html+='<div style="margin-bottom:8px;"><strong style="color:var(--text-cream);">'+m.name+'</strong> '+(m.hp?'<span style="color:var(--red-light);">'+m.hp+'HP</span>':'');
        if(m.intent)html+=' <span class="monster-intent">'+m.intent+'</span>';
        html+='</div>';
      });
      html+='</div>';
    }
    if(d.recommendations&&d.recommendations.length){
      html+='<div class="recommendation"><h3>✨ AI推荐</h3>';
      d.recommendations.forEach((r,i)=>{
        html+='<div class="rec-item">'+(i+1)+'. '+r.action+' <span class="score">'+r.score.toFixed(1)+'</span></div>';
      });
      html+='</div>';
    }
    if(d.draw_pile&&d.draw_pile.length){
      html+='<div class="deck-panel"><h4>📚 抽牌堆 ('+d.draw_pile.length+')</h4><div class="draw-pile">';
      d.draw_pile.forEach(c=>{html+='<span class="draw-card">'+c+'</span>';});
      html+='</div></div>';
    }
    document.getElementById('liveContent').innerHTML=html;
  }).catch(()=>{});
}
refresh();setInterval(refresh,3000);
</script>
</body></html>"""

HISTORY_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/game-theme.css">
<title>历史对局 - STS2决策器</title>
<style>
.history-container{max-width:1000px;margin:0 auto;padding:20px;}
.history-item{background:linear-gradient(135deg,#2a2018,#1a120c);border:2px solid #4a3a25;border-radius:8px;padding:16px 20px;margin-bottom:12px;cursor:pointer;transition:all .2s;display:flex;align-items:center;gap:16px;}
.history-item:hover{border-color:var(--gold);transform:translateX(4px);}
.history-item .char-icon{width:48px;height:48px;background:linear-gradient(135deg,#2a4a2a,#1a3a1a);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:24px;border:2px solid var(--silent);flex-shrink:0;}
.history-item .info{flex:1;min-width:0;}
.history-item .title{color:var(--gold);font-size:16px;font-weight:600;margin-bottom:4px;}
.history-item .meta{color:var(--text-gray);font-size:13px;display:flex;gap:14px;flex-wrap:wrap;}
.history-item .result{padding:4px 12px;border-radius:3px;font-size:13px;font-weight:600;flex-shrink:0;}
.result-win{background:rgba(90,138,74,.2);color:var(--green-bright);border:1px solid var(--green);}
.result-lose{background:rgba(184,64,64,.2);color:var(--red-light);border:1px solid var(--red);}
.result-ongoing{background:rgba(74,122,184,.2);color:var(--blue-light);border:1px solid var(--blue);}
.filters{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;}
.empty{text-align:center;padding:60px;color:var(--text-dim);}
.empty .icon{font-size:48px;margin-bottom:12px;}
</style></head>
<body>
<div class="game-nav"><div class="nav-inner">
  <a href="/" class="nav-brand">⚔️ STS2决策器</a>
  <a href="/live">当前对局</a><a href="/history" class="active">历史对局</a>
  <a href="/monsters">怪物图鉴</a><a href="/cards">卡牌图鉴</a>
  <a href="/relics">遗物图鉴</a><a href="/guide">使用指南</a><a href="/download">下载</a>
</div></div>
<div class="page-header"><h1>📊 历史对局</h1><p>查看所有对局记录 · 战略复盘分析</p></div>
<div class="history-container">
  <div class="filters">
    <button class="filter-btn active" onclick="filterHistory('all',this)">全部</button>
    <button class="filter-btn" onclick="filterHistory('win',this)">胜利</button>
    <button class="filter-btn" onclick="filterHistory('lose',this)">失败</button>
  </div>
  <div id="historyList"><div class="empty"><div class="icon">📜</div>暂无对局记录<br><span style="font-size:13px;">开始游戏后自动记录</span></div></div>
</div>
<script>
let allRuns=[];
fetch('/api/history').then(r=>r.json()).then(d=>{
  allRuns=d.runs||[];
  renderHistory('all');
}).catch(()=>{
  document.getElementById('historyList').innerHTML='<div class="empty"><div class="icon">⚠️</div>请先登录后查看历史记录</div>';
});
function filterHistory(type,btn){
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderHistory(type);
}
function renderHistory(type){
  let list=allRuns;
  if(type==='win')list=list.filter(r=>r.result==='胜利'||r.result==='win');
  if(type==='lose')list=list.filter(r=>r.result==='失败'||r.result==='lose');
  const el=document.getElementById('historyList');
  if(!list.length){el.innerHTML='<div class="empty"><div class="icon">📜</div>暂无对局记录</div>';return;}
  el.innerHTML=list.map(r=>{
    const resultCls=r.result==='胜利'||r.result==='win'?'result-win':(r.result==='失败'||r.result==='lose'?'result-lose':'result-ongoing');
    return '<div class="history-item" onclick="location.href='/replay/'+r.id+''">'+
      '<div class="char-icon">🐍</div>'+
      '<div class="info"><div class="title">静默猎手 · 进阶'+(r.ascension||0)+'</div>'+
      '<div class="meta"><span>❤️ '+(r.current_hp||0)+'/'+(r.max_hp||70)+'</span><span>🪙 '+(r.gold||0)+'</span><span>🏔️ '+(r.max_floor||0)+'层</span><span>🃏 '+(r.deck_size||0)+'张</span><span>'+(r.date||'')+'</span></div></div>'+
      '<span class="result '+resultCls+'">'+(r.result||'进行中')+'</span></div>';
  }).join('');
}
</script>
</body></html>"""

MONSTERS_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/game-theme.css">
<title>怪物图鉴 - STS2决策器</title>
<style>
.empty{text-align:center;padding:40px;color:var(--text-dim);font-size:14px;}
</style></head>
<body>
<div class="game-nav"><div class="nav-inner">
  <a href="/" class="brand">⚔️ STS2</a>
  <a href="/live">当前对局</a><a href="/history">历史对局</a>
  <a href="/monsters" class="active">怪物图鉴</a><a href="/cards">卡牌图鉴</a>
  <a href="/relics">遗物图鉴</a><a href="/guide">指南</a><a href="/download">下载</a>
</div></div>
<div class="monster-three-col">
  <div class="monster-actions-col">
    <h3>行动列表</h3>
    <div id="actions"><div class="empty">选择怪物查看行动</div></div>
  </div>
  <div class="monster-center-col" id="display">
    <div style="color:var(--text-dim);font-size:16px;">← 从右侧选择怪物</div>
  </div>
  <div class="monster-list-col" id="list"></div>
</div>
<script>
let allMonsters=[];
fetch('/api/monsters').then(r=>r.json()).then(d=>{
  allMonsters=d.monsters||[];
  renderList();
  if(allMonsters.length)selectMonster(allMonsters[0].id);
});
function renderList(){
  const chapters={};
  allMonsters.forEach(m=>{const c=m.chapter||'未知';if(!chapters[c])chapters[c]=[];chapters[c].push(m);});
  let html='';
  Object.entries(chapters).forEach(([ch,monsters])=>{
    html+='<div class="monster-chapter"><div class="monster-chapter-title">'+ch+'</div>';
    monsters.forEach(m=>{
      const cls=m.is_elite?'elite':(m.is_boss?'boss':'');
      html+='<div class="monster-list-item '+cls+'" data-id="'+m.id+'" onclick="selectMonster(''+m.id+'')">'+
        (m.image_url?'<img src="'+m.image_url+'" style="width:22px;height:22px;object-fit:contain;">':'👹')+m.name+'</div>';
    });
    html+='</div>';
  });
  document.getElementById('list').innerHTML=html;
}
function selectMonster(id){
  const m=allMonsters.find(x=>x.id===id);if(!m)return;
  document.querySelectorAll('.monster-list-item').forEach(el=>el.classList.remove('selected'));
  document.querySelector('[data-id="'+id+'"]')?.classList.add('selected');
  document.getElementById('display').innerHTML=
    (m.image_url?'<img src="'+m.image_url+'" onerror="this.style.display='none'">':'')+
    '<div class="m-name">'+m.name+'</div>'+
    (m.hp?'<div class="m-hp">❤️ '+m.hp+'</div>':'')+
    (m.strategy?'<div class="m-strategy"><strong style="color:var(--green-light);">应对策略</strong><br>'+m.strategy+'</div>':'');
  const actions=m.actions||[];
  document.getElementById('actions').innerHTML=actions.length?
    actions.map(a=>'<div class="monster-action"><div class="a-name">'+a.name+'</div>'+
    (a.damage?'<div class="a-dmg">伤害: '+a.damage+'</div>':'')+
    (a.effect?'<div style="font-size:11px;color:var(--text-gray);margin-top:2px;">'+a.effect+'</div>':'')+'</div>').join('')
    :'<div class="empty">暂无行动数据</div>';
}
</script>
</body></html>"""

CARDS_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/game-theme.css">
<title>卡牌总览 - STS2决策器</title>
<style>
.codex-stats{display:flex;gap:8px;padding:10px 20px;background:rgba(0,0,0,.3);border-bottom:1px solid var(--border-dark);flex-wrap:wrap;}
.codex-stats .st{padding:4px 10px;background:rgba(255,255,255,.03);border-radius:3px;font-size:12px;color:var(--text-gray);}
.codex-stats .st b{color:var(--gold);}
.empty{text-align:center;padding:60px;color:var(--text-dim);grid-column:1/-1;}
</style></head>
<body>
<div class="game-nav"><div class="nav-inner">
  <a href="/" class="brand">⚔️ STS2</a>
  <a href="/live">当前对局</a><a href="/history">历史对局</a>
  <a href="/monsters">怪物图鉴</a><a href="/cards" class="active">卡牌图鉴</a>
  <a href="/relics">遗物图鉴</a><a href="/guide">指南</a><a href="/download">下载</a>
</div></div>
<div class="codex-layout">
  <div class="codex-sidebar">
    <input type="text" class="search-box" id="search" placeholder="搜索卡牌..." oninput="renderCards()">
    <div class="filter-group">
      <div class="filter-label">类型</div>
      <button class="filter-option active" data-f="all">全部</button>
      <button class="filter-option" data-f="攻击">攻击</button>
      <button class="filter-option" data-f="技能">技能</button>
      <button class="filter-option" data-f="能力">能力</button>
      <button class="filter-option" data-f="诅咒">诅咒</button>
    </div>
    <div class="filter-group">
      <div class="filter-label">稀有度</div>
      <button class="filter-option" data-r="基础">基础</button>
      <button class="filter-option" data-r="普通">普通</button>
      <button class="filter-option" data-r="罕见">罕见</button>
      <button class="filter-option" data-r="稀有">稀有</button>
    </div>
    <div class="filter-group">
      <div class="filter-label">费用</div>
      <button class="filter-option" data-c="0">0费</button>
      <button class="filter-option" data-c="1">1费</button>
      <button class="filter-option" data-c="2">2费</button>
      <button class="filter-option" data-c="3">3费+</button>
    </div>
  </div>
  <div class="codex-main">
    <div class="codex-stats" id="stats"></div>
    <div class="codex-card-grid" id="grid" style="padding:16px 0;"></div>
  </div>
</div>
<div class="modal-overlay" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal-box"><button class="close" onclick="closeModal()">×</button><div id="modal-content"></div></div>
</div>
<script>
let allCards=[],curF='all',curR=null,curC=null;
fetch('/api/cards').then(r=>r.json()).then(d=>{allCards=d.cards||[];renderStats();renderCards();});
function renderStats(){
  const s={};allCards.forEach(c=>{s[c.rarity]=(s[c.rarity]||0)+1;});
  document.getElementById('stats').innerHTML='<div class="st"><b>'+allCards.length+'</b> 张卡牌</div>'+
    Object.entries(s).map(([r,n])=>'<div class="st"><b>'+n+'</b> '+r+'</div>').join('');
}
document.querySelector('.codex-sidebar').addEventListener('click',e=>{
  if(e.target.classList.contains('filter-option')){
    const f=e.target.dataset.f,r=e.target.dataset.r,c=e.target.dataset.c;
    e.target.parentElement.querySelectorAll('.filter-option').forEach(b=>b.classList.remove('active'));
    e.target.classList.add('active');
    if(f!==undefined){curF=f;}
    if(r!==undefined){curR=curR===r?null:r;if(curR)e.target.classList.add('active');}
    if(c!==undefined){curC=curC===c?null:c;if(curC)e.target.classList.add('active');}
    renderCards();
  }
});
function renderCards(){
  const q=document.getElementById('search').value.toLowerCase();
  let list=allCards;
  if(curF!=='all')list=list.filter(c=>c.type===curF);
  if(curR)list=list.filter(c=>c.rarity===curR);
  if(curC){if(curC==='3')list=list.filter(c=>c.cost>=3);else list=list.filter(c=>c.cost==parseInt(curC));}
  if(q)list=list.filter(c=>c.name_cn.toLowerCase().includes(q)||c.name_en.toLowerCase().includes(q)||c.effect.toLowerCase().includes(q));
  const el=document.getElementById('grid');
  if(!list.length){el.innerHTML='<div class="empty">未找到卡牌</div>';return;}
  el.innerHTML=list.map(c=>{
    const img=c.image_url?'<img class="game-card-img" src="'+c.image_url+'" onclick="showDetail(''+c.id+'')" onerror="this.outerHTML='<div style=\'width:100%;height:260px;background:linear-gradient(135deg,#2a2018,#1a120c);border:2px solid #4a3a25;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:48px;cursor:pointer;\' onclick=\'showDetail("'+c.id+'")\'>🃏</div>'">':
    '<div style="width:100%;height:260px;background:linear-gradient(135deg,#2a2018,#1a120c);border:2px solid #4a3a25;border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:48px;cursor:pointer;" onclick="showDetail(''+c.id+'')">🃏</div>';
    return img;
  }).join('');
}
function showDetail(id){
  const c=allCards.find(x=>x.id===id);if(!c)return;
  document.getElementById('modal-content').innerHTML=
    '<div style="display:flex;gap:20px;align-items:flex-start;">'+
    (c.image_url?'<img src="'+c.image_url+'" style="width:200px;border-radius:4px;box-shadow:0 4px 16px rgba(0,0,0,.6);">':'')+
    '<div style="flex:1;">'+
    '<h2>'+c.name_cn+'</h2>'+
    '<div style="color:var(--text-gray);font-size:13px;margin-bottom:14px;">'+c.name_en+' · '+c.type+' · '+c.rarity+' · '+c.cost+'费</div>'+
    '<div class="form-group"><label>效果</label><div style="color:var(--text-cream);line-height:1.7;">'+c.effect+'</div></div>'+
    (c.upgraded?'<div class="form-group"><label>升级效果</label><div style="color:var(--green-light);line-height:1.7;">'+c.upgraded+'</div></div>':'')+
    (c.synergy?'<div class="form-group"><label>流派适配</label><div style="color:var(--text-cream);line-height:1.7;">'+c.synergy+'</div></div>':'')+
    '</div></div>';
  document.getElementById('modal').classList.add('show');
}
function closeModal(){document.getElementById('modal').classList.remove('show');}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});
</script>
</body></html>"""

RELICS_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/game-theme.css">
<title>遗物收集 - STS2决策器</title>
<style>
.relic-toolbar{display:flex;gap:8px;padding:12px 20px;background:rgba(0,0,0,.3);border-bottom:1px solid var(--border-dark);align-items:center;flex-wrap:wrap;}
.relic-toolbar input{padding:7px 12px;background:var(--bg-black);border:1px solid var(--border-dark);border-radius:3px;color:var(--text-white);font-size:13px;font-family:'Kreon',serif;outline:none;min-width:200px;}
.relic-toolbar input:focus{border-color:var(--gold-dim);}
.empty{text-align:center;padding:40px;color:var(--text-dim);}
</style></head>
<body>
<div class="game-nav"><div class="nav-inner">
  <a href="/" class="brand">⚔️ STS2</a>
  <a href="/live">当前对局</a><a href="/history">历史对局</a>
  <a href="/monsters">怪物图鉴</a><a href="/cards">卡牌图鉴</a>
  <a href="/relics" class="active">遗物图鉴</a><a href="/guide">指南</a><a href="/download">下载</a>
</div></div>
<div class="relic-toolbar">
  <input type="text" id="search" placeholder="搜索遗物..." oninput="renderRelics()">
  <span style="color:var(--text-gray);font-size:13px;" id="total"></span>
</div>
<div id="relicContent"></div>
<div class="modal-overlay" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal-box"><button class="close" onclick="closeModal()">×</button><div id="modal-content"></div></div>
</div>
<script>
let allRelics=[];
const rarityOrder=['初始','普通','罕见','稀有','古代','先古','Boss','事件','商店'];
fetch('/api/relics').then(r=>r.json()).then(d=>{
  allRelics=d.relics||[];
  document.getElementById('total').textContent='共 '+allRelics.length+' 个遗物';
  renderRelics();
});
function rarityClass(r){
  if(r==='初始')return'rarity-starter';if(r==='普通')return'rarity-common';
  if(r==='罕见')return'rarity-uncommon';if(r==='稀有')return'rarity-rare';
  if(r==='古代'||r==='先古')return'rarity-ancient';if(r==='Boss')return'rarity-boss';
  return'rarity-common';
}
function renderRelics(){
  const q=document.getElementById('search').value.toLowerCase();
  let list=allRelics;
  if(q)list=list.filter(r=>r.name.toLowerCase().includes(q)||r.name_en.toLowerCase().includes(q)||r.effect.toLowerCase().includes(q));
  const groups={};
  list.forEach(r=>{if(!groups[r.rarity])groups[r.rarity]=[];groups[r.rarity].push(r);});
  let html='<div class="relic-section-group">';
  rarityOrder.forEach(r=>{
    if(groups[r]&&groups[r].length){
      html+='<div class="relic-group-title">'+r+' <span class="count">('+groups[r].length+')</span></div>';
      html+='<div class="relic-icon-grid">';
      groups[r].forEach(rel=>{
        html+='<div class="relic-icon '+rarityClass(r)+'" onclick="showDetail(''+rel.id+'')">'+
          (rel.image_url?'<img src="'+rel.image_url+'" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">':'')+
          '<div style="display:none;width:48px;height:48px;align-items:center;justify-content:center;font-size:28px;margin:0 auto 4px;">🏺</div>'+
          '<div class="name">'+rel.name+'</div>'+
          '<div class="tooltip"><div class="t-name">'+rel.name+'</div><div class="t-effect">'+rel.effect+'</div></div>'+
          '</div>';
      });
      html+='</div>';
    }
  });
  Object.entries(groups).forEach(([r,items])=>{
    if(!rarityOrder.includes(r)){
      html+='<div class="relic-group-title">'+r+' <span class="count">('+items.length+')</span></div>';
      html+='<div class="relic-icon-grid">';
      items.forEach(rel=>{
        html+='<div class="relic-icon '+rarityClass(r)+'" onclick="showDetail(''+rel.id+'')">'+
          (rel.image_url?'<img src="'+rel.image_url+'" onerror="this.style.display='none'">':'')+
          '<div class="name">'+rel.name+'</div>'+
          '<div class="tooltip"><div class="t-name">'+rel.name+'</div><div class="t-effect">'+rel.effect+'</div></div></div>';
      });
      html+='</div>';
    }
  });
  html+='</div>';
  if(!list.length)html='<div class="empty">未找到遗物</div>';
  document.getElementById('relicContent').innerHTML=html;
}
function showDetail(id){
  const r=allRelics.find(x=>x.id===id);if(!r)return;
  document.getElementById('modal-content').innerHTML=
    '<div style="display:flex;gap:20px;align-items:center;margin-bottom:16px;">'+
    (r.image_url?'<img src="'+r.image_url+'" style="width:64px;height:64px;object-fit:contain;filter:drop-shadow(0 4px 8px rgba(0,0,0,.6));">':'')+
    '<div><h2 style="margin:0;">'+r.name+'</h2><div style="color:var(--text-gray);font-size:13px;">'+r.name_en+' · '+r.rarity+' · '+(r.pool==='silent'?'静默猎手专属':'共享')+'</div></div></div>'+
    '<div class="form-group"><label>效果</label><div style="color:var(--text-cream);line-height:1.7;">'+r.effect+'</div></div>'+
    (r.description?'<div class="form-group"><label>说明</label><div style="color:var(--text-cream);line-height:1.7;">'+r.description+'</div></div>':'')+
    (r.synergy?'<div class="form-group"><label>流派适配</label><div style="color:var(--green-light);line-height:1.7;">'+r.synergy+'</div></div>':'');
  document.getElementById('modal').classList.add('show');
}
function closeModal(){document.getElementById('modal').classList.remove('show');}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});
</script>
</body></html>"""

REPLAY_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/game-theme.css">
<title>对局复盘 - STS2决策器</title>
<style>
body{font-family:'Kreon','Georgia',serif;}
.replay-container{max-width:1100px;margin:0 auto;padding:20px;}
.info-bar{display:flex;align-items:center;gap:20px;padding:16px 20px;background:linear-gradient(135deg,#2a2018,#1a120c);border:2px solid #4a3a25;border-radius:8px;margin-bottom:20px;flex-wrap:wrap;}
.info-bar .char-icon{width:50px;height:50px;background:linear-gradient(135deg,#2a4a2a,#1a3a1a);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:28px;border:2px solid var(--silent);}
.info-bar .stat{display:flex;align-items:center;gap:6px;font-size:17px;}
.info-bar .stat .icon{font-size:20px;}
.info-bar .stat.hp{color:var(--red-light);}
.info-bar .stat.gold{color:var(--gold);}
.info-bar .stat.floor{color:var(--blue-light);}
.info-bar .right{margin-left:auto;text-align:right;font-size:13px;color:var(--text-gray);}
.section{background:linear-gradient(135deg,rgba(42,32,24,.6),rgba(26,18,12,.6));border:1px solid #4a3a25;border-radius:8px;padding:18px;margin-bottom:18px;}
.section-title{font-size:18px;color:var(--gold);margin-bottom:12px;font-family:'Cinzel',serif;}
.section-title .count{color:var(--text-gray);font-size:14px;margin-left:8px;font-family:'Kreon',serif;}
.relic-row{display:flex;flex-wrap:wrap;gap:8px;}
.relic-icon{width:52px;height:52px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:26px;background:rgba(255,255,255,.03);border:2px solid #5a4a35;position:relative;cursor:pointer;transition:transform .15s;}
.relic-icon:hover{transform:scale(1.1);border-color:var(--gold);}
.relic-icon .tooltip{position:absolute;bottom:100%;left:50%;transform:translateX(-50%);background:#1a120c;border:1px solid var(--gold-dark);padding:8px 12px;border-radius:4px;font-size:12px;white-space:normal;width:200px;display:none;z-index:10;color:var(--text-cream);}
.relic-icon:hover .tooltip{display:block;}
.card-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;}
.card-entry{background:linear-gradient(135deg,#2a2018,#1a120c);border:2px solid #4a3a25;border-radius:6px;padding:10px;display:flex;align-items:center;gap:8px;cursor:pointer;transition:all .15s;}
.card-entry:hover{border-color:var(--gold);transform:translateY(-2px);}
.card-entry .card-icon{width:32px;height:40px;background:rgba(255,255,255,.05);border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;}
.card-entry .card-info{flex:1;min-width:0;}
.card-entry .card-name{font-size:13px;color:var(--text-cream);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.card-entry .card-count{font-size:11px;color:var(--text-gray);}
.card-entry.rare{border-color:var(--gold-dark);}
.card-entry.uncommon{border-color:var(--green);}
.card-entry.curse{border-color:var(--purple);}
.analysis-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:16px;}
.analysis-item{background:rgba(201,162,39,.05);padding:14px;border-radius:6px;text-align:center;border:1px solid #4a3a25;}
.analysis-item .val{font-size:26px;font-weight:700;color:var(--gold);font-family:'Cinzel',serif;}
.analysis-item .lbl{font-size:12px;color:var(--text-gray);margin-top:4px;}
.suggestion{background:rgba(201,162,39,.08);border-left:3px solid var(--gold);padding:10px 14px;margin-bottom:8px;border-radius:0 4px 4px 0;}
.suggestion.warning{background:rgba(184,64,64,.08);border-left-color:var(--red);}
.suggestion.info{background:rgba(74,122,184,.08);border-left-color:var(--blue);}
.suggestion .title{font-weight:700;color:var(--gold);margin-bottom:4px;font-size:14px;}
.suggestion.warning .title{color:var(--red-light);}
.suggestion.info .title{color:var(--blue-light);}
.suggestion .content{font-size:13px;color:var(--text-cream);line-height:1.5;}
.loading{text-align:center;padding:60px;color:var(--text-dim);font-size:16px;}
</style></head>
<body>
<div class="game-nav"><div class="nav-inner">
  <a href="/" class="nav-brand">⚔️ STS2决策器</a>
  <a href="/live">当前对局</a><a href="/history" class="active">历史对局</a>
  <a href="/monsters">怪物图鉴</a><a href="/cards">卡牌图鉴</a>
  <a href="/relics">遗物图鉴</a><a href="/guide">使用指南</a><a href="/download">下载</a>
</div></div>
<div class="page-header"><h1>📜 对局复盘</h1><p>战略分析 · 卡组回顾 · 改进建议</p></div>
<div class="replay-container" id="content"><div class="loading">加载中...</div></div>
<script>
const runId="{{ run_id }}";
const relicEmoji={"风的女儿":"🌪️","水银沙漏":"⏳","投斧":"🪓","船夹板":"🛡️","金纸":"📜","永冻冰晶":"❄️","钨合金棍":"🔧","蛇之戒指":"💍","红面具":"🎭","节日拉炮":"🎉","巨大扭蛋":"🥚","空鸟笼":"🐦"};
function getRelicEmoji(name){return relicEmoji[name]||"📦";}
function getCardRarity(name){if(name.includes("打击")||name.includes("防御"))return"basic";if(name.includes("诅咒")||name.includes("进阶之灾")||name.includes("笨拙")||name.includes("睡眠不佳"))return"curse";if(name.includes("+"))return"rare";return"uncommon";}
fetch('/api/history/'+runId).then(r=>r.json()).then(run=>{
  if(run.error){document.getElementById('content').innerHTML='<p style="color:#ff6464">'+run.error+'</p>';return;}
  const ascension=run.ascension||0,hp=run.current_hp||0,maxHp=run.max_hp||70,gold=run.gold||0,deck=run.deck||[],relics=run.relics||[],maxFloor=run.max_floor||0;
  let html='';
  html+='<div class="info-bar"><div class="char-icon">🐍</div><div class="stat hp"><span class="icon">❤️</span>'+hp+'/'+maxHp+'</div><div class="stat gold"><span class="icon">🪙</span>'+gold+'</div><div class="stat"><span class="icon">🃏</span>'+deck.length+'</div><div class="stat floor"><span class="icon">🏔️</span>'+maxFloor+'</div><div class="stat"><span class="icon">⭐</span>进阶'+ascension+'</div><div class="right"><div>'+(run.date||'')+'</div><div>静默猎手 · '+(run.result||'未知')+'</div></div></div>';
  html+='<div class="section"><div class="section-title">📦 遗物 <span class="count">('+relics.length+')</span></div><div class="relic-row">';
  for(const r of relics){html+='<div class="relic-icon"><span>'+getRelicEmoji(r)+'</span><div class="tooltip">'+r+'</div></div>';}
  html+='</div></div>';
  const cardCounts={};for(const c of deck){cardCounts[c]=(cardCounts[c]||0)+1;}
  html+='<div class="section"><div class="section-title">🃏 卡牌 <span class="count">('+deck.length+')</span></div><div class="card-row">';
  for(const [name,count] of Object.entries(cardCounts)){
    html+='<div class="card-entry '+getCardRarity(name)+'"><div class="card-icon">🃏</div><div class="card-info"><div class="card-name">'+name+'</div>'+(count>1?'<div class="card-count">×'+count+'</div>':'')+'</div></div>';
  }
  html+='</div></div>';
  html+='<div class="section"><div class="section-title">📊 战略复盘分析</div><div id="analysisContent"><div class="loading">分析中...</div></div></div>';
  document.getElementById('content').innerHTML=html;
  fetch('/api/analysis/'+runId).then(r=>r.json()).then(d=>{
    const a=d.analysis;let ah='<div class="analysis-grid">';
    ah+='<div class="analysis-item"><div class="val">'+a.score+'</div><div class="lbl">综合评分</div></div>';
    ah+='<div class="analysis-item"><div class="val">'+a.archetype.primary+'</div><div class="lbl">主要流派</div></div>';
    ah+='<div class="analysis-item"><div class="val">'+(a.combat_analysis.win_rate||0).toFixed(0)+'%</div><div class="lbl">战斗胜率</div></div>';
    ah+='<div class="analysis-item"><div class="val">'+(a.combat_analysis.avg_hp_loss||0)+'</div><div class="lbl">场均失血</div></div>';
    ah+='</div>';
    if(a.suggestions&&a.suggestions.length){
      ah+='<div style="margin-top:16px"><div class="section-title" style="font-size:15px">💡 改进建议</div>';
      for(const s of a.suggestions){ah+='<div class="suggestion '+s.type+'"><div class="title">'+s.title+'</div><div class="content">'+s.content+'</div></div>';}
      ah+='</div>';
    }
    document.getElementById('analysisContent').innerHTML=ah;
  });
});
</script>
</body></html>"""


if __name__ == "__main__":
    print("=" * 50)
    print(f"STS2 Advisor Web App v8.0 ({MODE}模式)")
    print("=" * 50)
    if MODE == "cloud":
        print("云端模式：等待本地agent推送游戏状态")
        print("固定网址：部署后永久不变")
    else:
        print("本地模式：直连游戏API (127.0.0.1:8080)")
    print(f"访问地址: http://127.0.0.1:8766")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8766, debug=False)
