"""LLM provider configuration for OpenAI-compatible chat completions."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

try:
    from openai import OpenAI
except ImportError:  # Allows import-time diagnostics before dependencies are installed.
    OpenAI = None  # type: ignore[assignment]


DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.5-flash",
    "openai_compatible": "gpt-4o-mini",
}

BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}

API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "openai_compatible": "LLM_API_KEY",
}


@dataclass(frozen=True)
class LLMProviderConfig:
    provider: str
    model: str
    api_key_env: str
    base_url: str | None = None


def build_chat_client() -> tuple[Any, LLMProviderConfig]:
    """Build an OpenAI-compatible client for OpenAI, Groq, Gemini or custom APIs."""

    if OpenAI is None:
        raise RuntimeError(
            "The 'openai' package is required for LLM provider access. "
            "Install dependencies with: python3 -m pip install -r requirements.txt"
        )

    config = resolve_provider_config()
    api_key = os.environ.get(config.api_key_env)
    if not api_key:
        raise RuntimeError(
            f"Missing {config.api_key_env} environment variable for provider {config.provider}."
        )

    kwargs: dict[str, Any] = {"api_key": api_key}
    if config.base_url:
        kwargs["base_url"] = config.base_url
    return OpenAI(**kwargs), config


def build_chat_client_for_config(config: LLMProviderConfig) -> Any:
    """Build a client for an already resolved provider config."""

    if OpenAI is None:
        raise RuntimeError(
            "The 'openai' package is required for LLM provider access. "
            "Install dependencies with: python3 -m pip install -r requirements.txt"
        )

    api_key = os.environ.get(config.api_key_env)
    if not api_key:
        raise RuntimeError(
            f"Missing {config.api_key_env} environment variable for provider {config.provider}."
        )

    kwargs: dict[str, Any] = {"api_key": api_key}
    if config.base_url:
        kwargs["base_url"] = config.base_url
    return OpenAI(**kwargs)


def resolve_provider_config() -> LLMProviderConfig:
    provider, api_key_env = _selected_provider_and_key_env()
    return _provider_config(provider, api_key_env)


def fallback_provider_configs(primary: LLMProviderConfig) -> list[LLMProviderConfig]:
    """Return configured fallback providers after the selected primary provider."""

    if os.environ.get("LLM_PROVIDER"):
        return []

    configs = []
    for provider in ("groq", "gemini", "openai"):
        if provider == primary.provider:
            continue
        api_key_env = API_KEY_ENV[provider]
        if os.environ.get(api_key_env):
            configs.append(_provider_config(provider, api_key_env))
    return configs


def _provider_config(provider: str, api_key_env: str) -> LLMProviderConfig:
    model = (
        os.environ.get("LLM_MODEL")
        or os.environ.get(f"{provider.upper()}_MODEL")
        or DEFAULT_MODELS[provider]
    )
    base_url = (
        os.environ.get("LLM_BASE_URL")
        if provider == "openai_compatible"
        else BASE_URLS.get(provider)
    )
    if provider == "openai_compatible" and not base_url:
        raise RuntimeError("LLM_BASE_URL is required when LLM_PROVIDER=openai_compatible.")
    return LLMProviderConfig(
        provider=provider,
        model=model,
        api_key_env=api_key_env,
        base_url=base_url,
    )


def _selected_provider_and_key_env() -> tuple[str, str]:
    explicit = os.environ.get("LLM_PROVIDER")
    if explicit:
        normalized = explicit.strip().lower().replace("-", "_")
        if normalized not in API_KEY_ENV:
            supported = ", ".join(sorted(API_KEY_ENV))
            raise RuntimeError(f"Unsupported LLM_PROVIDER={explicit}. Supported: {supported}.")
        return normalized, API_KEY_ENV[normalized]

    if os.environ.get("GROQ_API_KEY"):
        return "groq", "GROQ_API_KEY"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini", "GEMINI_API_KEY"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai", "OPENAI_API_KEY"
    if os.environ.get("LLM_API_KEY") and os.environ.get("LLM_BASE_URL"):
        return "openai_compatible", "LLM_API_KEY"
    return "groq", "GROQ_API_KEY"
