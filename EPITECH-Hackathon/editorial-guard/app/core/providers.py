"""LLM providers.

One interface, several backends. Each key declares its provider, so an Anthropic
key talks to Anthropic and a Gemini key talks to Google. Adding another provider
(OpenAI, etc.) means writing one more class and registering it, the same seam idea
as the analyzers.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any


def parse_json(text: str) -> Any:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
    return json.loads(text)


class Provider(ABC):
    name: str = "base"
    label: str = "Base"

    def __init__(self) -> None:
        self._clients: dict[str, Any] = {}

    @abstractmethod
    def _client(self, api_key: str) -> Any: ...

    @abstractmethod
    def list_models(self, api_key: str) -> list[dict[str, str]]: ...

    @abstractmethod
    def complete_json(self, api_key: str, model: str, system: str, user: str,
                      max_tokens: int) -> Any: ...

    @abstractmethod
    def test(self, api_key: str, model: str) -> None: ...

    def explain(self, exc: Exception) -> str:
        msg = str(exc)
        low = msg.lower()
        if "401" in msg or "invalid" in low and "key" in low or "api_key_invalid" in low \
                or "authentication" in low:
            return "authentication failed: this key was rejected by the provider"
        if "403" in msg or "permission" in low:
            return f"permission denied: {msg}"
        if "404" in msg or "not found" in low or "not_found" in low:
            return f"model not found or not accessible: {msg}"
        return f"{type(exc).__name__}: {msg}"


class AnthropicProvider(Provider):
    name = "anthropic"
    label = "Anthropic (Claude)"

    def _client(self, api_key: str) -> Any:
        if api_key not in self._clients:
            import anthropic
            self._clients[api_key] = anthropic.Anthropic(api_key=api_key)
        return self._clients[api_key]

    def list_models(self, api_key: str) -> list[dict[str, str]]:
        client = self._client(api_key)
        return [{"id": m.id, "display_name": getattr(m, "display_name", m.id)}
                for m in client.models.list()]

    def complete_json(self, api_key: str, model: str, system: str, user: str,
                      max_tokens: int) -> Any:
        client = self._client(api_key)
        message = client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in message.content
                       if getattr(b, "type", None) == "text")
        return parse_json(text)

    def test(self, api_key: str, model: str) -> None:
        client = self._client(api_key)
        client.messages.create(model=model, max_tokens=8,
                               messages=[{"role": "user", "content": "ping"}])


class GeminiProvider(Provider):
    name = "gemini"
    label = "Google (Gemini)"

    def _client(self, api_key: str) -> Any:
        if api_key not in self._clients:
            try:
                from google import genai
            except Exception as exc:
                raise RuntimeError(
                    "the google-genai package is required for Gemini keys. "
                    "Install it with 'pip install google-genai'."
                ) from exc
            self._clients[api_key] = genai.Client(api_key=api_key)
        return self._clients[api_key]

    def list_models(self, api_key: str) -> list[dict[str, str]]:
        client = self._client(api_key)
        out: list[dict[str, str]] = []
        for m in client.models.list():
            actions = getattr(m, "supported_actions", None) or \
                getattr(m, "supported_generation_methods", []) or []
            if actions and "generateContent" not in actions:
                continue
            mid = (getattr(m, "name", "") or "").replace("models/", "")
            if not mid or "gemini" not in mid.lower():
                continue
            out.append({"id": mid, "display_name": getattr(m, "display_name", mid) or mid})
        return out

    def complete_json(self, api_key: str, model: str, system: str, user: str,
                      max_tokens: int) -> Any:
        from google.genai import types
        client = self._client(api_key)
        resp = client.models.generate_content(
            model=model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
            ),
        )
        return parse_json(resp.text)

    def test(self, api_key: str, model: str) -> None:
        from google.genai import types
        client = self._client(api_key)
        client.models.generate_content(
            model=model, contents="ping",
            config=types.GenerateContentConfig(max_output_tokens=8),
        )


PROVIDERS: dict[str, Provider] = {
    "anthropic": AnthropicProvider(),
    "gemini": GeminiProvider(),
}


def get_provider(name: str) -> Provider | None:
    return PROVIDERS.get(name)


def provider_list() -> list[dict[str, str]]:
    return [{"name": p.name, "label": p.label} for p in PROVIDERS.values()]
