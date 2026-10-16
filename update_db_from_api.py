#!/usr/bin/env python3
"""从spire-codex API获取最新数据，更新cards_db.py/relics_db.py/monsters.py"""
import json, urllib.request, re

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def clean_desc(text):
    """清理描述中的BBCode标签"""
    if not text: return ''
    text = re.sub(r'\[gold\](.*?)\[/gold\]', r'\1', text)
    text = re.sub(r'\[blue\](.*?)\[/blue\]', r'\1', text)
    text = re.sub(r'\[red\](.*?)\[/red\]', r'\1', text)
    text = re.sub(r'\[green\](.*?)\[/green\]', r'\1', text)
    text = re.sub(r'\[purple\](.*?)\[/purple\]', r'\1', text)
    text = re.sub(r'\[.*?\]', '', text)
    return text.strip()

print("=== 获取卡牌数据 ===")
cards_raw = fetch("https://spire-codex.com/api/cards?color=silent&lang=zhs")
print(f"获取到 {len(cards_raw)} 张卡牌")

cards = []
for c in cards_raw:
    cid = c['id'].lower()
    img_url = f"https://cdn.spire-codex.com/cards-full/stable/{cid}.webp"
    img_upg = f"https://cdn.spire-codex.com/cards-full/stable/{cid}_upg.webp"
    cards.append({
        'id': cid,
        'name_cn': c.get('name', ''),
        'name_en': c['id'].replace('_', ' ').title(),
        'cost': c.get('cost', 0),
        'type': c.get('type', ''),
        'rarity': c.get('rarity', ''),
        'effect': clean_desc(c.get('description', '')),
        'upgraded': clean_desc(c.get('description_upgraded', '')) or clean_desc(c.get('description', '')),
        'image_url': img_url,
        'image_url_upg': img_upg,
        'tags': [c.get('type', ''), c.get('rarity', '')],
        'synergy': ''
    })

print(f"处理后 {len(cards)} 张卡牌")
print(f"前3张: {[c['name_cn'] for c in cards[:3]]}")

print("\n=== 获取遗物数据 ===")
relics_raw = fetch("https://spire-codex.com/api/relics?lang=zhs")
print(f"获取到 {len(relics_raw)} 个遗物（全部角色）")

relics = []
for r in relics_raw:
    pool = r.get('pool', 'shared')
    if pool not in ('silent', 'shared'):
        continue
    rid = r['id'].lower()
    img_url = r.get('image_url', '')
    if img_url and img_url.startswith('/'):
        img_url = 'https://spire-codex.com' + img_url
    relics.append({
        'id': rid,
        'name': r.get('name', ''),
        'name_en': r['id'].replace('_', ' ').title(),
        'effect': clean_desc(r.get('description', '')),
        'description': clean_desc(r.get('flavor', '')),
        'rarity': r.get('rarity', '').replace('遗物', ''),
        'pool': pool,
        'image_url': img_url,
        'synergy': ''
    })

print(f"筛选后 {len(relics)} 个静默猎手/共享遗物")
print(f"前3个: {[r['name'] for r in relics[:3]]}")

print("\n=== 获取怪物数据 ===")
monsters_raw = fetch("https://spire-codex.com/api/monsters?lang=zhs")
print(f"获取到 {len(monsters_raw)} 个怪物")

monsters = []
for m in monsters_raw:
    mid = m['id'].lower()
    img_url = m.get('image_url', '')
    if img_url and img_url.startswith('/'):
        img_url = 'https://spire-codex.com' + img_url
    
    moves = []
    for mv in m.get('moves', []):
        dmg = mv.get('damage', {})
        moves.append({
            'name': mv.get('name', ''),
            'intent': mv.get('intent', ''),
            'damage': dmg.get('normal', 0) if isinstance(dmg, dict) else 0,
            'hits': dmg.get('hit_count', 1) if isinstance(dmg, dict) else 1,
            'desc': clean_desc(mv.get('description', ''))
        })
    
    monsters.append({
        'id': mid,
        'name': m.get('name', ''),
        'act': m.get('act', '未知'),
        'type': m.get('type', '普通'),
        'hp_min': m.get('min_hp', 0),
        'hp_max': m.get('max_hp', m.get('min_hp', 0)),
        'hp_asc_min': m.get('min_hp_ascension', m.get('min_hp', 0)),
        'hp_asc_max': m.get('max_hp_ascension', m.get('max_hp', m.get('min_hp', 0))),
        'moves': moves,
        'abilities': [],
        'tip': '',
        'image_url': img_url
    })

print(f"处理后 {len(monsters)} 个怪物")
print(f"前3个: {[m['name'] for m in monsters[:3]]}")

# 写入cards_db.py
print("\n=== 写入cards_db.py ===")
with open('advisor/cards_db.py', 'w', encoding='utf-8') as f:
    f.write('"""静默猎手卡牌数据库 - 数据来源: spire-codex.com"""\n\n')
    f.write('CARDS = ')
    f.write(repr(cards))
    f.write('\n')
print(f"✅ cards_db.py 写入完成，{len(cards)}张卡牌")

# 写入relics_db.py
print("=== 写入relics_db.py ===")
with open('advisor/relics_db.py', 'w', encoding='utf-8') as f:
    f.write('"""遗物数据库 - 数据来源: spire-codex.com"""\n\n')
    f.write('RELICS = ')
    f.write(repr(relics))
    f.write('\n')
print(f"✅ relics_db.py 写入完成，{len(relics)}个遗物")

# 写入monsters.py
print("=== 写入monsters.py ===")
with open('advisor/monsters.py', 'w', encoding='utf-8') as f:
    f.write('"""怪物数据库 - 数据来源: spire-codex.com"""\n\n')
    f.write('MONSTERS = ')
    f.write(repr(monsters))
    f.write('\n')
print(f"✅ monsters.py 写入完成，{len(monsters)}个怪物")

print("\n=== 全部完成！===")
