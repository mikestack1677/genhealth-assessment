from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM document extraction providers."""

    @abstractmethod
    async def extract(self, pdf_bytes: bytes, filename: str) -> str:
        """Send PDF to LLM. Return raw text response (expected to contain JSON)."""
