"""LLM client.

A thin, provider-agnostic wrapper. It holds a provider (Anthropic, Gemini, ...),
an api key, and a model, and dispatches calls to the provider. When it is not
configured, or a live call fails, it reports a clear reason and the runner falls
back to the analyzers' offline detectors.
"""
from __future__ import annotations

from typing import Any

from .providers import Provider, parse_json  # noqa: F401 (re-exported for tests)


class LLMClient:
    def __init__(self, provider: Provider | None, api_key: str | None, model: str):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.last_error: str | None = None
        self.configured = bool(provider and api_key)
        if not self.configured:
            self.last_error = "no active API key set"

    @property
    def live(self) -> bool:
        return self.configured

    @property
    def provider_name(self) -> str | None:
        return self.provider.name if self.provider else None

    def set_model(self, model: str) -> None:
        self.model = model

    def list_models(self) -> list[dict[str, str]]:
        if not self.configured:
            return []
        try:
            models = self.provider.list_models(self.api_key)
            self.last_error = None
            return models
        except Exception as exc:
            self.last_error = self.provider.explain(exc)
            return []

    def test(self) -> tuple[bool, str | None]:
        if not self.configured:
            return False, self.last_error or "client not configured"
        try:
            self.provider.test(self.api_key, self.model)
            self.last_error = None
            return True, None
        except Exception as exc:
            self.last_error = self.provider.explain(exc)
            return False, self.last_error

    def complete_json(self, system: str, user: str, max_tokens: int = 2000) -> Any:
        return self.provider.complete_json(self.api_key, self.model, system, user, max_tokens)

    def explain(self, exc: Exception) -> str:
        return self.provider.explain(exc) if self.provider else str(exc)
