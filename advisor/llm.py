"""
LLM大语言模型接入模块
支持OpenAI兼容API，无key时降级为规则分析
"""
import os
import json
from typing import Optional


class LLMClient:
    """LLM客户端 - 支持OpenAI兼容API"""

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        self.enabled = bool(self.api_key)

    def _call_api(self, messages: list, max_tokens: int = 1000) -> str:
        """调用LLM API"""
        if not self.enabled:
            return ""
        try:
            import urllib.request
            data = json.dumps({
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[LLM调用失败: {e}]"

    def analyze_combat(self, state: dict, recommendation: dict) -> str:
        """分析战斗局面"""
        if not self.enabled:
            return self._rule_based_combat_analysis(state, recommendation)

        prompt = f"""你是杀戮尖塔2的顶级玩家。请分析当前战斗局面并给出建议。

当前状态：
- 玩家HP: {state.get('hp', '?')}/{state.get('max_hp', '?')}
- 格挡: {state.get('block', 0)}
- 能量: {state.get('energy', '?')}
- 回合: {state.get('turn', '?')}
- 手牌: {[c.get('name') for c in state.get('hand', [])]}
- 敌人: {[{ 'name': e.get('name'), 'hp': e.get('hp'), 'intent': e.get('intent_type')} for e in state.get('enemies', [])]}

AI推荐: {recommendation.get('best', {}).get('label', '无')}
推荐理由: {recommendation.get('reason', '')}

请用中文回答：
1. 当前局面的关键判断
2. 推荐动作是否合理
3. 有没有更好的选择
4. 后续回合的规划"""

        messages = [
            {"role": "system", "content": "你是杀戮尖塔2的顶级玩家，擅长静默猎手。回答简洁专业。"},
            {"role": "user", "content": prompt}
        ]
        return self._call_api(messages)

    def analyze_run(self, run_data: dict) -> str:
        """分析整局对局"""
        if not self.enabled:
            return self._rule_based_run_analysis(run_data)

        deck = run_data.get("deck", [])
        relics = run_data.get("relics", [])
        result = run_data.get("result", "未知")

        prompt = f"""请分析这局杀戮尖塔2静默猎手对局。

对局结果: {result}
进阶等级: {run_data.get('ascension', 0)}
到达楼层: {run_data.get('max_floor', 0)}
最终牌组({len(deck)}张): {deck}
遗物({len(relics)}个): {relics}

请用中文回答：
1. 牌组构成分析（流派、优缺点）
2. 关键决策点评价
3. 如果重来，会做哪些不同的选择
4. 整体评分和改进建议"""

        messages = [
            {"role": "system", "content": "你是杀戮尖塔2的顶级玩家，擅长静默猎手的战略分析。"},
            {"role": "user", "content": prompt}
        ]
        return self._call_api(messages, max_tokens=2000)

    def _rule_based_combat_analysis(self, state: dict, recommendation: dict) -> str:
        """无LLM时的规则分析"""
        lines = ["【规则分析（未配置LLM API Key）】"]

        hp = state.get("hp", 0)
        max_hp = state.get("max_hp", 70)
        enemies = state.get("enemies", [])
        total_incoming = sum(e.get("intent_damage", 0) for e in enemies)
        block = state.get("block", 0)

        if hp < max_hp * 0.3:
            lines.append("⚠️ 血量危险（低于30%），优先防御或快速击杀")
        elif total_incoming > block + 15:
            lines.append(f"⚠️  incoming伤害{total_incoming}超过格挡{block}+15，需要补防御")
        else:
            lines.append("✅ 血量和格挡状态良好")

        if recommendation.get("best"):
            lines.append(f"AI推荐: {recommendation['best']['label']}")
            lines.append(f"理由: {recommendation.get('reason', '')}")

        return "\n".join(lines)

    def _rule_based_run_analysis(self, run_data: dict) -> str:
        """无LLM时的对局规则分析"""
        from advisor.analysis import analyze_run, generate_replay_narrative
        analysis = analyze_run(run_data)
        narrative = generate_replay_narrative(run_data)

        lines = [narrative, "", "【改进建议】"]
        for s in analysis["suggestions"]:
            lines.append(f"- {s['title']}: {s['content']}")

        return "\n".join(lines)


_llm_instance = None


def get_llm() -> LLMClient:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMClient()
    return _llm_instance
