"""
AstrBot Dual-Consciousness Role-Play Plugin (Refactored)
=====================================================
Features:
  1. Conscious layer (on_llm_request) - injects role identity/style/boundaries into system prompt
  2. Subconscious layer (on_llm_response) - modulates LLM output based on emotion state
  3. Multi-role support - switch between different characters
  4. Model separation - different models for conscious/subconscious layers
  5. Knowledge base - powered by AstrBot built-in knowledge base
"""

from astrbot.api.event import filter as evt_filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api.provider import ProviderRequest, LLMResponse
from astrbot.api import logger
import json
import re
from typing import Optional, Dict

# ===================== Role Config Model =====================


class RoleConfig:
    """单个角色配置"""
    def __init__(self, config_dict: dict):
        self.name = config_dict.get("name", "")
        self.conscious_prompt = config_dict.get("conscious_prompt", "")
        self.subconscious_prompt = config_dict.get("subconscious_prompt", "")
        self.personality = config_dict.get("personality", "")
        self.style = config_dict.get("style", "")
        self.boundaries = config_dict.get("boundaries", "")


class PluginConfig:
    """完整插件配置"""
    def __init__(self, config: dict):
        # 角色配置
        self.roles = {
            k: RoleConfig(v)
            for k, v in config.get("roles", {}).items()
        }
        self.active_role = config.get("active_role", "default")

        # 模型配置
        self.conscious_model = config.get("conscious_model", "")
        self.subconscious_model = config.get("subconscious_model", "")

        # 情绪系统
        self.primary_emotion = config.get("primary_emotion", "normal")
        self.emotion_triggers = config.get("emotion_triggers", {})
        self.emotion_modulation = config.get("emotion_modulation", {})

        # 调制方法
        self.modulation_method = config.get("modulation_method", "regex")

        # 调试
        self.show_debug_log = config.get("show_debug_log", True)
        self.show_kb_log = config.get("show_kb_log", True)

    @property
    def current_role(self) -> Optional[RoleConfig]:
        """获取当前激活的角色"""
        return self.roles.get(self.active_role, self.roles.get("default"))


# ===================== Emotion Modulator =====================


class EmotionModulator:
    """
    潜意识模块：支持多种调制方式
    - regex: 正则表达式替换
    - llm: 使用独立 LLM 调制（需要实现）
    """

    def __init__(self, config: PluginConfig, astrbot_context: Context):
        self.config = config
        self.context = astrbot_context
        self.current_emotion = config.primary_emotion

    def detect_emotion(self, text: str) -> str:
        """检测情绪触发词，返回情绪类型"""
        text_lower = text.lower()
        for keyword, emotion in self.config.emotion_triggers.items():
            if keyword in text_lower:
                self.current_emotion = emotion
                return emotion
        return self.current_emotion

    def modulate(self, response_text: str, emotion: str) -> str:
        """调制响应文本"""
        if self.config.modulation_method == "llm":
            # TODO: 实现 LLM 调制
            # 目前先回退到 regex
            return self._regex_modulation(response_text, emotion)
        else:
            return self._regex_modulation(response_text, emotion)

    def _regex_modulation(self, response_text: str, emotion: str) -> str:
        """正则表达式调制（原有逻辑）"""
        rules = self.config.emotion_modulation.get(emotion, [])
        modulated = response_text

        for rule in rules:
            pattern = rule.get("pattern", "")
            replacement = rule.get("replacement", "")
            emotion_tag = rule.get("emotion_tag", False)

            if emotion_tag:
                modulated = f"[{emotion}]{modulated}[/{emotion}]"
            elif pattern and replacement:
                try:
                    modulated = re.sub(pattern, replacement, modulated)
                except re.error:
                    pass

        return modulated

    def reset(self):
        """重置到默认情绪"""
        self.current_emotion = self.config.primary_emotion


# ===================== System Prompt Builder =====================


