"""
HospitalOps AI — LLM Provider Abstraction & Implementations (Chunk 4.4).

Provides a decoupled interface for language model completion:
- LLMProvider: Abstract base class for model providers.
- NullLLMProvider: Default unconfigured provider communicating generation unavailability.
- MockLLMProvider: Deterministic provider for testing, adversarial validation, and CI.
- OpenAICompatibleProvider: Generic HTTP client provider for local or remote OpenAI-compatible endpoints.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

import httpx

from app.models.base import HospitalOpsBaseModel

logger = logging.getLogger(__name__)


class LLMMessage(HospitalOpsBaseModel):
    """Chat message exchanged with language model provider."""

    role: str
    content: str


class LLMProvider(ABC):
    """Abstract interface for language model generation providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider implementation (e.g. 'openai_compatible', 'mock', 'null')."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier of the model being called (e.g. 'gpt-4o-mini', 'mock-v1')."""

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_output_tokens: int = 1500,
    ) -> tuple[str, dict[str, int] | None, dict[str, Any]]:
        """
        Execute generation call against the model provider.

        Returns:
            (raw_text_content, token_usage_dict, extra_metadata_dict)

        Raises:
            RuntimeError: On provider failure or unconfigured state.
            TimeoutError: If the provider call exceeds configured timeout.
        """

    @abstractmethod
    async def check_health(self) -> bool:
        """Verify provider availability and connectivity."""


class NullLLMProvider(LLMProvider):
    """Null provider used when no model provider is configured or generation is disabled."""

    def __init__(self, reason: str = "LLM provider is not configured.") -> None:
        self._reason = reason

    @property
    def provider_name(self) -> str:
        return "null"

    @property
    def model_name(self) -> str:
        return "none"

    async def generate(
        self,
        messages: list[LLMMessage],
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_output_tokens: int = 1500,
    ) -> tuple[str, dict[str, int] | None, dict[str, Any]]:
        raise RuntimeError(self._reason)

    async def check_health(self) -> bool:
        return False


class MockLLMProvider(LLMProvider):
    """
    Deterministic mock provider for unit tests, security audits, and offline validation.
    Supports preset responses, custom handlers, and simulated failure injection.
    """

    def __init__(
        self,
        preset_response: str | None = None,
        preset_usage: dict[str, int] | None = None,
        should_fail: bool = False,
        fail_exception: Exception | None = None,
        custom_handler: Callable[[list[LLMMessage]], str] | None = None,
        provider_name: str = "mock",
        model_name: str = "mock-model-v1",
    ) -> None:
        self._preset_response = preset_response
        self._preset_usage = preset_usage or {"prompt_tokens": 120, "completion_tokens": 45}
        self._should_fail = should_fail
        self._fail_exception = fail_exception
        self._custom_handler = custom_handler
        self._provider_name = provider_name
        self._model_name = model_name
        self.call_history: list[dict[str, Any]] = []

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def set_preset_response(self, text: str) -> None:
        """Update preset response on the fly."""
        self._preset_response = text

    def set_should_fail(self, fail: bool, exc: Exception | None = None) -> None:
        """Toggle simulated failure."""
        self._should_fail = fail
        self._fail_exception = exc

    async def generate(
        self,
        messages: list[LLMMessage],
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_output_tokens: int = 1500,
    ) -> tuple[str, dict[str, int] | None, dict[str, Any]]:
        self.call_history.append(
            {
                "messages": messages,
                "response_schema": response_schema,
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "timestamp": time.time(),
            }
        )

        if self._should_fail:
            if self._fail_exception:
                raise self._fail_exception
            raise RuntimeError("Simulated mock provider failure")

        if self._custom_handler:
            text = self._custom_handler(messages)
            return text, self._preset_usage, {"mock": True}

        if self._preset_response is not None:
            return self._preset_response, self._preset_usage, {"mock": True}

        # Default fallback JSON output
        default_json = (
            '{\n'
            '  "answer": "This is a deterministic mock answer grounded in hospital reference policy. [S1]",\n'
            '  "answer_type": "GROUNDED",\n'
            '  "insufficient_evidence": false,\n'
            '  "limitations": [],\n'
            '  "follow_up_questions": ["What is the escalation timeline?"]\n'
            '}'
        )
        return default_json, self._preset_usage, {"mock": True}

    async def check_health(self) -> bool:
        return not self._should_fail


class OpenAICompatibleProvider(LLMProvider):
    """
    HTTP client provider for OpenAI-compatible completions endpoints
    (local Ollama, vLLM, LMStudio, or remote endpoints).
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model_name: str = "gpt-4o-mini",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self._api_key = api_key or ""
        self._model_name = model_name
        self._timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(
        self,
        messages: list[LLMMessage],
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        max_output_tokens: int = 1500,
    ) -> tuple[str, dict[str, int] | None, dict[str, Any]]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload: dict[str, Any] = {
            "model": self._model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_output_tokens,
            "response_format": {"type": "json_object"},
        }

        url = f"{self._base_url}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                start_t = time.perf_counter()
                resp = await client.post(url, json=payload, headers=headers)
                latency_ms = (time.perf_counter() - start_t) * 1000

                if resp.status_code != 200:
                    logger.error(
                        "LLM provider returned error status | provider=%s code=%d",
                        self.provider_name,
                        resp.status_code,
                    )
                    raise RuntimeError(f"Provider returned error status {resp.status_code}: {resp.text[:200]}")

                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    raise RuntimeError("Provider returned empty choices array.")

                content = choices[0].get("message", {}).get("content", "")
                usage = data.get("usage")

                meta = {
                    "latency_ms": latency_ms,
                    "finish_reason": choices[0].get("finish_reason"),
                }
                return content, usage, meta

        except httpx.TimeoutException as exc:
            logger.error("LLM provider request timed out | provider=%s timeout=%.1fs", self.provider_name, self._timeout_seconds)
            raise TimeoutError(f"LLM provider timed out after {self._timeout_seconds}s") from exc
        except Exception as exc:
            if isinstance(exc, RuntimeError | TimeoutError):
                raise
            logger.error("LLM provider connection failed | provider=%s err=%s", self.provider_name, type(exc).__name__)
            raise RuntimeError(f"LLM provider communication failed: {type(exc).__name__}") from exc

    async def check_health(self) -> bool:
        """Verify endpoint connectivity."""
        if not self._base_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {}
                if self._api_key:
                    headers["Authorization"] = f"Bearer {self._api_key}"
                resp = await client.get(f"{self._base_url}/models", headers=headers)
                return resp.status_code in (200, 401)
        except Exception:
            return False
