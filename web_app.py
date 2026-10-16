"""
STS2 Advisor Web Application - 公开网站版
功能：当前对局决策器、历史对局、复盘分析、怪物行为、牌序显示、LLM分析
"""
import json
import os
import time
import hashlib
import threading
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, Response, session

from advisor.client import AutoSpireClient
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

# 历史对局存储目录
HISTORY_DIR = os.path.join(os.path.expanduser("~"), ".sts2_advisor", "history")
os.makedirs(HISTORY_DIR, exist_ok=True)

# ============ 工具函数 ============
def state_hash(snap):
    """计算状态哈希，用于去重"""
    d = snap.get("data", snap)
    # 只哈希关键状态字段，忽略时间戳等
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
    """获取游戏状态，带缓存去重"""
    try:
        snap = client.get_state()
        h = state_hash(snap)
        now = time.time()
        if h == _state_cache["hash"] and now - _state_cache["time"] < 2:
            return _state_cache["data"], False  # 状态未变化
        _state_cache["hash"] = h
        _state_cache["data"] = snap
        _state_cache["time"] = now
        return snap, True
    except Exception as e:
        return {"error": str(e), "screen": "disconnected"}, False


def get_combat_recommendation(snap):
    """获取战斗推荐，带缓存"""
    h = state_hash(snap)
    now = time.time()
    if h == _recommendation_cache["hash"] and now - _recommendation_cache["time"] < 3:
        return _recommendation_cache["data"]

    d = snap.get("data", snap)
    combat_snap = d.get("combat", d)
    state = CombatState.from_snapshot(combat_snap)

    # 更新牌序记忆
    draw_memory.observe_new_cards(state.hand)

    root = mcts.search(state, iterations=500)
    ranked = mcts.ranked_actions(root)
    best = ranked[0][0] if ranked else None
    reason = explain_combat(state, best, ranked)

    # 构建已知牌序
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
            "kind": "play_card",
            "card": action.card.name,
            "cost": action.card.cost,
            "target": target,
            "label": f"打[{action.card.name}]→{target}"
        }
    return {"kind": action.kind, "label": action.kind}


def state_to_dict(state):
    return {
        "hp": state.player_hp,
        "max_hp": state.player_max_hp,
        "block": state.player_block,
        "energy": state.energy,
        "hand": [{"name": c.name, "cost": c.cost, "playable": c.playable} for c in state.hand],
        "enemies": [{
            "name": e.name, "hp": e.hp, "max_hp": e.max_hp,
            "block": e.block, "poison": e.poison,
            "intent_type": e.intent_type, "intent_damage": e.intent_total_damage,
            "is_aoe": e.is_aoe
        } for e in state.enemies],
        "turn": state.turn
    }