class PersonaPromptBuilder:
    """主意识 prompt 构建器"""

    EMOTION_STYLE_HINTS = {
        "happy": "(tone: cheerful, slightly playful)",
        "sad": "(tone: low, with ellipsis..., slower pace)",
        "angry": "(tone: sharp, decisive, brief)",
        "anxious": "(tone: fast, short sentences, slightly panicked, more ellipsis)",
        "shy": "(tone: slow, cautious word choice)",
        "cold": "(tone: minimal words, sharp and toxic)",
        "affectionate": "(tone: warm, can suddenly say intimate words like 'love you')",
        "normal": "(tone: natural, conversational)",
        "trust": "(tone: relaxed, can share more personal information)",
        "fear": "(tone: brief, alert, may use ! and ?, fragmented)",
        "calm": "(tone: normal, standard punctuation)",
    }

    def __init__(self, config: PluginConfig):
        self.config = config

    def build_system_prompt(
        self,
        base_system_prompt: str,
        current_emotion: str
    ) -> str:
        """构建完整的系统 prompt"""
        role = self.config.current_role

        # 使用角色的主意识 prompt
        if role and role.conscious_prompt:
            prompt_template = role.conscious_prompt
        elif base_system_prompt:
            prompt_template = base_system_prompt
        else:
            prompt_template = self._default_prompt(role)

        # 添加情绪提示
        emotion_hint = self.EMOTION_STYLE_HINTS.get(current_emotion, "")

        # 构建最终 prompt
        system_prompt = f"""
{prompt_template}

---
[Current Emotion State]
Emotion: {current_emotion}
Emotional tone: {emotion_hint}

[Instructions]
- Maintain your identity as defined above
- Your tone/word choice should reflect the current emotion
- Do not break character boundaries
"""

        return system_prompt.strip()

    def _default_prompt(self, role: Optional[RoleConfig]) -> str:
        """默认角色 prompt"""
        return f"""
# Identity
Name: {role.name if role else "Unknown"}

# Personality
{role.personality if role else "Rational, restrained"}

# Speaking Style
{role.style if role else "Concise and direct"}

# Boundaries
{role.boundaries if role else "No swearing, no politics"}

You are playing this character. Stay in character at all times.
"""


# ===================== AstrBot Plugin Main Class =====================


