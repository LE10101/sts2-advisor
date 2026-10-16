"""
STS2 Advisor Web Application - 公开网站版
功能：当前对局决策器、历史对局、复盘分析、怪物行为、牌序显示、LLM分析、多用户
"""
import json
import os
import time
import hashlib
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, Response, session

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
    from advisor.cards import CARD_EFFECTS
    return jsonify({"cards": {k: v for k, v in CARD_EFFECTS.items()}})


@app.route("/api/cards/<card_name>")
def api_card_detail(card_name):
    """卡牌详情API"""
    from advisor.cards import CARD_EFFECTS
    if card_name in CARD_EFFECTS:
        return jsonify({"card": {"name": card_name, **CARD_EFFECTS[card_name]}})
    # 模糊搜索
    for name, effect in CARD_EFFECTS.items():
        if card_name.lower() in name.lower():
            return jsonify({"card": {"name": name, **effect}})
    return jsonify({"error": "卡牌未找到"}), 404


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
<title>STS2 决策器 - 静默猎手AI教练</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,'Segoe UI',sans-serif; background:#0f1923; color:#e0e6ed; min-height:100vh; }
.header { background:linear-gradient(135deg,#1a2a3a,#0f1923); padding:20px; border-bottom:2px solid #2d4a6a; }
.header .container { display:flex; justify-content:space-between; align-items:center; max-width:900px; margin:0 auto; }
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
<div class="header"><div class="container">
  <div><h1>STS2 决策器</h1><p>杀戮尖塔2 · 静默猎手AI教练 · 实时决策 + 战略复盘</p></div>
  <div class="user-menu" id="userMenu"><a href="/login">登录</a><a href="/register">注册</a></div>
</div></div>
<div class="container">
  <div class="card-grid">
    <a class="card" href="/live"><div class="icon">⚔️</div><h3>当前对局</h3><p>实时战斗决策推荐、怪物行为显示、牌序记忆、路线/奖励/商店指导</p><span class="status" id="liveStatus">检测中...</span></a>
    <a class="card" href="/history"><div class="icon">📊</div><h3>历史对局</h3><p>查看所有对局记录，筛选进阶、角色、结果，追踪你的进步</p></a>
    <a class="card" href="/monsters"><div class="icon">👹</div><h3>怪物图鉴</h3><p>所有怪物的固定行为模式、伤害数值、应对策略</p></a>
    <a class="card" href="/cards"><div class="icon">🃏</div><h3>卡牌图鉴</h3><p>静默猎手全卡牌效果、升级对比、流派搭配推荐</p></a>
  </div>
</div>
<div class="footer">STS2 Advisor v8.0 · 基于MCTS+评估器 · 数据来自STS2 AI Agent mod</div>
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
</script>
</body>
</html>"""

LOGIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>登录 - STS2决策器</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,sans-serif;background:#0f1923;color:#e0e6ed;min-height:100vh;display:flex;align-items:center;justify-content:center;}
.login-box{background:#1a2a3a;padding:40px;border-radius:12px;border:1px solid #2d4a6a;width:360px;}
.login-box h1{color:#4fc3f7;font-size:24px;margin-bottom:8px;text-align:center;}
.login-box p{color:#8899aa;font-size:14px;text-align:center;margin-bottom:24px;}
.form-group{margin-bottom:16px;}
.form-group label{display:block;font-size:14px;color:#8899aa;margin-bottom:6px;}
.form-group input{width:100%;padding:10px 12px;background:#0f1923;border:1px solid #2d4a6a;border-radius:6px;color:#e0e6ed;font-size:14px;}
.form-group input:focus{outline:none;border-color:#4fc3f7;}
.btn{width:100%;padding:12px;background:#4fc3f7;color:#0f1923;border:none;border-radius:6px;font-size:16px;font-weight:bold;cursor:pointer;margin-top:8px;}
.btn:hover{background:#81d4fa;}
.error{color:#ef5350;font-size:13px;margin-top:8px;text-align:center;min-height:18px;}
.links{margin-top:16px;text-align:center;font-size:14px;}
.links a{color:#4fc3f7;text-decoration:none;}
.steam-btn{width:100%;padding:10px;background:#1b2838;color:#66c0f4;border:1px solid #66c0f4;border-radius:6px;font-size:14px;cursor:pointer;margin-top:12px;}
</style></head>
<body>
<div class="login-box">
  <h1>STS2 决策器</h1><p>登录以同步你的对局历史</p>
  <div class="form-group"><label>用户名</label><input type="text" id="username" placeholder="输入用户名"></div>
  <div class="form-group"><label>密码</label><input type="password" id="password" placeholder="输入密码"></div>
  <button class="btn" onclick="doLogin()">登录</button>
  <div class="error" id="error"></div>
  <button class="steam-btn" onclick="alert('Steam登录开发中')">用Steam账号登录</button>
  <div class="links">还没有账号？<a href="/register">立即注册</a></div>
</div>
<script>
function doLogin(){
  const u=document.getElementById('username').value,p=document.getElementById('password').value;
  fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})})
  .then(r=>r.json()).then(d=>{if(d.ok){location.href='/';}else{document.getElementById('error').textContent=d.error;}});
}
document.getElementById('password').addEventListener('keypress',e=>{if(e.key==='Enter')doLogin();});
</script>
</body></html>"""

REGISTER_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>注册 - STS2决策器</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,sans-serif;background:#0f1923;color:#e0e6ed;min-height:100vh;display:flex;align-items:center;justify-content:center;}
.login-box{background:#1a2a3a;padding:40px;border-radius:12px;border:1px solid #2d4a6a;width:360px;}
.login-box h1{color:#4fc3f7;font-size:24px;margin-bottom:8px;text-align:center;}
.login-box p{color:#8899aa;font-size:14px;text-align:center;margin-bottom:24px;}
.form-group{margin-bottom:16px;}
.form-group label{display:block;font-size:14px;color:#8899aa;margin-bottom:6px;}
.form-group input{width:100%;padding:10px 12px;background:#0f1923;border:1px solid #2d4a6a;border-radius:6px;color:#e0e6ed;font-size:14px;}
.form-group input:focus{outline:none;border-color:#4fc3f7;}
.btn{width:100%;padding:12px;background:#4fc3f7;color:#0f1923;border:none;border-radius:6px;font-size:16px;font-weight:bold;cursor:pointer;margin-top:8px;}
.btn:hover{background:#81d4fa;}
.error{color:#ef5350;font-size:13px;margin-top:8px;text-align:center;min-height:18px;}
.links{margin-top:16px;text-align:center;font-size:14px;}
.links a{color:#4fc3f7;text-decoration:none;}
</style></head>
<body>
<div class="login-box">
  <h1>注册账号</h1><p>创建账号以同步对局历史</p>
  <div class="form-group"><label>用户名（至少3字符）</label><input type="text" id="username" placeholder="输入用户名"></div>
  <div class="form-group"><label>密码（至少6字符）</label><input type="password" id="password" placeholder="输入密码"></div>
  <div class="form-group"><label>确认密码</label><input type="password" id="password2" placeholder="再次输入密码"></div>
  <button class="btn" onclick="doRegister()">注册</button>
  <div class="error" id="error"></div>
  <div class="links">已有账号？<a href="/login">去登录</a></div>
</div>
<script>
function doRegister(){
  const u=document.getElementById('username').value,p=document.getElementById('password').value,p2=document.getElementById('password2').value;
  if(p!==p2){document.getElementById('error').textContent='两次密码不一致';return;}
  fetch('/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})})
  .then(r=>r.json()).then(d=>{if(d.ok){location.href='/';}else{document.getElementById('error').textContent=d.error;}});
}
</script>
</body></html>"""

LIVE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>当前对局 - STS2决策器</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,sans-serif;background:#0f1923;color:#e0e6ed;min-height:100vh;}
.topbar{background:#1a2a3a;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #2d4a6a;position:sticky;top:0;z-index:100;}
.topbar a{color:#4fc3f7;text-decoration:none;font-size:14px;}
.topbar .status{font-size:12px;padding:4px 10px;border-radius:12px;}
.online{background:#1b5e20;color:#66bb6a;}.offline{background:#b71c1c;color:#ef5350;}
.container{max-width:800px;margin:0 auto;padding:16px;}
.panel{background:#1a2a3a;border-radius:10px;padding:16px;margin-bottom:16px;border:1px solid #2d4a6a;}
.panel h2{font-size:16px;color:#4fc3f7;margin-bottom:12px;}
.rec-card{background:linear-gradient(135deg,#1e3a5f,#1a2a3a);border:2px solid #4fc3f7;border-radius:10px;padding:16px;margin-bottom:12px;}
.rec-card .action{font-size:20px;font-weight:bold;color:#fff;}
.rec-card .reason{color:#88ccff;font-size:14px;margin-top:8px;line-height:1.6;}
.stat-row{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px;}
.stat{flex:1;min-width:80px;text-align:center;}
.stat .val{font-size:24px;font-weight:bold;color:#fff;}
.stat .lbl{font-size:12px;color:#8899aa;}
.enemy{background:#2a1a1a;border-radius:8px;padding:10px;margin-bottom:8px;border-left:3px solid #ef5350;}
.enemy .name{font-weight:bold;color:#ef9a9a;}
.enemy .hp-bar{height:6px;background:#333;border-radius:3px;margin:6px 0;overflow:hidden;}
.enemy .hp-fill{height:100%;background:linear-gradient(90deg,#ef5350,#ff8a65);transition:width .3s;}
.enemy .intent{font-size:13px;color:#ffcc80;margin-top:4px;}
.hand{display:flex;flex-wrap:wrap;gap:6px;}
.card-item{background:#2a3a4a;border-radius:6px;padding:8px 10px;font-size:13px;border:1px solid #3d5a7a;}
.card-item.playable{border-color:#66bb6a;}
.card-item.unplayable{opacity:.5;border-color:#555;}
.card-item .cost{display:inline-block;width:20px;height:20px;line-height:20px;text-align:center;background:#4fc3f7;border-radius:50%;font-size:11px;margin-right:6px;color:#000;font-weight:bold;}
.draw-order{font-size:13px;color:#aaa;line-height:1.8;}
.draw-order .known{color:#66bb6a;}
.alternatives{margin-top:8px;}
.alt-item{padding:8px;background:#15202b;border-radius:6px;margin-bottom:4px;font-size:13px;display:flex;justify-content:space-between;}
.alt-item .val{color:#8899aa;}
</style></head>
<body>
<div class="topbar"><a href="/">← 返回首页</a><span>当前对局</span><span class="status offline" id="connStatus">未连接</span></div>
<div class="container">
  <div class="panel"><h2>🎯 推荐动作</h2><div id="recContent"><p style="color:#8899aa">等待游戏数据...</p></div></div>
  <div class="panel"><h2>📊 状态</h2><div class="stat-row" id="stats"></div></div>
  <div class="panel"><h2>👹 敌人</h2><div id="enemies"></div></div>
  <div class="panel"><h2>🃏 手牌</h2><div class="hand" id="hand"></div></div>
  <div class="panel"><h2>📜 牌序记忆 <span style="font-size:12px;color:#8899aa;font-weight:normal">SL后可查看抽牌顺序</span></h2><div class="draw-order" id="drawOrder">暂无数据</div></div>
  <div class="panel"><h2>💡 备选方案</h2><div class="alternatives" id="alts"></div></div>
</div>
<script>
async function update(){
  try{
    const r=await fetch('/api/recommend');const d=await r.json();
    document.getElementById('connStatus').textContent='已连接';document.getElementById('connStatus').className='status online';
    if(d.error){document.getElementById('recContent').innerHTML='<p style="color:#ef5350">'+d.error+'</p>';return;}
    if(d.phase==='combat'&&d.state){
      const s=d.state;
      document.getElementById('stats').innerHTML='<div class="stat"><div class="val" style="color:#ef5350">'+s.hp+'/'+s.max_hp+'</div><div class="lbl">生命</div></div><div class="stat"><div class="val" style="color:#4fc3f7">'+s.block+'</div><div class="lbl">格挡</div></div><div class="stat"><div class="val" style="color:#ffcc80">'+s.energy+'</div><div class="lbl">能量</div></div><div class="stat"><div class="val">T'+s.turn+'</div><div class="lbl">回合</div></div>';
      if(d.best){document.getElementById('recContent').innerHTML='<div class="rec-card"><div class="action">'+d.best.label+'</div><div class="reason">'+d.reason+'</div></div>';}
      document.getElementById('enemies').innerHTML=s.enemies.map(e=>'<div class="enemy"><div class="name">'+e.name+(e.poison>0?' <span style="color:#66bb6a">毒'+e.poison+'</span>':'')+'</div><div class="hp-bar"><div class="hp-fill" style="width:'+(e.hp/e.max_hp*100).toFixed(0)+'%"></div></div><div style="font-size:12px;color:#aaa">'+e.hp+'/'+e.max_hp+' HP '+(e.block>0?'🛡'+e.block:'')+'</div><div class="intent">意图: '+(e.intent_type||'?')+' '+(e.intent_damage>0?'伤害'+e.intent_damage:'')+' '+(e.is_aoe?'(AOE)':'')+'</div></div>').join('');
      document.getElementById('hand').innerHTML=s.hand.map(c=>'<div class="card-item '+(c.playable?'playable':'unplayable')+'"><span class="cost">'+c.cost+'</span>'+c.name+'</div>').join('');
      document.getElementById('alts').innerHTML=(d.ranked||[]).slice(1).map(a=>'<div class="alt-item"><span>'+a.action.label+'</span><span class="val">胜率'+(a.value*100).toFixed(0)+'% ('+a.visits+'次)</span></div>').join('')||'<span style="color:#666">无</span>';
      if(d.draw_order&&d.draw_order.length){document.getElementById('drawOrder').innerHTML='已知牌序: '+d.draw_order.map((c,i)=>'<span class="known">'+(i+1)+'.'+c+'</span>').join(' → ');}
    }else if(d.phase==='map'||d.phase==='reward'||d.phase==='shop'){
      document.getElementById('recContent').innerHTML='<div class="rec-card"><div class="action">'+d.phase+'推荐</div><div class="reason">'+JSON.stringify(d.recommendation||{}).substring(0,200)+'</div></div>';
    }
  }catch(e){
    document.getElementById('connStatus').textContent='未连接';document.getElementById('connStatus').className='status offline';
    document.getElementById('recContent').innerHTML='<p style="color:#8899aa">等待游戏启动...</p>';
  }
}
setInterval(update,1500);update();
</script>
</body></html>"""

HISTORY_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>历史对局 - STS2决策器</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,sans-serif;background:#0f1923;color:#e0e6ed;}
.topbar{background:#1a2a3a;padding:12px 20px;border-bottom:1px solid #2d4a6a;}
.topbar a{color:#4fc3f7;text-decoration:none;}
.container{max-width:800px;margin:0 auto;padding:16px;}
.run-item{background:#1a2a3a;border-radius:10px;padding:16px;margin-bottom:12px;border:1px solid #2d4a6a;cursor:pointer;transition:all .2s;display:flex;justify-content:space-between;align-items:center;}
.run-item:hover{border-color:#4fc3f7;}
.run-item .info{flex:1;}
.run-item .date{color:#8899aa;font-size:12px;}
.run-item .meta{margin-top:6px;font-size:14px;}
.run-item .meta span{margin-right:16px;}
.run-item .result{padding:4px 12px;border-radius:12px;font-size:12px;}
.win{background:#1b5e20;color:#66bb6a;}.lose{background:#b71c1c;color:#ef5350;}
.empty{text-align:center;padding:60px;color:#556677;}
</style></head>
<body>
<div class="topbar"><a href="/">← 返回首页</a> | 历史对局</div>
<div class="container"><div id="runs"><div class="empty">加载中...</div></div></div>
<script>
fetch('/api/history').then(r=>r.json()).then(d=>{
  const el=document.getElementById('runs');
  if(!d.runs.length){el.innerHTML='<div class="empty">暂无对局记录<br><small>完成一局后会自动保存</small></div>';return;}
  el.innerHTML=d.runs.map(r=>'<div class="run-item" onclick="location.href=\'/replay/'+r.id+'\'"><div class="info"><div class="date">'+r.date+'</div><div class="meta"><span>进阶'+r.ascension+'</span><span>'+r.character+'</span><span>楼层'+r.floor+'</span><span>'+r.deck_size+'张牌</span><span>'+r.relics+'遗物</span></div></div><span class="result '+(r.result==='胜利'?'win':'lose')+'">'+r.result+'</span></div>').join('');
});
</script>
</body></html>"""

MONSTERS_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>怪物图鉴 - STS2决策器</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,sans-serif;background:#0f1923;color:#e0e6ed;}
.topbar{background:#1a2a3a;padding:12px 20px;border-bottom:1px solid #2d4a6a;}
.topbar a{color:#4fc3f7;text-decoration:none;}
.container{max-width:900px;margin:0 auto;padding:16px;}
.filters{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;}
.filter-btn{padding:6px 14px;background:#1a2a3a;border:1px solid #2d4a6a;border-radius:20px;color:#8899aa;cursor:pointer;font-size:13px;}
.filter-btn.active{background:#4fc3f7;color:#000;border-color:#4fc3f7;}
.monster{background:#1a2a3a;border-radius:10px;padding:14px 16px;margin-bottom:10px;border:1px solid #2d4a6a;cursor:pointer;transition:all .2s;}
.monster:hover{border-color:#4fc3f7;background:#1f3347;transform:translateX(4px);}
.monster h3{color:#ef9a9a;margin-bottom:6px;display:flex;align-items:center;gap:8px;}
.monster .type-tag{font-size:11px;padding:2px 8px;border-radius:10px;background:#2d4a6a;color:#8899aa;}
.monster .type-tag.boss{background:#8b0000;color:#ffaaaa;}
.monster .type-tag.elite{background:#8b6914;color:#ffd700;}
.monster .hp{color:#8899aa;font-size:13px;margin-bottom:6px;}
.monster .tip{color:#a0d0a0;font-size:12px;font-style:italic;}
.monster .moves-preview{font-size:12px;color:#667788;margin-top:4px;}
/* 详情弹窗 */
.modal-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.8);z-index:100;justify-content:center;align-items:center;padding:20px;}
.modal-overlay.show{display:flex;}
.modal{background:#1a2a3a;border-radius:12px;padding:24px;max-width:500px;width:100%;max-height:85vh;overflow-y:auto;border:2px solid #4fc3f7;}
.modal h2{color:#ef9a9a;margin-bottom:12px;}
.modal .close-btn{float:right;background:none;border:none;color:#8899aa;font-size:24px;cursor:pointer;}
.modal .detail-row{margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid #2d4a6a;}
.modal .detail-label{color:#8899aa;font-size:12px;margin-bottom:4px;}
.modal .detail-value{color:#e0e6ed;font-size:14px;}
.modal .move-item{padding:8px 0;border-bottom:1px solid #2d4a6a;}
.modal .move-name{color:#ffcc80;font-weight:bold;}
.modal .move-desc{color:#aaa;font-size:13px;margin-top:2px;}
.modal .tip-box{background:rgba(76,175,80,.1);border-left:3px solid #4caf50;padding:10px;margin-top:12px;border-radius:4px;}
.modal .tip-box .label{color:#4caf50;font-size:12px;font-weight:bold;margin-bottom:4px;}
.empty{text-align:center;padding:60px;color:#556677;}
</style></head>
<body>
<div class="topbar"><a href="/">← 返回首页</a> | 怪物图鉴</div>
<div class="container">
  <div class="filters" id="filters">
    <button class="filter-btn active" data-act="all">全部</button>
    <button class="filter-btn" data-act="密林">密林</button>
    <button class="filter-btn" data-act="巢穴">巢穴</button>
    <button class="filter-btn" data-act="荣耀">荣耀</button>
    <button class="filter-btn" data-act="暗港">暗港</button>
  </div>
  <div id="list"><div class="empty">加载中...</div></div>
</div>
<div class="modal-overlay" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal">
    <button class="close-btn" onclick="closeModal()">×</button>
    <div id="modal-content"></div>
  </div>
</div>
<script>
let allMonsters=[];
let currentFilter='all';
fetch('/api/monsters').then(r=>r.json()).then(d=>{
  allMonsters=d.monsters||[];
  renderMonsters();
});
document.getElementById('filters').addEventListener('click',e=>{
  if(e.target.classList.contains('filter-btn')){
    document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
    e.target.classList.add('active');
    currentFilter=e.target.dataset.act;
    renderMonsters();
  }
});
function renderMonsters(){
  const list=currentFilter==='all'?allMonsters:allMonsters.filter(m=>m.act===currentFilter);
  const el=document.getElementById('list');
  if(!list.length){el.innerHTML='<div class="empty">暂无怪物数据</div>';return;}
  el.innerHTML=list.map(m=>'<div class="monster" onclick="showDetail(\\''+(m.id||m.name)+'\\')">'+
    '<h3>'+m.name+'<span class="type-tag '+m.type+'">'+m.type+'</span></h3>'+
    '<div class="hp">HP: '+m.hp_min+'-'+m.hp_max+(m.hp_asc_min?' (进阶'+m.hp_asc_min+'-'+m.hp_asc_max+')':'')+' | '+m.act+'</div>'+
    '<div class="moves-preview">招式: '+(m.moves||[]).map(mv=>mv.name.replace('!','')).join(' / ')+'</div>'+
    (m.tip?'<div class="tip">💡 '+m.tip+'</div>':'')+
  '</div>').join('');
}
function showDetail(id){
  const m=allMonsters.find(x=>(x.id||x.name)===id);
  if(!m)return;
  const c=document.getElementById('modal-content');
  c.innerHTML='<h2>'+m.name+'</h2>'+
    '<div class="detail-row"><div class="detail-label">章节 / 类型</div><div class="detail-value">'+m.act+' · '+m.type+'</div></div>'+
    '<div class="detail-row"><div class="detail-label">血量</div><div class="detail-value">'+m.hp_min+'-'+m.hp_max+(m.hp_asc_min?' (进阶: '+m.hp_asc_min+'-'+m.hp_asc_max+')':'')+'</div></div>'+
    (m.abilities&&m.abilities.length?'<div class="detail-row"><div class="detail-label">初始能力</div><div class="detail-value">'+m.abilities.join(', ')+'</div></div>':'')+
    '<div class="detail-row"><div class="detail-label">招式列表 ('+(m.moves||[]).length+')</div>'+
    (m.moves||[]).map(mv=>'<div class="move-item"><div class="move-name">'+mv.name+'</div><div class="move-desc">'+mv.desc+(mv.damage?' · 伤害'+mv.damage+(mv.hits>1?'×'+mv.hits:''):'')+'</div></div>').join('')+'</div>'+
    (m.tip?'<div class="tip-box"><div class="label">应对策略</div><div>'+m.tip+'</div></div>':'');
  document.getElementById('modal').classList.add('show');
}
function closeModal(){document.getElementById('modal').classList.remove('show');}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});
</script>
</body></html>"""

CARDS_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>卡牌图鉴 - STS2决策器</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:-apple-system,sans-serif;background:#0f1923;color:#e0e6ed;}
.topbar{background:#1a2a3a;padding:12px 20px;border-bottom:1px solid #2d4a6a;}
.topbar a{color:#4fc3f7;text-decoration:none;}
.container{max-width:1000px;margin:0 auto;padding:16px;}
.search-box{margin-bottom:16px;}
.search-box input{width:100%;padding:10px 16px;background:#1a2a3a;border:1px solid #2d4a6a;border-radius:8px;color:#e0e6ed;font-size:14px;}
.search-box input:focus{outline:none;border-color:#4fc3f7;}
.filters{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;}
.filter-btn{padding:6px 14px;background:#1a2a3a;border:1px solid #2d4a6a;border-radius:20px;color:#8899aa;cursor:pointer;font-size:13px;}
.filter-btn.active{background:#4fc3f7;color:#000;border-color:#4fc3f7;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;}
.card{background:#1a2a3a;border-radius:8px;padding:12px;border:1px solid #2d4a6a;font-size:13px;cursor:pointer;transition:all .2s;}
.card:hover{border-color:#4fc3f7;background:#1f3347;transform:translateY(-2px);}
.card .name{color:#4fc3f7;font-weight:bold;margin-bottom:6px;display:flex;align-items:center;gap:6px;}
.card .cost{display:inline-block;width:20px;height:20px;line-height:20px;text-align:center;background:#4fc3f7;border-radius:50%;font-size:12px;color:#000;font-weight:bold;}
.card .rarity{font-size:10px;padding:1px 6px;border-radius:8px;margin-left:auto;}
.card .rarity.common{background:#666;color:#fff;}
.card .rarity.uncommon{background:#4a7c4a;color:#fff;}
.card .rarity.rare{background:#b8860b;color:#fff;}
.card .effect{color:#aaa;font-size:12px;line-height:1.5;}
.card .tags{margin-top:6px;display:flex;gap:4px;flex-wrap:wrap;}
.card .tag{font-size:10px;padding:1px 6px;background:#2d4a6a;border-radius:8px;color:#8899aa;}
/* 详情弹窗 */
.modal-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.8);z-index:100;justify-content:center;align-items:center;padding:20px;}
.modal-overlay.show{display:flex;}
.modal{background:#1a2a3a;border-radius:12px;padding:24px;max-width:500px;width:100%;max-height:85vh;overflow-y:auto;border:2px solid #4fc3f7;}
.modal h2{color:#4fc3f7;margin-bottom:12px;display:flex;align-items:center;gap:10px;}
.modal .close-btn{float:right;background:none;border:none;color:#8899aa;font-size:24px;cursor:pointer;}
.modal .detail-row{margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #2d4a6a;}
.modal .detail-label{color:#8899aa;font-size:12px;margin-bottom:4px;}
.modal .detail-value{color:#e0e6ed;font-size:14px;line-height:1.6;}
.modal .synergy-box{background:rgba(76,175,80,.1);border-left:3px solid #4caf50;padding:10px;margin-top:12px;border-radius:4px;}
.modal .synergy-box .label{color:#4caf50;font-size:12px;font-weight:bold;margin-bottom:4px;}
.empty{text-align:center;padding:60px;color:#556677;}
</style></head>
<body>
<div class="topbar"><a href="/">← 返回首页</a> | 卡牌图鉴（静默猎手）</div>
<div class="container">
  <div class="search-box"><input type="text" id="search" placeholder="搜索卡牌名称或效果..." oninput="renderCards()"></div>
  <div class="filters" id="filters">
    <button class="filter-btn active" data-rarity="all">全部</button>
    <button class="filter-btn" data-rarity="common">普通</button>
    <button class="filter-btn" data-rarity="uncommon">罕见</button>
    <button class="filter-btn" data-rarity="rare">稀有</button>
    <button class="filter-btn" data-type="attack">攻击</button>
    <button class="filter-btn" data-type="skill">技能</button>
    <button class="filter-btn" data-type="power">能力</button>
  </div>
  <div class="grid" id="grid"></div>
</div>
<div class="modal-overlay" id="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal">
    <button class="close-btn" onclick="closeModal()">×</button>
    <div id="modal-content"></div>
  </div>
</div>
<script>
let allCards=[];
let currentRarity='all';
let currentType='all';
fetch('/api/cards').then(r=>r.json()).then(d=>{
  allCards=Object.entries(d.cards).map(([name,e])=>({name,...e}));
  renderCards();
});
document.getElementById('filters').addEventListener('click',e=>{
  if(e.target.classList.contains('filter-btn')){
    const type=e.target.dataset.rarity||e.target.dataset.type;
    if(e.target.dataset.rarity){currentRarity=type;currentType='all';}
    else{currentType=type;currentRarity='all';}
    document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
    e.target.classList.add('active');
    renderCards();
  }
});
function renderCards(){
  const q=document.getElementById('search').value.toLowerCase();
  let list=allCards;
  if(currentRarity!=='all')list=list.filter(c=>(c.rarity||'common')===currentRarity);
  if(currentType!=='all')list=list.filter(c=>(c.type||'')===currentType);
  if(q)list=list.filter(c=>c.name.toLowerCase().includes(q)||JSON.stringify(c).toLowerCase().includes(q));
  const el=document.getElementById('grid');
  if(!list.length){el.innerHTML='<div class="empty">未找到卡牌</div>';return;}
  el.innerHTML=list.map(c=>{
    const eff=[];
    if(c.attack)eff.push('攻击'+c.attack+(c.hits>1?'×'+c.hits:''));
    if(c.block)eff.push('格挡'+c.block);
    if(c.poison)eff.push('毒'+c.poison);
    if(c.draw)eff.push('抽'+c.draw);
    if(c.weak)eff.push('虚弱'+c.weak);
    if(c.vulnerable)eff.push('易伤'+c.vulnerable);
    return '<div class="card" onclick="showDetail(\\''+c.name.replace(/'/g,"\\\\'")+'\\')">'+
      '<div class="name"><span class="cost">'+(c.cost??'?')+'</span>'+c.name+
      '<span class="rarity '+(c.rarity||'common')+'">'+(c.rarity||'普通')+'</span></div>'+
      '<div class="effect">'+eff.join(' ')+(c.description?' · '+c.description:'')+'</div>'+
    '</div>';
  }).join('');
}
function showDetail(name){
  const c=allCards.find(x=>x.name===name);
  if(!c)return;
  const eff=[];
  if(c.attack)eff.push('攻击力: '+c.attack+(c.hits>1?' ×'+c.hits+'段':''));
  if(c.block)eff.push('格挡: '+c.block);
  if(c.poison)eff.push('施加毒: '+c.poison);
  if(c.draw)eff.push('抽牌: '+c.draw);
  if(c.weak)eff.push('施加虚弱: '+c.weak);
  if(c.vulnerable)eff.push('施加易伤: '+c.vulnerable);
  if(c.energy)eff.push('获得能量: '+c.energy);
  const c2=document.getElementById('modal-content');
  c2.innerHTML='<h2><span class="cost">'+(c.cost??'?')+'</span>'+c.name+
    '<span class="rarity '+(c.rarity||'common')+'">'+(c.rarity||'普通')+'</span></h2>'+
    '<div class="detail-row"><div class="detail-label">类型</div><div class="detail-value">'+(c.type||'未知')+'</div></div>'+
    '<div class="detail-row"><div class="detail-label">效果</div><div class="detail-value">'+(eff.length?eff.join('<br>'):(c.description||'无详细数据'))+'</div></div>'+
    (c.description?'<div class="detail-row"><div class="detail-label">卡牌描述</div><div class="detail-value">'+c.description+'</div></div>':'')+
    (c.upgraded?'<div class="detail-row"><div class="detail-label">升级效果</div><div class="detail-value">'+c.upgraded+'</div></div>':'')+
    '<div class="synergy-box"><div class="label">流派适配</div><div>'+getSynergy(c)+'</div></div>';
  document.getElementById('modal').classList.add('show');
}
function getSynergy(c){
  const n=c.name.toLowerCase();
  if(n.includes('毒')||c.poison)return '适合毒流，与 致命毒药、毒雾、催化剂 搭配';
  if(n.includes('shiv')||n.includes('匕首')||c.shiv)return '适合Shiv流，与 无限刀刃、刀锋之舞 搭配';
  if(c.block&&c.draw)return '适合格挡流，与 后空翻、逃脱计划 搭配';
  if(c.draw)return '适合过牌流，与 战术、肾上腺素 搭配';
  return '通用卡牌，可融入多种流派';
}
function closeModal(){document.getElementById('modal').classList.remove('show');}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});
</script>
</body></html>"""

REPLAY_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>对局历史 - STS2决策器</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{font-family:'Georgia',serif;background:linear-gradient(180deg,#1a0f0a,#0d0705);color:#e8dcc8;min-height:100vh;}
.topbar{background:rgba(0,0,0,.6);padding:10px 20px;border-bottom:2px solid #8b6914;}
.topbar a{color:#d4a843;text-decoration:none;font-size:14px;}
.container{max-width:1100px;margin:0 auto;padding:20px;}
.info-bar{display:flex;align-items:center;gap:20px;padding:16px;background:rgba(0,0,0,.4);border-radius:8px;margin-bottom:20px;flex-wrap:wrap;}
.info-bar .char-icon{width:50px;height:50px;background:linear-gradient(135deg,#2d5a27,#1a3a18);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:28px;border:2px solid #8b6914;}
.info-bar .stat{display:flex;align-items:center;gap:6px;font-size:18px;}
.info-bar .stat .icon{font-size:22px;}
.info-bar .stat.hp{color:#ff6b6b;}
.info-bar .stat.gold{color:#ffd700;}
.info-bar .stat.floor{color:#87ceeb;}
.info-bar .right{margin-left:auto;text-align:right;font-size:13px;color:#a89880;}
.relic-section,.card-section,.analysis-section,.map-section{background:rgba(0,0,0,.3);border-radius:8px;padding:16px;margin-bottom:20px;}
.section-title{font-size:18px;color:#d4a843;margin-bottom:12px;}
.section-title .count{color:#a89880;font-size:14px;margin-left:8px;}
.relic-grid{display:flex;flex-wrap:wrap;gap:8px;}
.relic-item{width:48px;height:48px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:24px;background:rgba(255,255,255,.05);border:2px solid #555;position:relative;cursor:pointer;transition:transform .15s;}
.relic-item:hover{transform:scale(1.1);}
.relic-item .tooltip{position:absolute;bottom:100%;left:50%;transform:translateX(-50%);background:#222;padding:6px 10px;border-radius:4px;font-size:12px;white-space:nowrap;display:none;z-index:10;border:1px solid #555;}
.relic-item:hover .tooltip{display:block;}
.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:8px;}
.card-item{background:linear-gradient(135deg,#1a2a1a,#0d1a0d);border:2px solid #4a6a4a;border-radius:8px;padding:10px;display:flex;align-items:center;gap:8px;cursor:pointer;transition:all .15s;}
.card-item:hover{border-color:#6a9a6a;transform:translateY(-2px);}
.card-item .card-icon{width:32px;height:40px;background:rgba(255,255,255,.1);border-radius:4px;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;}
.card-item .card-info{flex:1;min-width:0;}
.card-item .card-name{font-size:13px;color:#e8dcc8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.card-item .card-count{font-size:11px;color:#888;}
.card-item.rare{border-color:#ffd700;background:linear-gradient(135deg,#2a2a1a,#1a1a0d);}
.card-item.uncommon{border-color:#4a9eff;background:linear-gradient(135deg,#1a2a3a,#0d1a2a);}
.card-item.curse{border-color:#8b3a8b;background:linear-gradient(135deg,#2a1a2a,#1a0d1a);}
.card-item.basic{border-color:#666;background:linear-gradient(135deg,#222,#111);}
.analysis-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:16px;}
.analysis-item{background:rgba(255,255,255,.03);padding:12px;border-radius:6px;text-align:center;}
.analysis-item .val{font-size:28px;font-weight:bold;color:#d4a843;}
.analysis-item .lbl{font-size:12px;color:#888;margin-top:4px;}
.suggestion{background:rgba(255,200,50,.1);border-left:3px solid #ffc832;padding:10px 14px;margin-bottom:8px;border-radius:0 6px 6px 0;}
.suggestion.warning{background:rgba(255,100,100,.1);border-left-color:#ff6464;}
.suggestion.info{background:rgba(100,150,255,.1);border-left-color:#6496ff;}
.suggestion .title{font-weight:bold;color:#ffc832;margin-bottom:4px;}
.suggestion.warning .title{color:#ff6464;}
.suggestion.info .title{color:#6496ff;}
.suggestion .content{font-size:13px;color:#ccc;line-height:1.5;}
.loading{text-align:center;padding:60px;color:#666;font-size:16px;}
</style></head>
<body>
<div class="topbar"><a href="/history">← 返回历史列表</a> | 对局历史记录</div>
<div class="container" id="content"><div class="loading">加载中...</div></div>
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
  html+='<div class="relic-section"><div class="section-title">📦 遗物 <span class="count">('+relics.length+')</span></div><div class="relic-grid">';
  for(const r of relics){html+='<div class="relic-item common"><span>'+getRelicEmoji(r)+'</span><div class="tooltip">'+r+'</div></div>';}
  html+='</div></div>';
  const cardCounts={};for(const c of deck){cardCounts[c]=(cardCounts[c]||0)+1;}
  html+='<div class="card-section"><div class="section-title">🃏 卡牌 <span class="count">('+deck.length+')</span></div><div class="card-grid">';
  for(const [name,count] of Object.entries(cardCounts)){
    html+='<div class="card-item '+getCardRarity(name)+'"><div class="card-icon">🃏</div><div class="card-info"><div class="card-name">'+name+'</div>'+(count>1?'<div class="card-count">×'+count+'</div>':'')+'</div></div>';
  }
  html+='</div></div>';
  html+='<div class="analysis-section"><div class="section-title">📊 战略复盘分析</div><div id="analysisContent"><div class="loading">分析中...</div></div></div>';
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