# ============ 页面路由 ============
INDEX_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>STS2 决策器 - 静默猎手AI教练</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: -apple-system, 'Segoe UI', sans-serif; background:#0f1923; color:#e0e6ed; min-height:100vh; }
.header { background:linear-gradient(135deg,#1a2a3a,#0f1923); padding:20px; border-bottom:2px solid #2d4a6a; }
.header .container { display:flex; justify-content:space-between; align-items:center; }
.header h1 { font-size:24px; color:#4fc3f7; }
.header p { color:#8899aa; margin-top:4px; font-size:14px; }
.user-menu { display:flex; align-items:center; gap:12px; }
.user-menu a { color:#4fc3f7; text-decoration:none; font-size:14px; padding:6px 12px; border:1px solid #4fc3f7; border-radius:6px; }
.user-menu .username { color:#66bb6a; font-size:14px; }
.container { max-width:900px; margin:0 auto; padding:20px; }
.card-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:16px; margin-top:20px; }
.card { background:#1a2a3a; border-radius:12px; padding:24px; border:1px solid #2d4a6a; cursor:pointer; transition:all .2s; text-decoration:none; color:inherit; display:block; }
.card:hover { border-color:#4fc3f7; transform:translateY(-2px); box-shadow:0 8px 24px rgba(79,195,247,.15); }
.card h3 { color:#4fc3f7; font-size:18px; margin-bottom:8px; }
.card p { color:#8899aa; font-size:14px; line-height:1.6; }
.card .icon { font-size:32px; margin-bottom:12px; }
.status { display:inline-block; padding:4px 12px; border-radius:20px; font-size:12px; margin-top:12px; }
.status.online { background:#1b5e20; color:#66bb6a; }
.status.offline { background:#b71c1c; color:#ef5350; }
.footer { text-align:center; padding:20px; color:#556677; font-size:12px; margin-top:40px; }
</style>
</head>
<body>
<div class="header">
  <div class="container">
    <div>
      <h1>STS2 决策器</h1>
      <p>杀戮尖塔2 · 静默猎手AI教练 · 实时决策 + 战略复盘</p>
    </div>
    <div class="user-menu" id="userMenu">
      <a href="/login">登录</a>
      <a href="/register">注册</a>
    </div>
  </div>
</div>
<div class="container">
  <div class="card-grid">
    <a class="card" href="/live">
      <div class="icon">⚔️</div>
      <h3>当前对局</h3>
      <p>实时战斗决策推荐、怪物行为显示、牌序记忆、路线/奖励/商店指导</p>
      <span class="status" id="liveStatus">检测中...</span>
    </a>
    <a class="card" href="/history">
      <div class="icon">📊</div>
      <h3>历史对局</h3>
      <p>查看所有对局记录，筛选进阶、角色、结果，追踪你的进步</p>
    </a>
    <a class="card" href="/monsters">
      <div class="icon">👹</div>
      <h3>怪物图鉴</h3>
      <p>所有怪物的固定行为模式、伤害数值、应对策略</p>
    </a>
    <a class="card" href="/cards">
      <div class="icon">🃏</div>
      <h3>卡牌图鉴</h3>
      <p>静默猎手全卡牌效果、升级对比、流派搭配推荐</p>
    </a>
  </div>
</div>
<div class="footer">STS2 Advisor v6.0 · 基于MCTS+评估器 · 数据来自STS2 AI Agent mod</div>
<script>
fetch('/api/auth/me').then(r=>r.json()).then(d=>{
  const menu=document.getElementById('userMenu');
  if(d.logged_in){
    menu.innerHTML='<span class="username">'+d.user.username+'</span><a href="#" onclick="logout()">登出</a>';
  }
});
function logout(){
  fetch('/api/auth/logout',{method:'POST'}).then(()=>location.href='/');
}
fetch('/api/status').then(r=>r.json()).then(d=>{
  const el=document.getElementById('liveStatus');
  if(d.connected){el.textContent='游戏已连接';el.className='status online';}
  else{el.textContent='游戏未连接';el.className='status offline';}
});
</script>
</body>
</html>"""


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
            return jsonify({"connected": True, "screen": live.get("screen", "unknown"),
                            "mode": "cloud", "age": int(live["age_seconds"])})
        return jsonify({"connected": False, "screen": "waiting_for_agent", "mode": "cloud"})
    snap, changed = get_game_state()
    return jsonify({"connected": "error" not in snap, "screen": snap.get("screen", "unknown"), "mode": "local"})


@app.route("/api/state")
def api_state():
    user_id = _get_user_id()
    if MODE == "cloud":
        live = cloud_db.get_live_state(user_id=user_id)
        if live:
            return jsonify({"state": live.get("state", {}), "changed": True, "mode": "cloud"})
        return jsonify({"state": {"screen": "waiting"}, "changed": False, "mode": "cloud"})
    snap, changed = get_game_state()
    return jsonify({"state": snap, "changed": changed, "mode": "local"})


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
    """获取历史对局列表（云端数据库）"""
    user_id = _get_user_id()
    runs = cloud_db.list_runs(limit=50, user_id=user_id)
    return jsonify({"runs": runs})


@app.route("/api/history/<run_id>")
def api_history_detail(run_id):
    """获取单局复盘数据（云端数据库）"""
    user_id = _get_user_id()
    data = cloud_db.get_run(run_id, user_id=user_id)
    if not data:
        return jsonify({"error": "对局不存在"}), 404
    return jsonify(data)


@app.route("/api/analysis/<run_id>")
def api_analysis(run_id):
    """获取对局战略复盘分析"""
    user_id = _get_user_id()
    data = cloud_db.get_run(run_id, user_id=user_id)
    if not data:
        return jsonify({"error": "对局不存在"}), 404
    analysis = analyze_run(data)
    narrative = generate_replay_narrative(data)
    return jsonify({"analysis": analysis, "narrative": narrative})


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


def _get_user_id():
    """从session或请求头获取user_id"""
    user = auth.current_user()
    if user:
        return user["user_id"]
    # 支持agent用token认证
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        user = auth.verify_token(token)
        if user:
            return user["user_id"]
    return 0  # 匿名用户


# ============ Agent推送API（本地agent推送到云端） ============
@app.route("/api/agent/state", methods=["POST"])
def api_agent_state():
    """本地agent推送游戏状态和推荐结果"""
    user_id = _get_user_id()
    data = request.json or {}
    screen = data.get("screen", "unknown")
    phase = data.get("phase", "unknown")
    state = data.get("state", {})
    recommendation = data.get("recommendation", {})
    cloud_db.update_live_state(screen, phase, state, recommendation, user_id=user_id)
    return jsonify({"ok": True, "received": True, "user_id": user_id})


@app.route("/api/agent/run", methods=["POST"])
def api_agent_run():
    """本地agent推送对局数据（开始/更新/结束）"""
    user_id = _get_user_id()
    data = request.json or {}
    run_id = cloud_db.save_run(data, user_id=user_id)
    return jsonify({"ok": True, "run_id": run_id, "user_id": user_id})


@app.route("/api/agent/decision", methods=["POST"])
def api_agent_decision():
    """本地agent推送决策记录"""
    user_id = _get_user_id()
    data = request.json or {}
    cloud_db.save_decision(
        data.get("run_id", ""),
        data.get("floor", 0),
        data.get("phase", ""),
        data.get("action", ""),
        data.get("reason", ""),
        data.get("value", 0),
        user_id=user_id
    )
    return jsonify({"ok": True})


@app.route("/api/agent/optimization", methods=["POST"])
def api_agent_optimization():
    """本地agent推送自我优化记录"""
    user_id = _get_user_id()
    data = request.json or {}
    cloud_db.save_optimization(
        data.get("type", ""),
        data.get("description", ""),
        data.get("data", {}),
        user_id=user_id
    )
    return jsonify({"ok": True})


@app.route("/api/optimizations")
def api_optimizations():
    """查看自我优化记录"""
    opts = cloud_db.list_optimizations(limit=20)
    return jsonify({"optimizations": opts})


@app.route("/api/monsters")
def api_monsters():
    """获取怪物行为数据库"""
    from advisor.monsters import MONSTER_DB
    return jsonify({"monsters": MONSTER_DB})


@app.route("/api/cards")
def api_cards():
    """获取卡牌数据库"""
    from advisor.cards import CARD_EFFECTS
    return jsonify({"cards": {k: v for k, v in CARD_EFFECTS.items()}})


@app.route("/api/llm_analyze", methods=["POST"])
def api_llm_analyze():
    """LLM分析接口"""
    data = request.json or {}
    llm = get_llm()
    analysis_type = data.get("type", "combat")

    if analysis_type == "combat":
        result = llm.analyze_combat(data.get("state", {}), data.get("recommendation", {}))
    elif analysis_type == "reward":
        result = llm.analyze_reward(
            data.get("deck", []), data.get("options", []),
            data.get("relics", []), data.get("hp", 70), data.get("gold", 0)
        )
    elif analysis_type == "run":
        run_data = RunRecorder.load_run(data.get("run_id", ""))
        if run_data:
            result = llm.analyze_run(run_data)
        else:
            result = "对局不存在"
    else:
        result = "不支持的分析类型"

    return jsonify({
        "analysis": result,
        "llm_enabled": llm.enabled,
        "model": llm.model if llm.enabled else "规则分析（未配置API Key）"
    })


# ============ 页面模板 ============
LIVE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>当前对局 - STS2决策器</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,sans-serif; background:#0f1923; color:#e0e6ed; min-height:100vh; }
.topbar { background:#1a2a3a; padding:12px 20px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #2d4a6a; position:sticky; top:0; z-index:100; }
.topbar a { color:#4fc3f7; text-decoration:none; font-size:14px; }
.topbar .status { font-size:12px; padding:4px 10px; border-radius:12px; }
.online { background:#1b5e20; color:#66bb6a; }
.offline { background:#b71c1c; color:#ef5350; }
.container { max-width:800px; margin:0 auto; padding:16px; }
.panel { background:#1a2a3a; border-radius:10px; padding:16px; margin-bottom:16px; border:1px solid #2d4a6a; }
.panel h2 { font-size:16px; color:#4fc3f7; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center; }
.rec-card { background:linear-gradient(135deg,#1e3a5f,#1a2a3a); border:2px solid #4fc3f7; border-radius:10px; padding:16px; margin-bottom:12px; }
.rec-card .action { font-size:20px; font-weight:bold; color:#fff; }
.rec-card .reason { color:#88ccff; font-size:14px; margin-top:8px; line-height:1.6; }
.rec-card .winrate { color:#66bb6a; font-size:14px; margin-top:4px; }
.stat-row { display:flex; gap:16px; flex-wrap:wrap; margin-bottom:12px; }
.stat { flex:1; min-width:80px; text-align:center; }
.stat .val { font-size:24px; font-weight:bold; color:#fff; }
.stat .lbl { font-size:12px; color:#8899aa; }
.enemy { background:#2a1a1a; border-radius:8px; padding:10px; margin-bottom:8px; border-left:3px solid #ef5350; }
.enemy .name { font-weight:bold; color:#ef9a9a; }
.enemy .hp-bar { height:6px; background:#333; border-radius:3px; margin:6px 0; overflow:hidden; }
.enemy .hp-fill { height:100%; background:linear-gradient(90deg,#ef5350,#ff8a65); transition:width .3s; }
.enemy .intent { font-size:13px; color:#ffcc80; margin-top:4px; }
.hand { display:flex; flex-wrap:wrap; gap:6px; }
.card-item { background:#2a3a4a; border-radius:6px; padding:8px 10px; font-size:13px; border:1px solid #3d5a7a; }
.card-item.playable { border-color:#66bb6a; }
.card-item.unplayable { opacity:.5; border-color:#555; }
.card-item .cost { display:inline-block; width:20px; height:20px; line-height:20px; text-align:center; background:#4fc3f7; border-radius:50%; font-size:11px; margin-right:6px; color:#000; font-weight:bold; }
.draw-order { font-size:13px; color:#aaa; line-height:1.8; }
.draw-order .known { color:#66bb6a; }
.alternatives { margin-top:8px; }
.alt-item { padding:8px; background:#15202b; border-radius:6px; margin-bottom:4px; font-size:13px; display:flex; justify-content:space-between; }
.alt-item .val { color:#8899aa; }
</style>
</head>
<body>
<div class="topbar">
  <a href="/">← 返回首页</a>
  <span>当前对局</span>
  <span class="status offline" id="connStatus">未连接</span>
</div>
<div class="container">
  <div class="panel" id="recPanel">
    <h2>🎯 推荐动作</h2>
    <div id="recContent"><p style="color:#8899aa">等待游戏数据...</p></div>
  </div>
  <div class="panel">
    <h2>📊 状态</h2>
    <div class="stat-row" id="stats"></div>
  </div>
  <div class="panel">
    <h2>👹 敌人</h2>
    <div id="enemies"></div>
  </div>
  <div class="panel">
    <h2>🃏 手牌</h2>
    <div class="hand" id="hand"></div>
  </div>
  <div class="panel">
    <h2>📜 牌序记忆 <span style="font-size:12px;color:#8899aa;font-weight:normal">SL后可查看抽牌顺序</span></h2>
    <div class="draw-order" id="drawOrder">暂无数据</div>
  </div>
  <div class="panel">
    <h2>💡 备选方案</h2>
    <div class="alternatives" id="alts"></div>
  </div>
</div>
<script>
let lastHash='';
async function update(){
  try{
    const r=await fetch('/api/recommend');
    const d=await r.json();
    document.getElementById('connStatus').textContent='已连接';
    document.getElementById('connStatus').className='status online';
    if(d.error){document.getElementById('recContent').innerHTML='<p style="color:#ef5350">'+d.error+'</p>';return;}
    // 战斗阶段
    if(d.phase==='combat'&&d.state){
      const s=d.state;
      // 状态
      document.getElementById('stats').innerHTML=`
        <div class="stat"><div class="val" style="color:#ef5350">${s.hp}/${s.max_hp}</div><div class="lbl">生命</div></div>
        <div class="stat"><div class="val" style="color:#4fc3f7">${s.block}</div><div class="lbl">格挡</div></div>
        <div class="stat"><div class="val" style="color:#ffcc80">${s.energy}</div><div class="lbl">能量</div></div>
        <div class="stat"><div class="val">T${s.turn}</div><div class="lbl">回合</div></div>`;
      // 推荐
      if(d.best){
        document.getElementById('recContent').innerHTML=`
          <div class="rec-card">
            <div class="action">${d.best.label}</div>
            <div class="winrate">${d.reason}</div>
          </div>`;
      }
      // 敌人
      document.getElementById('enemies').innerHTML=s.enemies.map(e=>`
        <div class="enemy">
          <div class="name">${e.name} ${e.poison>0?'<span style="color:#66bb6a">毒'+e.poison+'</span>':''}</div>
          <div class="hp-bar"><div class="hp-fill" style="width:${(e.hp/e.max_hp*100).toFixed(0)}%"></div></div>
          <div style="font-size:12px;color:#aaa">${e.hp}/${e.max_hp} HP ${e.block>0?'🛡'+e.block:''}</div>
          <div class="intent">意图: ${e.intent_type||'?'} ${e.intent_damage>0?'伤害'+e.intent_damage:''} ${e.is_aoe?'(AOE)':''}</div>
        </div>`).join('');
      // 手牌
      document.getElementById('hand').innerHTML=s.hand.map(c=>`
        <div class="card-item ${c.playable?'playable':'unplayable'}">
          <span class="cost">${c.cost}</span>${c.name}
        </div>`).join('');
      // 备选
      document.getElementById('alts').innerHTML=(d.ranked||[]).slice(1).map(a=>`
        <div class="alt-item"><span>${a.action.label}</span><span class="val">胜率${(a.value*100).toFixed(0)}% (${a.visits}次)</span></div>`).join('')||'<span style="color:#666">无</span>';
      // 牌序
      if(d.draw_order&&d.draw_order.length){
        document.getElementById('drawOrder').innerHTML='已知牌序: '+d.draw_order.map((c,i)=>`<span class="known">${i+1}.${c}</span>`).join(' → ');
      }
    } else if(d.phase==='map'){
      document.getElementById('recContent').innerHTML='<div class="rec-card"><div class="action">路线推荐</div><div class="winrate">'+JSON.stringify(d.recommendation)+'</div></div>';
    } else if(d.phase==='reward'){
      document.getElementById('recContent').innerHTML='<div class="rec-card"><div class="action">奖励选择</div><div class="winrate">'+JSON.stringify(d.recommendation)+'</div></div>';
    } else if(d.phase==='shop'){
      document.getElementById('recContent').innerHTML='<div class="rec-card"><div class="action">商店购买</div><div class="winrate">'+JSON.stringify(d.recommendation)+'</div></div>';
    }
  }catch(e){
    document.getElementById('connStatus').textContent='未连接';
    document.getElementById('connStatus').className='status offline';
    document.getElementById('recContent').innerHTML='<p style="color:#8899aa">等待游戏启动...</p>';
  }
}
setInterval(update,1500);
update();
</script>
</body>
</html>"""

HISTORY_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>历史对局 - STS2决策器</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,sans-serif; background:#0f1923; color:#e0e6ed; }
.topbar { background:#1a2a3a; padding:12px 20px; border-bottom:1px solid #2d4a6a; }
.topbar a { color:#4fc3f7; text-decoration:none; }
.container { max-width:800px; margin:0 auto; padding:16px; }
.run-item { background:#1a2a3a; border-radius:10px; padding:16px; margin-bottom:12px; border:1px solid #2d4a6a; cursor:pointer; transition:all .2s; display:flex; justify-content:space-between; align-items:center; }
.run-item:hover { border-color:#4fc3f7; }
.run-item .info { flex:1; }
.run-item .date { color:#8899aa; font-size:12px; }
.run-item .meta { margin-top:6px; font-size:14px; }
.run-item .meta span { margin-right:16px; }
.run-item .result { padding:4px 12px; border-radius:12px; font-size:12px; }
.win { background:#1b5e20; color:#66bb6a; }
.lose { background:#b71c1c; color:#ef5350; }
.empty { text-align:center; padding:60px; color:#556677; }
</style>
</head>
<body>
<div class="topbar"><a href="/">← 返回首页</a> | 历史对局</div>
<div class="container">
  <div id="runs"><div class="empty">加载中...</div></div>
</div>
<script>
fetch('/api/history').then(r=>r.json()).then(d=>{
  const el=document.getElementById('runs');
  if(!d.runs.length){el.innerHTML='<div class="empty">暂无对局记录<br><small>完成一局后会自动保存</small></div>';return;}
  el.innerHTML=d.runs.map(r=>`
    <div class="run-item" onclick="location.href='/replay/${r.id}'">
      <div class="info">
        <div class="date">${r.date}</div>
        <div class="meta">
          <span>进阶${r.ascension}</span>
          <span>${r.character}</span>
          <span>楼层${r.floor}</span>
          <span>${r.deck_size}张牌</span>
          <span>${r.relics}遗物</span>
        </div>
      </div>
      <span class="result ${r.result==='胜利'?'win':'lose'}">${r.result}</span>
    </div>`).join('');
});
</script>
</body>
</html>"""

MONSTERS_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>怪物图鉴 - STS2决策器</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,sans-serif; background:#0f1923; color:#e0e6ed; }
.topbar { background:#1a2a3a; padding:12px 20px; border-bottom:1px solid #2d4a6a; }
.topbar a { color:#4fc3f7; text-decoration:none; }
.container { max-width:800px; margin:0 auto; padding:16px; }
.monster { background:#1a2a3a; border-radius:10px; padding:16px; margin-bottom:12px; border:1px solid #2d4a6a; }
.monster h3 { color:#ef9a9a; margin-bottom:8px; }
.monster .hp { color:#8899aa; font-size:14px; margin-bottom:8px; }
.monster .moves { font-size:13px; line-height:1.8; }
.monster .move { padding:4px 0; border-bottom:1px solid #2d4a6a; }
.monster .move:last-child { border-bottom:none; }
.monster .move .name { color:#ffcc80; font-weight:bold; }
.empty { text-align:center; padding:60px; color:#556677; }
</style>
</head>
<body>
<div class="topbar"><a href="/">← 返回首页</a> | 怪物图鉴</div>
<div class="container"><div id="list"><div class="empty">加载中...</div></div></div>
<script>
fetch('/api/monsters').then(r=>r.json()).then(d=>{
  const el=document.getElementById('list');
  if(!d.monsters||!d.monsters.length){el.innerHTML='<div class="empty">怪物数据库建设中...</div>';return;}
  el.innerHTML=d.monsters.map(m=>`
    <div class="monster">
      <h3>${m.name}</h3>
      <div class="hp">HP: ${m.hp_min}-${m.hp_max} | 出现于: ${m.act||'?'}</div>
      <div class="moves">${(m.moves||[]).map(mv=>`
        <div class="move"><span class="name">${mv.name}</span>: ${mv.desc} ${mv.damage?`(伤害${mv.damage}${mv.hits>1?'×'+mv.hits:''})`:''}</div>`).join('')}</div>
    </div>`).join('');
});
</script>
</body>
</html>"""

CARDS_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>卡牌图鉴 - STS2决策器</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,sans-serif; background:#0f1923; color:#e0e6ed; }
.topbar { background:#1a2a3a; padding:12px 20px; border-bottom:1px solid #2d4a6a; }
.topbar a { color:#4fc3f7; text-decoration:none; }
.container { max-width:900px; margin:0 auto; padding:16px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:10px; }
.card { background:#1a2a3a; border-radius:8px; padding:12px; border:1px solid #2d4a6a; font-size:13px; }
.card .name { color:#4fc3f7; font-weight:bold; margin-bottom:4px; }
.card .cost { display:inline-block; width:18px; height:18px; line-height:18px; text-align:center; background:#4fc3f7; border-radius:50%; font-size:11px; color:#000; font-weight:bold; margin-right:6px; }
.card .effect { color:#aaa; font-size:12px; line-height:1.5; }
</style>
</head>
<body>
<div class="topbar"><a href="/">← 返回首页</a> | 卡牌图鉴</div>
<div class="container"><div class="grid" id="grid"></div></div>
<script>
fetch('/api/cards').then(r=>r.json()).then(d=>{
  const cards=Object.entries(d.cards).sort((a,b)=>a[0].localeCompare(b[0]));
  document.getElementById('grid').innerHTML=cards.map(([name,e])=>`
    <div class="card">
      <div class="name"><span class="cost">${e.cost??'?'}</span>${name}</div>
      <div class="effect">${e.attack?`攻击${e.attack}${e.hits>1?'×'+e.hits:''} `:''}${e.block?`格挡${e.block} `:''}${e.poison?`毒${e.poison} `:''}${e.draw?`抽${e.draw} `:''}${e.weak?`虚弱${e.weak} `:''}${e.vulnerable?`易伤${e.vulnerable} `:''}</div>
    </div>`).join('');
});
</script>
</body>
</html>"""

LOGIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>登录 - STS2决策器</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,sans-serif; background:#0f1923; color:#e0e6ed; min-height:100vh; display:flex; align-items:center; justify-content:center; }
.login-box { background:#1a2a3a; padding:40px; border-radius:12px; border:1px solid #2d4a6a; width:360px; }
.login-box h1 { color:#4fc3f7; font-size:24px; margin-bottom:8px; text-align:center; }
.login-box p { color:#8899aa; font-size:14px; text-align:center; margin-bottom:24px; }
.form-group { margin-bottom:16px; }
.form-group label { display:block; font-size:14px; color:#8899aa; margin-bottom:6px; }
.form-group input { width:100%; padding:10px 12px; background:#0f1923; border:1px solid #2d4a6a; border-radius:6px; color:#e0e6ed; font-size:14px; }
.form-group input:focus { outline:none; border-color:#4fc3f7; }
.btn { width:100%; padding:12px; background:#4fc3f7; color:#0f1923; border:none; border-radius:6px; font-size:16px; font-weight:bold; cursor:pointer; margin-top:8px; }
.btn:hover { background:#81d4fa; }
.error { color:#ef5350; font-size:13px; margin-top:8px; text-align:center; min-height:18px; }
.links { margin-top:16px; text-align:center; font-size:14px; }
.links a { color:#4fc3f7; text-decoration:none; }
.steam-btn { width:100%; padding:10px; background:#1b2838; color:#66c0f4; border:1px solid #66c0f4; border-radius:6px; font-size:14px; cursor:pointer; margin-top:12px; }
</style>
</head>
<body>
<div class="login-box">
  <h1>STS2 决策器</h1>
  <p>登录以同步你的对局历史</p>
  <div class="form-group">
    <label>用户名</label>
    <input type="text" id="username" placeholder="输入用户名">
  </div>
  <div class="form-group">
    <label>密码</label>
    <input type="password" id="password" placeholder="输入密码">
  </div>
  <button class="btn" onclick="doLogin()">登录</button>
  <div class="error" id="error"></div>
  <button class="steam-btn" onclick="alert('Steam登录开发中')">用Steam账号登录</button>
  <div class="links">
    还没有账号？<a href="/register">立即注册</a>
  </div>
</div>
<script>
function doLogin(){
  const u=document.getElementById('username').value;
  const p=document.getElementById('password').value;
  fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})})
  .then(r=>r.json()).then(d=>{
    if(d.ok){location.href='/';}
    else{document.getElementById('error').textContent=d.error;}
  });
}
document.getElementById('password').addEventListener('keypress',e=>{if(e.key==='Enter')doLogin();});
</script>
</body>
</html>"""

REGISTER_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>注册 - STS2决策器</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,sans-serif; background:#0f1923; color:#e0e6ed; min-height:100vh; display:flex; align-items:center; justify-content:center; }
.login-box { background:#1a2a3a; padding:40px; border-radius:12px; border:1px solid #2d4a6a; width:360px; }
.login-box h1 { color:#4fc3f7; font-size:24px; margin-bottom:8px; text-align:center; }
.login-box p { color:#8899aa; font-size:14px; text-align:center; margin-bottom:24px; }
.form-group { margin-bottom:16px; }
.form-group label { display:block; font-size:14px; color:#8899aa; margin-bottom:6px; }
.form-group input { width:100%; padding:10px 12px; background:#0f1923; border:1px solid #2d4a6a; border-radius:6px; color:#e0e6ed; font-size:14px; }
.form-group input:focus { outline:none; border-color:#4fc3f7; }
.btn { width:100%; padding:12px; background:#4fc3f7; color:#0f1923; border:none; border-radius:6px; font-size:16px; font-weight:bold; cursor:pointer; margin-top:8px; }
.btn:hover { background:#81d4fa; }
.error { color:#ef5350; font-size:13px; margin-top:8px; text-align:center; min-height:18px; }
.links { margin-top:16px; text-align:center; font-size:14px; }
.links a { color:#4fc3f7; text-decoration:none; }
</style>
</head>
<body>
<div class="login-box">
  <h1>注册账号</h1>
  <p>创建账号以同步对局历史</p>
  <div class="form-group">
    <label>用户名（至少3字符）</label>
    <input type="text" id="username" placeholder="输入用户名">
  </div>
  <div class="form-group">
    <label>密码（至少6字符）</label>
    <input type="password" id="password" placeholder="输入密码">
  </div>
  <div class="form-group">
    <label>确认密码</label>
    <input type="password" id="password2" placeholder="再次输入密码">
  </div>
  <button class="btn" onclick="doRegister()">注册</button>
  <div class="error" id="error"></div>
  <div class="links">
    已有账号？<a href="/login">去登录</a>
  </div>
</div>
<script>
function doRegister(){
  const u=document.getElementById('username').value;
  const p=document.getElementById('password').value;
  const p2=document.getElementById('password2').value;
  if(p!==p2){document.getElementById('error').textContent='两次密码不一致';return;}
  fetch('/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})})
  .then(r=>r.json()).then(d=>{
    if(d.ok){location.href='/';}
    else{document.getElementById('error').textContent=d.error;}
  });
}
</script>
</body>
</html>"""

REPLAY_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>对局历史 - STS2决策器</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:'Georgia', serif; background:linear-gradient(180deg,#1a0f0a,#0d0705); color:#e8dcc8; min-height:100vh; }
.topbar { background:rgba(0,0,0,.6); padding:10px 20px; border-bottom:2px solid #8b6914; }
.topbar a { color:#d4a843; text-decoration:none; font-size:14px; }
.container { max-width:1100px; margin:0 auto; padding:20px; }

/* 顶部信息栏 */
.info-bar { display:flex; align-items:center; gap:20px; padding:16px; background:rgba(0,0,0,.4); border-radius:8px; margin-bottom:20px; flex-wrap:wrap; }
.info-bar .char-icon { width:50px; height:50px; background:linear-gradient(135deg,#2d5a27,#1a3a18); border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:28px; border:2px solid #8b6914; }
.info-bar .stat { display:flex; align-items:center; gap:6px; font-size:18px; }
.info-bar .stat .icon { font-size:22px; }
.info-bar .stat.hp { color:#ff6b6b; }
.info-bar .stat.gold { color:#ffd700; }
.info-bar .stat.floor { color:#87ceeb; }
.info-bar .right { margin-left:auto; text-align:right; font-size:13px; color:#a89880; }

/* 路线图 */
.map-section { background:rgba(0,0,0,.3); border-radius:8px; padding:16px; margin-bottom:20px; }
.map-row { display:flex; align-items:center; gap:8px; margin-bottom:10px; }
.map-row .act-name { width:60px; font-size:16px; color:#d4a843; font-weight:bold; }
.map-row .nodes { display:flex; gap:4px; flex-wrap:wrap; }
.map-node { width:32px; height:32px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-size:16px; background:rgba(255,255,255,.05); border:1px solid #444; }
.map-node.combat { background:#3a1a1a; border-color:#8b3a3a; }
.map-node.elite { background:#3a2a1a; border-color:#8b6914; }
.map-node.boss { background:#4a1a3a; border-color:#8b3a6a; }
.map-node.shop { background:#1a2a3a; border-color:#3a6a8b; }
.map-node.rest { background:#1a3a1a; border-color:#3a8b3a; }
.map-node.event { background:#2a1a3a; border-color:#6a3a8b; }
.map-node.treasure { background:#3a3a1a; border-color:#8b8b3a; }
.map-node.unknown { background:#222; border-color:#555; }

/* 遗物栏 */
.relic-section { background:rgba(0,0,0,.3); border-radius:8px; padding:16px; margin-bottom:20px; }
.section-title { font-size:18px; color:#d4a843; margin-bottom:12px; }
.section-title .count { color:#a89880; font-size:14px; margin-left:8px; }
.section-title .rarity { color:#888; font-size:13px; margin-left:12px; }
.relic-grid { display:flex; flex-wrap:wrap; gap:8px; }
.relic-item { width:48px; height:48px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:24px; background:rgba(255,255,255,.05); border:2px solid #555; position:relative; cursor:pointer; transition:transform .15s; }
.relic-item:hover { transform:scale(1.1); }
.relic-item.common { border-color:#888; }
.relic-item.uncommon { border-color:#4a9eff; }
.relic-item.rare { border-color:#ffd700; }
.relic-item.boss { border-color:#ff6bff; }
.relic-item .tooltip { position:absolute; bottom:100%; left:50%; transform:translateX(-50%); background:#222; padding:6px 10px; border-radius:4px; font-size:12px; white-space:nowrap; display:none; z-index:10; border:1px solid #555; }
.relic-item:hover .tooltip { display:block; }

/* 卡牌栏 */
.card-section { background:rgba(0,0,0,.3); border-radius:8px; padding:16px; margin-bottom:20px; }
.card-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:8px; }
.card-item { background:linear-gradient(135deg,#1a2a1a,#0d1a0d); border:2px solid #4a6a4a; border-radius:8px; padding:10px; display:flex; align-items:center; gap:8px; cursor:pointer; transition:all .15s; }
.card-item:hover { border-color:#6a9a6a; transform:translateY(-2px); }
.card-item .card-icon { width:32px; height:40px; background:rgba(255,255,255,.1); border-radius:4px; display:flex; align-items:center; justify-content:center; font-size:18px; flex-shrink:0; }
.card-item .card-info { flex:1; min-width:0; }
.card-item .card-name { font-size:13px; color:#e8dcc8; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.card-item .card-count { font-size:11px; color:#888; }
.card-item.rare { border-color:#ffd700; background:linear-gradient(135deg,#2a2a1a,#1a1a0d); }
.card-item.uncommon { border-color:#4a9eff; background:linear-gradient(135deg,#1a2a3a,#0d1a2a); }
.card-item.curse { border-color:#8b3a8b; background:linear-gradient(135deg,#2a1a2a,#1a0d1a); }
.card-item.basic { border-color:#666; background:linear-gradient(135deg,#222,#111); }

/* 分析面板 */
.analysis-section { background:rgba(0,0,0,.3); border-radius:8px; padding:16px; margin-bottom:20px; }
.analysis-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin-bottom:16px; }
.analysis-item { background:rgba(255,255,255,.03); padding:12px; border-radius:6px; text-align:center; }
.analysis-item .val { font-size:28px; font-weight:bold; color:#d4a843; }
.analysis-item .lbl { font-size:12px; color:#888; margin-top:4px; }
.suggestion { background:rgba(255,200,50,.1); border-left:3px solid #ffc832; padding:10px 14px; margin-bottom:8px; border-radius:0 6px 6px 0; }
.suggestion.warning { background:rgba(255,100,100,.1); border-left-color:#ff6464; }
.suggestion.info { background:rgba(100,150,255,.1); border-left-color:#6496ff; }
.suggestion .title { font-weight:bold; color:#ffc832; margin-bottom:4px; }
.suggestion.warning .title { color:#ff6464; }
.suggestion.info .title { color:#6496ff; }
.suggestion .content { font-size:13px; color:#ccc; line-height:1.5; }

.loading { text-align:center; padding:60px; color:#666; font-size:16px; }
</style>
</head>
<body>
<div class="topbar"><a href="/history">← 返回历史列表</a> | 对局历史记录</div>
<div class="container" id="content">
  <div class="loading">加载中...</div>
</div>
<script>
const runId="{{ run_id }}";

// 遗物emoji映射（占位符，提取真实图标后自动替换）
const relicEmoji = {
  "风的女儿":"🌪️","水银沙漏":"⏳","投斧":"🪓","船夹板":"🛡️","金纸":"📜",
  "永冻冰晶":"❄️","钨合金棍":"🔧","蛇之戒指":"💍","红面具":"🎭","节日拉炮":"🎉",
  "巨大扭蛋":"🥚","空鸟笼":"🐦"
};

// 节点类型映射
const nodeTypes = {
  "战斗":"combat","精英":"elite","Boss":"boss","商店":"shop",
  "休息":"rest","事件":"event","宝箱":"treasure","?":"unknown"
};

function getRelicEmoji(name){
  return relicEmoji[name] || "📦";
}

function getCardRarity(name){
  if(name.includes("打击")||name.includes("防御")) return "basic";
  if(name.includes("诅咒")||name.includes("进阶之灾")||name.includes("笨拙")||name.includes("睡眠不佳")) return "curse";
  if(name.includes("+")) return "rare";
  return "uncommon";
}

fetch('/api/history/'+runId).then(r=>r.json()).then(run=>{
  if(run.error){document.getElementById('content').innerHTML='<p style="color:#ff6464">'+run.error+'</p>';return;}

  // 顶部信息
  const ascension = run.ascension||0;
  const hp = run.current_hp||0;
  const maxHp = run.max_hp||70;
  const gold = run.gold||0;
  const deck = run.deck||[];
  const relics = run.relics||[];
  const maxFloor = run.max_floor||0;

  let html = '';

  // 信息栏
  html += '<div class="info-bar">';
  html += '<div class="char-icon">🐍</div>';
  html += '<div class="stat hp"><span class="icon">❤️</span>'+hp+'/'+maxHp+'</div>';
  html += '<div class="stat gold"><span class="icon">🪙</span>'+gold+'</div>';
  html += '<div class="stat"><span class="icon">🃏</span>'+deck.length+'</div>';
  html += '<div class="stat floor"><span class="icon">🏔️</span>'+maxFloor+'</div>';
  html += '<div class="stat"><span class="icon">⭐</span>进阶'+ascension+'</div>';
  html += '<div class="right">';
  html += '<div>'+(run.date||'')+'</div>';
  html += '<div>静默猎手 · '+ (run.result||'未知') +'</div>';
  html += '</div></div>';

  // 路线图（如果有数据）
  if(run.map_path){
    html += '<div class="map-section"><div class="section-title">🗺️ 路线图</div>';
    for(const act of run.map_path){
      html += '<div class="map-row"><div class="act-name">'+act.name+'</div><div class="nodes">';
      for(const node of act.nodes){
        const type = nodeTypes[node.type]||'unknown';
        html += '<div class="map-node '+type+'" title="'+node.type+'">'+(node.icon||'❓')+'</div>';
      }
      html += '</div></div>';
    }
    html += '</div>';
  }

  // 遗物栏
  html += '<div class="relic-section">';
  html += '<div class="section-title">📦 遗物 <span class="count">('+relics.length+')</span></div>';
  html += '<div class="relic-grid">';
  for(const r of relics){
    html += '<div class="relic-item common"><span>'+getRelicEmoji(r)+'</span><div class="tooltip">'+r+'</div></div>';
  }
  html += '</div></div>';

  // 卡牌栏
  const cardCounts = {};
  for(const c of deck){ cardCounts[c]=(cardCounts[c]||0)+1; }
  html += '<div class="card-section">';
  html += '<div class="section-title">🃏 卡牌 <span class="count">('+deck.length+')</span></div>';
  html += '<div class="card-grid">';
  for(const [name,count] of Object.entries(cardCounts)){
    const rarity = getCardRarity(name);
    html += '<div class="card-item '+rarity+'">';
    html += '<div class="card-icon">🃏</div>';
    html += '<div class="card-info"><div class="card-name">'+name+'</div>';
    if(count>1) html += '<div class="card-count">×'+count+'</div>';
    html += '</div></div>';
  }
  html += '</div></div>';

  // 战略分析
  html += '<div class="analysis-section"><div class="section-title">📊 战略复盘分析</div>';
  html += '<div id="analysisContent"><div class="loading">分析中...</div></div>';
  html += '</div>';

  document.getElementById('content').innerHTML = html;

  // 加载分析
  fetch('/api/analysis/'+runId).then(r=>r.json()).then(d=>{
    const a = d.analysis;
    let ah = '<div class="analysis-grid">';
    ah += '<div class="analysis-item"><div class="val">'+a.score+'</div><div class="lbl">综合评分</div></div>';
    ah += '<div class="analysis-item"><div class="val">'+a.archetype.primary+'</div><div class="lbl">主要流派</div></div>';
    ah += '<div class="analysis-item"><div class="val">'+(a.combat_analysis.win_rate||0).toFixed(0)+'%</div><div class="lbl">战斗胜率</div></div>';
    ah += '<div class="analysis-item"><div class="val">'+(a.combat_analysis.avg_hp_loss||0)+'</div><div class="lbl">场均失血</div></div>';
    ah += '</div>';

    if(a.suggestions && a.suggestions.length){
      ah += '<div style="margin-top:16px"><div class="section-title" style="font-size:15px">💡 改进建议</div>';
      for(const s of a.suggestions){
        ah += '<div class="suggestion '+s.type+'"><div class="title">'+s.title+'</div><div class="content">'+s.content+'</div></div>';
      }
      ah += '</div>';
    }
    document.getElementById('analysisContent').innerHTML = ah;
  });
});
</script>
</body>
</html>"""


if __name__ == "__main__":
    print("=" * 50)
    print(f"STS2 Advisor Web App v6.0 ({MODE}模式)")
    print("=" * 50)
    if MODE == "cloud":
        print("云端模式：等待本地agent推送游戏状态")
        print("固定网址：部署后永久不变")
    else:
        print("本地模式：直连游戏API (127.0.0.1:8080)")
    print(f"访问地址: http://127.0.0.1:8766")
    print("=" * 50)
    app.run(host="0.0.0.0", port=8766, debug=False)