class PersonaPlugin(Star):
    """通用双意识角色扮演插件（重构版）"""

    def __init__(self, context: Context):
        super().__init__(context)
        self.context = context

        # 加载配置
        plugin_config = getattr(context, "plugin_config", {}) or {}
        self.cfg = PluginConfig(plugin_config)

        # 初始化组件
        self.prompt_builder = PersonaPromptBuilder(self.cfg)
        self.modulator = EmotionModulator(self.cfg, context)

        logger.info(f"[PersonaPlugin] Initialized with {len(self.cfg.roles)} roles")
        logger.info(f"[PersonaPlugin] Active role: {self.cfg.active_role}")
        logger.info(f"[PersonaPlugin] Conscious model: {self.cfg.conscious_model or '(default)'}")
        logger.info(f"[PersonaPlugin] Subconscious model: {self.cfg.subconscious_model or '(default)'}")

    # ==================== Conscious Layer ====================

    @evt_filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
        """主意识层：构建并注入系统 prompt"""
        user_msg = event.message_str or ""

        # 检测情绪
        emotion = self.modulator.detect_emotion(user_msg)
        self.modulator.current_emotion = emotion

        # 构建系统 prompt
        original_prompt = req.system_prompt or ""
        enhanced_prompt = self.prompt_builder.build_system_prompt(
            base_system_prompt=original_prompt,
            current_emotion=emotion
        )

        # 注入 prompt
        req.system_prompt = enhanced_prompt

        # TODO: 尝试设置模型（需要验证 ProviderRequest 是否支持）
        if self.cfg.conscious_model and hasattr(req, 'model'):
            req.model = self.cfg.conscious_model
            if self.cfg.show_debug_log:
                logger.info(f"[Conscious Layer] Model override: {self.cfg.conscious_model}")

        # 检测知识库
        has_kb = bool(original_prompt and "[Related Knowledge Base Results]:" in original_prompt)
        kb_snippet = ""
        if has_kb:
            start = original_prompt.index("[Related Knowledge Base Results]:")
            kb_snippet = original_prompt[start:start + 300].replace("\n", " ")

        log_parts = [
            f"[PersonaPlugin] ====== Conscious Layer Triggered ======",
            f"  Role: {self.cfg.current_role.name if self.cfg.current_role else 'None'}",
            f"  Emotion: {emotion}",
            f"  User message: {user_msg[:80]}",
            f"  Knowledge base: {'YES' if has_kb else 'NO'}",
        ]
        if has_kb and kb_snippet:
            log_parts.append(f"  KB snippet: {kb_snippet[:200]}...")

        if self.cfg.show_debug_log:
            logger.info("\n".join(log_parts))
        elif self.cfg.show_kb_log and has_kb:
            logger.info(f"[PersonaPlugin] KB HIT | {user_msg[:60]}")

    # ==================== Subconscious Layer ====================

    @evt_filter.on_llm_response()
    async def on_llm_response(self, event: AstrMessageEvent, resp: LLMResponse):
        """潜意识层：调制 LLM 输出"""
        if not resp.completion_text:
            return

        original = resp.completion_text
        current_emotion = self.modulator.current_emotion

        # 调制响应
        modulated = self.modulator.modulate(original, current_emotion)

        if modulated != original:
            resp.completion_text = modulated
            if self.cfg.show_debug_log:
                logger.info(
                    f"[PersonaPlugin] Subconscious modulation | emotion: {current_emotion} | "
                    f"from: {original[:50]}... -> to: {modulated[:50]}..."
                )
        else:
            if self.cfg.show_debug_log:
                logger.info(
                    f"[PersonaPlugin] Subconscious layer | emotion: {current_emotion} | "
                    f"output (unchanged): {original[:80]}..."
                )

        # 重置情绪状态（可选）
        self.modulator.reset()

    # ==================== Role Management Commands ====================

    @evt_filter.command("role")
    async def role_list(self, event: AstrMessageEvent):
        """查看所有角色"""
        roles = list(self.cfg.roles.keys())
        info = [
            f"Available roles: {', '.join(roles)}",
            f"Active: {self.cfg.active_role}"
        ]
        yield event.plain_result("\n".join(info))

    @evt_filter.command("role_switch")
    async def role_switch(self, event: AstrMessageEvent, role_name: str = ""):
        """切换角色"""
        if not role_name:
            yield event.plain_result("Usage: /role_switch <role_name>")
            return

        if role_name not in self.cfg.roles:
            yield event.plain_result(f"Role not found: {role_name}")
            return

        self.cfg.active_role = role_name
        role = self.cfg.current_role
        yield event.plain_result(
            f"Switched to role: {role_name}\n"
            f"Name: {role.name}\n"
            f"Personality: {role.personality}"
        )

    @evt_filter.command("role_add")
    async def role_add(self, event: AstrMessageEvent, name: str = ""):
        """添加新角色"""
        if not name:
            yield event.plain_result("Usage: /role_add <role_name>")
            return

        # 创建默认角色配置
        new_role = RoleConfig({
            "name": name,
            "conscious_prompt": f"# Identity for {name}\n",
            "subconscious_prompt": "",
            "personality": "",
            "style": "",
            "boundaries": ""
        })

        self.cfg.roles[name] = new_role
        try:
            # 保存到持久化存储
            roles_data = {k: {
                "name": v.name,
                "conscious_prompt": v.conscious_prompt,
                "subconscious_prompt": v.subconscious_prompt,
                "personality": v.personality,
                "style": v.style,
                "boundaries": v.boundaries
            } for k, v in self.cfg.roles.items()}
            await self.put_kv_data("roles", json.dumps(roles_data))
            logger.info(f"[PersonaPlugin] Role added: {name}")
        except Exception as e:
            logger.error(f"[PersonaPlugin] Failed to save role: {e}")

        yield event.plain_result(
            f"Role added: {name}\n"
            f"Please configure conscious_prompt via WebUI"
        )

    # ==================== Emotion Commands ====================

    @evt_filter.command("persona_emotion")
    async def persona_emotion(self, event: AstrMessageEvent, emotion: str = ""):
        """查看或切换当前情绪"""
        valid_emotions = ["happy", "sad", "angry", "anxious", "shy", "cold", "affectionate", "normal", "trust", "fear", "calm"]

        if not emotion:
            yield event.plain_result(
                f"Current emotion: {self.modulator.current_emotion}\n"
                f"Available: {', '.join(valid_emotions)}"
            )
            return

        if emotion not in valid_emotions:
            yield event.plain_result(f"Invalid emotion. Available: {', '.join(valid_emotions)}")
            return

        self.modulator.current_emotion = emotion
        yield event.plain_result(f"Emotion switched: {emotion}")

    @evt_filter.command("persona_test")
    async def persona_test(self, event: AstrMessageEvent, text: str = ""):
        """测试情绪调制效果"""
        if not text:
            yield event.plain_result("Usage: /persona_test <text>")
            return

        emotion = self.modulator.detect_emotion(text)
        modulated = self.modulator.modulate(f"[TEST] {text}", emotion)
        yield event.plain_result(
            f"Input: {text}\n"
            f"Detected emotion: {emotion}\n"
            f"Modulated: {modulated}"
        )

    @evt_filter.command("persona_add_trigger")
    async def persona_add_trigger(self, event: AstrMessageEvent, keyword: str = "", emotion: str = ""):
        """添加情绪触发词"""
        if not keyword or not emotion:
            yield event.plain_result(
                "Usage: /persona_add_trigger <keyword> <emotion>\n"
                "Emotions: happy, sad, angry, anxious, shy, cold, affectionate, normal, trust, fear, calm"
            )
            return

        self.cfg.emotion_triggers[keyword] = emotion
        self.modulator.emotion_triggers = self.cfg.emotion_triggers

        try:
            await self.put_kv_data("emotion_triggers", json.dumps(self.cfg.emotion_triggers))
            logger.info(f"[PersonaPlugin] Trigger added: '{keyword}' -> {emotion}")
        except Exception as e:
            logger.error(f"[PersonaPlugin] Failed to save trigger: {e}")

        yield event.plain_result(f"Trigger added: '{keyword}' -> {emotion}")

    # ==================== Info Command ====================

    @evt_filter.command("persona")
    async def persona_info(self, event: AstrMessageEvent):
        """查看当前角色信息"""
        role = self.cfg.current_role
        if not role:
            yield event.plain_result("No active role configured.")
            return

        info_lines = [
            f"=== Current Role ====",
            f"Name: {role.name}",
            f"Personality: {role.personality}",
            f"Style: {role.style}",
            f"Boundaries: {role.boundaries}",
            "",
            f"=== Emotion System ====",
            f"Default emotion: {self.cfg.primary_emotion}",
            f"Current emotion: {self.modulator.current_emotion}",
            f"Triggers: {len(self.cfg.emotion_triggers)}",
            f"Modulation rules: {len(self.cfg.emotion_modulation)}",
            "",
            f"=== Model Config ====",
            f"Conscious model: {self.cfg.conscious_model or '(default)'}",
            f"Subconscious model: {self.cfg.subconscious_model or '(default)'}",
            f"Modulation method: {self.cfg.modulation_method}",
        ]
        yield event.plain_result("\n".join(info_lines))

    async def terminate(self):
        """保存配置"""
        try:
            await self.put_kv_data("emotion_triggers", json.dumps(self.cfg.emotion_triggers))
            roles_data = {k: {
                "name": v.name,
                "conscious_prompt": v.conscious_prompt,
                "subconscious_prompt": v.subconscious_prompt,
                "personality": v.personality,
                "style": v.style,
                "boundaries": v.boundaries
            } for k, v in self.cfg.roles.items()}
            await self.put_kv_data("roles", json.dumps(roles_data))
            logger.info("[PersonaPlugin] Config saved.")
        except Exception as e:
            logger.error(f"[PersonaPlugin] Failed to save config: {e}")
