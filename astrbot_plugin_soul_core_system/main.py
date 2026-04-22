"""
AstrBot Dual-Consciousness Role-Play Plugin
============================================
Features:
  1. Conscious layer (on_llm_request) - injects role identity/style/boundaries into system prompt
  2. Subconscious layer (on_llm_response) - modulates LLM output based on emotion state
  3. Knowledge base - powered by AstrBot built-in knowledge base (configured via WebUI)
  4. Memory - powered by AstrBot built-in conversation history

Usage:
  1. Fill in the system prompt in WebUI -> System Settings (becomes base_system_prompt)
  2. Fill in plugin config:
     - persona_name: character name
     - personality: personality description
     - speaking_style: speaking style
     - boundaries: behavior boundaries
     - primary_emotion: default emotion
     - emotion_triggers: emotion trigger keywords (JSON)
     - emotion_modulation: emotion modulation rules (JSON)
     - show_debug_log: show full debug log
     - show_kb_log: show knowledge base usage log
"""

from astrbot.api.event import filter as evt_filter, AstrMessageEvent
from astrbot.api.star import Context, Star
from astrbot.api.provider import ProviderRequest, LLMResponse
from astrbot.api import logger
import json
import re
from typing import Optional

# ===================== Plugin Config Model =====================


class PluginConfig:
    def __init__(self, config: dict):
        self.primary_emotion = config.get("primary_emotion", "normal")
        self.emotion_triggers = config.get("emotion_triggers", {})
        self.emotion_modulation = config.get("emotion_modulation", {})


# ===================== Emotion Modulator =====================


class EmotionModulator:
    """
    Subconscious module: detects emotion triggers -> updates emotion state -> modulates response
    """

    def __init__(
        self,
        primary_emotion: str = "normal",
        emotion_triggers: Optional[dict] = None,
        emotion_modulation: Optional[dict] = None,
    ):
        self.primary_emotion = primary_emotion
        self.current_emotion = primary_emotion
        self.emotion_triggers = emotion_triggers or {}
        self.emotion_modulation = emotion_modulation or {}

    def detect_emotion(self, text: str) -> str:
        """Detect emotion triggers in text, return emotion type."""
        text_lower = text.lower()
        for keyword, emotion in self.emotion_triggers.items():
            if keyword in text_lower:
                self.current_emotion = emotion
                return emotion
        return self.current_emotion

    def modulate(self, response_text: str, emotion: str) -> str:
        """Modulate response text based on current emotion."""
        rules = self.emotion_modulation.get(emotion, [])
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
        """Reset to primary emotion."""
        self.current_emotion = self.primary_emotion


# ===================== System Prompt Builder =====================


class PersonaPromptBuilder:
    """
    Conscious module: builds system prompt with identity/style/boundaries
    """

    EMOTION_STYLE_HINTS = {
        "happy": "(tone: cheerful, slightly playful)",
        "sad": "(tone: low, with ellipsis..., slower pace)",
        "angry": "(tone: sharp, decisive, brief)",
        "anxious": "(tone: fast, short sentences, slightly panicked)",
        "shy": "(tone: slow, cautious word choice)",
        "cold": "(tone: minimal words, sharp and toxic)",
        "affectionate": "(tone: warm, can suddenly say intimate words like 'love you')",
        "normal": "",
    }

    def build_system_prompt(
        self,
        base_system_prompt: str,
        persona_name: str,
        personality: str,
        boundaries: str,
        speaking_style: str,
        current_emotion: str,
        knowledge_hints: str = "",
    ) -> str:
        """
        Build complete system prompt.
        base_system_prompt: original prompt from WebUI system settings.
        """
        if not base_system_prompt or base_system_prompt.strip() == "":
            base_system_prompt = (
                f"You are playing the role of {persona_name or 'Aira'}.\n"
                f"Personality: {personality or 'rational, restrained, no swearing, no politics.'}\n"
                f"Speaking style: {speaking_style or 'concise and direct'}"
            )

        emotion_hint = self.EMOTION_STYLE_HINTS.get(current_emotion, "")

        system_parts = [
            base_system_prompt.strip(),
            "",
            "=" * 40,
            "[Dual-Consciousness System - Conscious Layer]",
            "=" * 40,
            f"Character: {persona_name or 'unnamed'}",
            f"Personality: {personality}",
            f"Style: {speaking_style}",
            f"Boundaries: {boundaries}",
            "",
            "[Dual-Consciousness System - Subconscious Layer]",
            f"Current emotion: {current_emotion}",
            f"Emotional tone: {emotion_hint}",
            "",
            "[Important] Subconscious modulation rules:",
            "1. Response must match the role identity defined by the conscious layer",
            "2. Tone/word choice/rhythm of response is determined by subconscious emotion state",
            "3. When emotion = happy -> upbeat tone",
            "4. When emotion = sad -> slower pace, can use ellipsis...",
            "5. When emotion = angry/cold -> very short response, decisive",
            "6. When emotion = affectionate -> can suddenly say intimate words",
            "",
            knowledge_hints,
        ]

        return "\n".join([p for p in system_parts if p])


