"""
LLM大语言模型接入模块
支持OpenAI兼容API，提供战略分析、决策建议、复盘解读
无API key时自动降级为规则分析
"""
import json
import os
import urllib.request
from typing import Optional


class LLMClient:
    """LLM客户端，支持OpenAI兼容API"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model
        self.enabled = bool(self.api_key)

    def _call_api(self, messages: list[dict], temperature: float = 0.3) -> str:
        """调用LLM API"""
        if not self.enabled:
            return ""

        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1000
            }
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(payload).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[LLM调用失败: {str(e)}]"

    def analyze_combat(self, state_dict: dict, recommendation: dict) -> str:
        """分析当前战斗局面，给出战略建议"""
        if not self.enabled:
            return self._rule_based_combat_analysis(state_dict, recommendation)

        prompt = f"""你是杀戮尖塔2静默猎手的专家教练。请分析当前战斗局面并给出建议。

当前状态：
- HP: {state_dict.get('hp')}/{state_dict.get('max_hp')}
- 格挡: {state_dict.get('block')}
- 能量: {state_dict.get('energy')}
- 回合: {state_dict.get('turn')}
- 手牌: {[c['name'] for c in state_dict.get('hand', [])]}
- 敌人: {json.dumps(state_dict.get('enemies', []), ensure_ascii=False)}

推荐动作: {recommendation.get('best', {}).get('label', '无')}
推荐理由: {recommendation.get('reason', '')}

请用简洁的中文回答：
1. 当前局面的核心风险是什么？
2. 这个回合的最优策略是什么？
3. 有什么需要注意的细节？"""

        return self._call_api([{"role": "user", "content": prompt}])

    def analyze_reward(self, deck: list[str], card_options: list[str],
                       relics: list[str], hp: int, gold: int) -> str:
        """分析选卡决策"""
        if not self.enabled:
            return self._rule_based_reward_analysis(deck, card_options, relics)

        prompt = f"""你是杀戮尖塔2静默猎手的专家教练。请分析选卡决策。

当前牌组({len(deck)}张): {deck}
遗物: {relics}
HP: {hp}, 金币: {gold}
可选卡牌: {card_options}

请用简洁的中文回答：
1. 推荐选哪张牌？为什么？
2. 这张牌对牌组的提升在哪里？
3. 有没有需要避免的陷阱？"""

        return self._call_api([{"role": "user", "content": prompt}])

    def analyze_route(self, hp: int, floor: int, deck: list[str],
                      options: list[dict]) -> str:
        """分析路线选择"""
        if not self.enabled:
            return "根据当前状态，推荐选择最有利于牌组发育的路线。"

        prompt = f"""你是杀戮尖塔2静默猎手的专家教练。请分析路线选择。

HP: {hp}, 楼层: {floor}
牌组: {deck}
可选路线: {json.dumps(options, ensure_ascii=False)}

请用简洁的中文推荐路线并说明理由。"""

        return self._call_api([{"role": "user", "content": prompt}])

    def analyze_run(self, run_data: dict) -> str:
        """分析整局游戏，给出复盘建议"""
        if not self.enabled:
            from .analysis import generate_replay_narrative
            return generate_replay_narrative(run_data)

        prompt = f"""你是杀戮尖塔2静默猎手的专家教练。请分析这局游戏并给出复盘建议。

对局数据:
- 进阶: {run_data.get('ascension', 0)}
- 最高楼层: {run_data.get('max_floor', 0)}
- 结果: {run_data.get('result', '未知')}
- 牌组({len(run_data.get('deck', []))}张): {run_data.get('deck', [])}
- 遗物({len(run_data.get('relics', []))}个): {run_data.get('relics', [])}
- 战斗数: {len(run_data.get('combats', []))}

请用中文给出：
1. 这局的核心打法和流派
2. 做得好的地方
3. 可以改进的地方（选卡、路线、战斗细节）
4. 下一局的建议"""

        return self._call_api([{"role": "user", "content": prompt}], temperature=0.4)

    # ===== 规则分析降级方案 =====
    def _rule_based_combat_analysis(self, state: dict, rec: dict) -> str:
        """无LLM时的规则分析"""
        lines = []
        hp_ratio = state.get("hp", 70) / state.get("max_hp", 70)

        # 风险评估
        total_threat = sum(e.get("intent_damage", 0) for e in state.get("enemies", []))
        block = state.get("block", 0)
        if total_threat > block + 10:
            lines.append(f"⚠️ 风险：敌人总威胁{total_threat}点，格挡仅{block}点，需要优先防御")
        elif hp_ratio < 0.3:
            lines.append("⚠️ 风险：血量低于30%，谨慎作战")
        else:
            lines.append("✅ 局面相对安全")

        # 策略建议
        best = rec.get("best", {})
        if best.get("kind") == "end_turn":
            lines.append(f"策略：{best.get('label', '结束回合')}，保留手牌到下回合")
        else:
            lines.append(f"策略：{best.get('label', '打出推荐牌')}")

        # 敌人优先级
        enemies = state.get("enemies", [])
        if len(enemies) > 1:
            low_hp = min(enemies, key=lambda e: e.get("hp", 999))
            lines.append(f"优先击杀：{low_hp.get('name', '?')}（HP {low_hp.get('hp', 0)}）")

        return "\n".join(lines)

    def _rule_based_reward_analysis(self, deck: list[str], options: list[str],
                                    relics: list[str]) -> str:
        """无LLM时的选卡规则分析"""
        from .cardvalue import score_card_for_deck

        lines = []
        scores = []
        for card in options:
            try:
                score = score_card_for_deck(card, deck, relics)
                scores.append((card, score))
            except:
                scores.append((card, 5.0))

        scores.sort(key=lambda x: x[1], reverse=True)
        if scores:
            best_card, best_score = scores[0]
            lines.append(f"推荐：「{best_card}」（评分{best_score:.1f}）")
            if len(scores) > 1:
                lines.append(f"次选：「{scores[1][0]}」（评分{scores[1][1]:.1f}）")

        # 流派判断
        poison_count = sum(1 for c in deck if "毒" in c)
        if poison_count >= 3:
            lines.append("当前为毒流派，优先选择毒相关卡牌")

        return "\n".join(lines)


# 全局单例
_llm_client: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    """获取LLM客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def configure_llm(api_key: str, base_url: str = "", model: str = "gpt-4o-mini"):
    """配置LLM"""
    global _llm_client
    _llm_client = LLMClient(api_key=api_key, base_url=base_url or None, model=model)
    return _llm_client
