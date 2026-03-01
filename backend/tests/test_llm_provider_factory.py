"""Unit tests for the get_llm_provider factory."""

from __future__ import annotations

from unittest.mock import patch

from genhealth.services.llm_providers import get_llm_provider
from genhealth.services.llm_providers.anthropic_provider import AnthropicProvider
from genhealth.services.llm_providers.gemini_provider import GeminiProvider


def test_get_llm_provider_returns_gemini_when_configured() -> None:
    """Factory returns GeminiProvider when llm_provider setting is 'gemini'."""
    with (
        patch("genhealth.services.llm_providers.gemini_provider.genai.Client"),
        patch("genhealth.services.llm_providers.anthropic_provider.get_settings"),
        patch("genhealth.services.llm_providers.gemini_provider.get_settings") as mock_settings,
    ):
        mock_settings.return_value.llm_provider = "gemini"
        mock_settings.return_value.google_api_key = ""
        with patch("genhealth.core.config.get_settings") as factory_settings:
            factory_settings.return_value.llm_provider = "gemini"
            provider = get_llm_provider()

    assert isinstance(provider, GeminiProvider)


def test_get_llm_provider_returns_anthropic_when_configured() -> None:
    """Factory returns AnthropicProvider when llm_provider setting is 'anthropic'."""
    with (
        patch("genhealth.services.llm_providers.anthropic_provider.anthropic.AsyncAnthropic"),
        patch("genhealth.services.llm_providers.anthropic_provider.get_settings") as mock_settings,
    ):
        mock_settings.return_value.llm_provider = "anthropic"
        mock_settings.return_value.anthropic_api_key = ""
        with patch("genhealth.core.config.get_settings") as factory_settings:
            factory_settings.return_value.llm_provider = "anthropic"
            provider = get_llm_provider()

    assert isinstance(provider, AnthropicProvider)
