"""Shared LLM service used by GovCon agents."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import httpx

from govcon.utils.config import Settings, get_settings
from govcon.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ChatMessage:
    """Minimal chat message representation."""

    role: str
    content: str


class LLMService:
    """Lightweight abstraction around provider-specific LLM clients."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._openai_client = None
        self._anthropic_client = None
        self._http_client: httpx.AsyncClient | None = None

    def default_model(self, provider: str) -> str:
        """Return the default model for the selected provider."""
        provider = provider.lower()
        if provider == "openai":
            return self.settings.openai_model
        if provider == "anthropic":
            return self.settings.anthropic_model
        if provider == "ollama":
            return self.settings.ollama_model
        raise ValueError(f"Unsupported LLM provider: {provider}")

    def default_temperature(self, provider: str) -> float:
        """Return a sane default temperature for a provider."""
        provider = provider.lower()
        if provider in {"openai", "anthropic", "ollama"}:
            return self.settings.openai_temperature
        return self.settings.openai_temperature

    async def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        provider: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> str:
        """Send chat-style messages to the configured LLM."""
        if not messages:
            raise ValueError("At least one chat message is required.")

        provider_name = (provider or self.settings.default_llm_provider).lower()
        model_name = model or self.default_model(provider_name)
        if provider_name == "openai":
            temp = None
        elif temperature is not None:
            temp = temperature
        else:
            temp = self.default_temperature(provider_name)

        if provider_name == "openai":
            return await self._chat_openai(messages, model_name, temp, max_output_tokens)

        if provider_name == "anthropic":
            return await self._chat_anthropic(messages, model_name, temp, max_output_tokens)

        if provider_name == "ollama":
            return await self._chat_ollama(messages, model_name, temp)

        raise ValueError(f"Unsupported LLM provider: {provider_name}")

    async def _chat_openai(
        self,
        messages: Sequence[ChatMessage],
        model_name: str,
        temperature: float,
        max_output_tokens: int | None,
    ) -> str:
        """Call OpenAI Chat Completions API (standard, stable API)."""
        client = self._get_openai_client()

        # Convert messages to OpenAI format
        openai_messages = [
            {
                "role": msg.role,
                "content": msg.content,
            }
            for msg in messages
        ]

        # Build request parameters
        request_params = {
            "model": model_name,
            "messages": openai_messages,
        }

        # Use max_completion_tokens for newer models (gpt-4+, gpt-5+, o1, o3)
        # and max_tokens for older models (gpt-3.5-turbo)
        if max_output_tokens is not None:
            # Use max_completion_tokens for GPT-4+, GPT-5+, and O-series models
            if any(pattern in model_name for pattern in ["gpt-4", "gpt-5", "o1", "o3"]):
                request_params["max_completion_tokens"] = max_output_tokens
            else:
                request_params["max_tokens"] = max_output_tokens
        if temperature is not None:
            request_params["temperature"] = temperature

        # Call the standard Chat Completions API
        response = await client.chat.completions.create(**request_params)

        # Extract text from response - standard structure
        if response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            content = message.content or ""
            # Debug logging
            logger.debug(f"OpenAI response - model: {model_name}, content_length: {len(content)}, has_content: {bool(content)}")
            if not content:
                logger.warning(f"Empty response from OpenAI - model: {model_name}, finish_reason: {response.choices[0].finish_reason if response.choices else 'N/A'}")
            return content

        logger.warning(f"No choices in OpenAI response - model: {model_name}")
        return ""

    async def _chat_anthropic(
        self,
        messages: Sequence[ChatMessage],
        model_name: str,
        temperature: float,
        max_output_tokens: int | None,
    ) -> str:
        client = self._get_anthropic_client()
        system_prompt = ""
        content_messages = []
        for msg in messages:
            if msg.role == "system" and not system_prompt:
                system_prompt = msg.content
            else:
                content_messages.append({"role": msg.role, "content": msg.content})

        response = await client.messages.create(
            model=model_name,
            system=system_prompt or None,
            messages=content_messages,
            temperature=temperature,
            max_tokens=max_output_tokens or 1024,
        )
        text_blocks = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text_blocks.append(block.text)
        return "\n".join(text_blocks).strip()

    async def _chat_ollama(
        self,
        messages: Sequence[ChatMessage],
        model_name: str,
        temperature: float,
    ) -> str:
        client = await self._get_http_client()
        url = self.settings.ollama_host.rstrip("/") + "/api/chat"
        payload = {
            "model": model_name,
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            "stream": False,
            "options": {"temperature": temperature},
        }
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        message = data.get("message") or {}
        return message.get("content", "").strip()

    def _get_openai_client(self):
        if self._openai_client is None:
            from openai import AsyncOpenAI

            api_key = self.settings.openai_api_key
            if not api_key:
                raise RuntimeError("OpenAI provider selected but OPENAI_API_KEY is not configured.")
            self._openai_client = AsyncOpenAI(api_key=api_key)
        return self._openai_client

    def _get_anthropic_client(self):
        if self._anthropic_client is None:
            from anthropic import AsyncAnthropic

            api_key = self.settings.anthropic_api_key
            if not api_key:
                raise RuntimeError(
                    "Anthropic provider selected but ANTHROPIC_API_KEY is not configured."
                )
            self._anthropic_client = AsyncAnthropic(api_key=api_key)
        return self._anthropic_client

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        return self._http_client

    async def aclose(self) -> None:
        """Close any open HTTP clients (used in tests/shutdown)."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None


# Shared singleton for application use.
llm_service = LLMService()

__all__ = ["ChatMessage", "LLMService", "llm_service"]