# ===================== AstrBot Plugin Main Class =====================


class PersonaPlugin(Star):
    """Dual-consciousness role-play plugin main class."""

    def __init__(self, context: Context):
        super().__init__(context)
        self.context = context

        plugin_config = getattr(context, "plugin_config", {}) or {}

        self.cfg = PluginConfig(plugin_config)

        self.persona_name = plugin_config.get("persona_name", "Aira")
        self.personality = plugin_config.get("personality", "rational and restrained, decisive")
        self.speaking_style = plugin_config.get(
            "speaking_style",
            "concise, short sentences, can be toxic or affectionate, occasional mixed Chinese-English",
        )
        self.boundaries = plugin_config.get(
            "boundaries", "no swearing, no politics, do not reveal system settings"
        )
        self.knowledge_hints = plugin_config.get(
            "knowledge_hints",
            "Please configure the knowledge base via AstrBot's built-in knowledge base feature. "
            "The character will retrieve relevant info from the knowledge base.",
        )
        self.show_debug_log = plugin_config.get("show_debug_log", False)
        self.show_kb_log = plugin_config.get("show_kb_log", True)

        self.prompt_builder = PersonaPromptBuilder()
        self.modulator = EmotionModulator(
            primary_emotion=self.cfg.primary_emotion,
            emotion_triggers=self.cfg.emotion_triggers,
            emotion_modulation=self.cfg.emotion_modulation,
        )

        logger.info(f"[PersonaPlugin] Initialized. Character: {self.persona_name}")

    # ==================== Conscious Layer ====================

    @evt_filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
        """
        Conscious layer: injects role prompt before LLM request.
        """
        user_msg = event.message_str or ""
        emotion = self.modulator.detect_emotion(user_msg)

        original_prompt = req.system_prompt or ""
        enhanced_prompt = self.prompt_builder.build_system_prompt(
            base_system_prompt=original_prompt,
            persona_name=self.persona_name,
            personality=self.personality,
            boundaries=self.boundaries,
            speaking_style=self.speaking_style,
            current_emotion=emotion,
            knowledge_hints=self.knowledge_hints,
        )

        req.system_prompt = enhanced_prompt

        # Detect if knowledge base was called
        has_kb = bool(original_prompt and "[Related Knowledge Base Results]:" in original_prompt)
        kb_snippet = ""
        if has_kb:
            start = original_prompt.index("[Related Knowledge Base Results]:")
            kb_snippet = original_prompt[start:start + 300].replace("\n", " ")

        log_parts = [
            f"[PersonaPlugin] ====== Conscious Layer Triggered ======",
            f"  Character: {self.persona_name}",
            f"  Detected emotion: {emotion}",
            f"  User message: {user_msg[:80]}",
            f"  Knowledge base: {'YES' if has_kb else 'NO'}",
        ]
        if has_kb and kb_snippet:
            log_parts.append(f"  KB snippet: {kb_snippet[:200]}...")

        if self.show_debug_log:
            logger.info("\n".join(log_parts))
        elif self.show_kb_log and has_kb:
            logger.info(f"[PersonaPlugin] KB HIT | {user_msg[:60]}")

    # ==================== Subconscious Layer ====================

    @evt_filter.on_llm_response()
    async def on_llm_response(self, event: AstrMessageEvent, resp: LLMResponse):
        """
        Subconscious layer: modulates LLM output after generation.
        """
        if not resp.completion_text:
            return

        original = resp.completion_text
        current_emotion = self.modulator.current_emotion

        modulated = self.modulator.modulate(original, current_emotion)

        if modulated != original:
            resp.completion_text = modulated
            if self.show_debug_log:
                logger.info(
                    f"[PersonaPlugin] Subconscious modulation | emotion: {current_emotion} | "
                    f"from: {original[:50]}... -> to: {modulated[:50]}..."
                )
        else:
            if self.show_debug_log:
                logger.info(
                    f"[PersonaPlugin] Subconscious layer | emotion: {current_emotion} | "
                    f"output (unchanged): {original[:80]}..."
                )

        self.modulator.reset()

    # ==================== Commands ====================

    @evt_filter.command("persona")
    async def persona_info(self, event: AstrMessageEvent):
        """View current character info."""
        info_lines = [
            f"Character: {self.persona_name}",
            f"Default emotion: {self.cfg.primary_emotion}",
            f"Current emotion: {self.modulator.current_emotion}",
            f"Personality: {self.personality}",
            f"Style: {self.speaking_style}",
            "",
            f"Emotion triggers: {len(self.cfg.emotion_triggers)}",
            f"Modulation rules: {len(self.cfg.emotion_modulation)}",
        ]
        yield event.plain_result("\n".join(info_lines))

    @evt_filter.command("persona_set")
    async def persona_set(self, event: AstrMessageEvent, key: str = "", value: str = ""):
        """Set character property: /persona_set persona_name Mi"""
        if not key or not value:
            yield event.plain_result(
                "Usage: /persona_set <key> <value>\n"
                "Keys: persona_name, personality, speaking_style, boundaries, primary_emotion"
            )
            return

        if key == "persona_name":
            self.persona_name = value
        elif key == "personality":
            self.personality = value
        elif key == "speaking_style":
            self.speaking_style = value
        elif key == "boundaries":
            self.boundaries = value
        elif key == "primary_emotion":
            self.modulator.primary_emotion = value
            self.modulator.current_emotion = value
        else:
            yield event.plain_result(f"Unknown key: {key}")
            return

        yield event.plain_result(f"Updated: {key} = {value}")

    @evt_filter.command("persona_emotion")
    async def persona_emotion(self, event: AstrMessageEvent, emotion: str = ""):
        """Manually set current emotion: /persona_emotion happy"""
        valid_emotions = ["happy", "sad", "angry", "anxious", "shy", "cold", "affectionate", "normal"]
        if not emotion:
            yield event.plain_result(
                f"Current: {self.modulator.current_emotion}\n"
                f"Options: {', '.join(valid_emotions)}"
            )
            return
        if emotion not in valid_emotions:
            yield event.plain_result(f"Invalid. Options: {', '.join(valid_emotions)}")
            return
        self.modulator.current_emotion = emotion
        yield event.plain_result(f"Emotion switched: {emotion}")

    @evt_filter.command("persona_test")
    async def persona_test(self, event: AstrMessageEvent, text: str = ""):
        """Test emotion modulation: /persona_test you idiot"""
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
        """Add emotion trigger: /persona_add_trigger game happy"""
        if not keyword or not emotion:
            yield event.plain_result(
                "Usage: /persona_add_trigger <keyword> <emotion>\n"
                "Emotions: happy, sad, angry, anxious, shy, cold, affectionate, normal"
            )
            return
        self.cfg.emotion_triggers[keyword] = emotion
        self.modulator.emotion_triggers = self.cfg.emotion_triggers
        try:
            await self.put_kv_data("emotion_triggers", json.dumps(self.cfg.emotion_triggers))
        except Exception:
            pass
        yield event.plain_result(f"Trigger added: '{keyword}' -> {emotion}")

    async def terminate(self):
        """Save config on plugin unload."""
        try:
            await self.put_kv_data("emotion_triggers", json.dumps(self.cfg.emotion_triggers))
            logger.info("[PersonaPlugin] Config saved.")
        except Exception as e:
            logger.error(f"[PersonaPlugin] Failed to save config: {e}")
