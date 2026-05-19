# Mistral AI LLM runtime
"""
ClientIQ - Mistral AI LLM Client
Wraps Mistral's hosted chat completions API with retry logic and a
small interface used by the agents.
"""

from typing import List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.utils.config import settings
from backend.utils.logger import logger


class MistralClient:
    """
    Client for Mistral AI's hosted chat completions API.

    Supports:
    - Single completion (complete)
    - Chat completion with system/user messages (chat)
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model = model or settings.mistral_model
        self.api_key = api_key or settings.mistral_api_key
        self.base_url = (base_url or settings.mistral_base_url).rstrip("/")
        self.timeout = 120.0

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def complete(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stop: Optional[List[str]] = None,
    ) -> str:
        """
        Single-turn completion.
        Returns the generated text string.
        """
        return self._chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def chat(
        self,
        system: str,
        user: str,
        history: Optional[List[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """
        Multi-turn chat completion.
        Builds message history in OpenAI-compatible format for Mistral.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user})

        return self._chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def _chat_completion(
        self,
        messages: List[dict],
        temperature: float,
        max_tokens: int,
        stop: Optional[List[str]] = None,
    ) -> str:
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY is not configured")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if stop:
            payload["stop"] = stop

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return self._extract_content(data)
        except httpx.TimeoutException:
            logger.warning("[Mistral] Request timed out after {}s", self.timeout)
            return "LLM response timed out. Please try again."
        except Exception as e:
            logger.error("[Mistral] Chat completion error: {}", e)
            raise

    def _extract_content(self, data: dict) -> str:
        choices = data.get("choices") or []
        if not choices:
            return ""

        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
            return "\n".join(text_parts).strip()

        return ""

    def health_check(self) -> bool:
        """Check if Mistral credentials can reach the hosted API."""
        if not self.api_key:
            return False

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    f"{self.base_url}/models",
                    headers=self._headers,
                )
                return response.status_code == 200
        except Exception:
            return False
