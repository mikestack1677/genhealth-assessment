from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from genhealth.services.llm_providers.base import LLMProvider


def get_llm_provider() -> LLMProvider:
    """Factory: return the configured LLM provider instance."""
    from genhealth.core.config import get_settings  # noqa: PLC0415 — deferred to avoid circular imports at module load

    settings = get_settings()
    if settings.llm_provider == "gemini":
        from genhealth.services.llm_providers.gemini_provider import (  # noqa: PLC0415 — deferred to avoid circular imports at module load
            GeminiProvider,
        )

        return GeminiProvider()
    from genhealth.services.llm_providers.anthropic_provider import (  # noqa: PLC0415 — deferred to avoid circular imports at module load
        AnthropicProvider,
    )

    return AnthropicProvider()
