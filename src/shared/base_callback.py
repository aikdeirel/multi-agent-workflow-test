import logging
from typing import Optional
from langchain.callbacks.base import BaseCallbackHandler


class BaseOperatorCallback(BaseCallbackHandler):
    """Base callback handler for operator agents."""

    def __init__(self, operator_name: str, emoji: str = "🤖"):
        """
        Initialize base callback with operator-specific details.
        
        Args:
            operator_name: Name of the operator (e.g., "math", "weather", "datetime")
            emoji: Emoji to use in log messages
        """
        super().__init__()
        self.operator_name = operator_name.upper()
        self.emoji = emoji
        self.logger = logging.getLogger(f"operators.{operator_name.lower()}_internal")

    def on_agent_action(self, action, **kwargs):
        """Called when agent takes an action."""
        self.logger.info(f"{self.emoji} {self.operator_name} AGENT ACTION: {action.tool}")
        self.logger.info(f"📋 {self.operator_name} AGENT PARAMETERS: {action.tool_input}")

    def on_tool_end(self, output, **kwargs):
        """Called when tool ends."""
        self.logger.info(f"🔧 {self.operator_name} TOOL RESPONSE: {str(output)[:200]}...")

    def on_text(self, text, **kwargs):
        """Called on agent text - captures thinking."""
        if text and text.strip():
            text_stripped = text.strip()
            if text_stripped.startswith("Thought:"):
                thinking = text_stripped.replace("Thought:", "").strip()
                self.logger.info(f"💭 {self.operator_name} AGENT THINKING: {thinking}")
            elif "I need" in text_stripped or "I should" in text_stripped:
                self.logger.info(f"🤔 {self.operator_name} AGENT REASONING: {text_stripped}")

    def on_llm_start(self, serialized, prompts, **kwargs):
        """Called when agent LLM starts."""
        if prompts and len(prompts) > 0:
            for i, prompt in enumerate(prompts):
                # Log a truncated version of the prompt sent to operator
                if len(str(prompt)) > 300:
                    truncated = (
                        str(prompt)[:150] + "...[TRUNCATED]..." + str(prompt)[-100:]
                    )
                    self.logger.info(f"📝 {self.operator_name} AGENT PROMPT #{i+1}: {truncated}")
                else:
                    self.logger.info(f"📝 {self.operator_name} AGENT PROMPT #{i+1}: {prompt}")


class MathOperatorCallback(BaseOperatorCallback):
    """Callback handler for math operator."""
    
    def __init__(self):
        super().__init__("math", "🧮")


class WeatherOperatorCallback(BaseOperatorCallback):
    """Callback handler for weather operator."""
    
    def __init__(self):
        super().__init__("weather", "🌤️")


class DateTimeOperatorCallback(BaseOperatorCallback):
    """Callback handler for datetime operator."""
    
    def __init__(self):
        super().__init__("datetime", "📅")