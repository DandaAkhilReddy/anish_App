"""Azure OpenAI provider — thin wrapper around the AsyncAzureOpenAI client."""
from __future__ import annotations

import json
import re
from typing import Any

from openai import AsyncAzureOpenAI

from app.core.config import settings
from app.core.exceptions import AIAnalysisError
from app.core.logging import get_logger

logger = get_logger(__name__)

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```")
_TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")
_JS_COMMENT_RE = re.compile(r"//[^\n]*")
_MAX_RETRIES = 1


def _extract_json(text: str) -> str:
    """Extract JSON from text that may contain markdown code fences."""
    match = _JSON_BLOCK_RE.search(text)
    if match:
        return match.group(1).strip()
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def _repair_json(text: str) -> str:
    """Attempt to fix common LLM JSON mistakes.

    Handles trailing commas before ``}`` or ``]`` and JS-style
    ``//`` line comments that models sometimes emit.
    """
    text = _JS_COMMENT_RE.sub("", text)
    text = _TRAILING_COMMA_RE.sub(r"\1", text)
    return text.strip()


class OpenAIProvider:
    """Manages the Azure OpenAI client and chat completion calls."""

    def __init__(self) -> None:
        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self._deployment = settings.azure_openai_deployment

    async def chat_completion_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 16000,
    ) -> dict[str, Any]:
        """Send a chat completion request and parse the JSON response.

        Uses ``response_format=json_object`` for structured output and
        falls back to text extraction + repair if needed. Retries once
        on JSON parse failure.

        Args:
            system_prompt: System message content.
            user_prompt: User message content.
            temperature: Sampling temperature (lower = more deterministic).
            max_tokens: Maximum tokens allowed in the assistant response.

        Returns:
            Parsed JSON dict from the assistant's response.

        Raises:
            AIAnalysisError: If the API call fails or the response cannot be
                decoded as valid JSON after retries.
        """
        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            content = await self._call_api(
                system_prompt, user_prompt, max_tokens
            )
            json_str = _repair_json(_extract_json(content))

            try:
                return json.loads(json_str)
            except json.JSONDecodeError as exc:
                last_error = exc
                logger.warning(
                    "openai_json_parse_error",
                    attempt=attempt + 1,
                    content=content[:500],
                    extracted=json_str[:500],
                )
                if attempt < _MAX_RETRIES:
                    logger.info("openai_json_retry", attempt=attempt + 2)

        raise AIAnalysisError(
            f"Invalid JSON response after {_MAX_RETRIES + 1} attempts: "
            f"{last_error}"
        ) from last_error

    async def _call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> str:
        """Execute the chat completion API call.

        Args:
            system_prompt: System message content.
            user_prompt: User message content.
            max_tokens: Maximum tokens in the response.

        Returns:
            Raw text content from the assistant.

        Raises:
            AIAnalysisError: On API errors or empty responses.
        """
        try:
            response = await self._client.chat.completions.create(
                model=self._deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                max_completion_tokens=max_tokens,
                timeout=180.0,
            )
        except Exception as exc:
            logger.error("openai_api_error", error=str(exc))
            raise AIAnalysisError(f"API call failed: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise AIAnalysisError("Empty response from AI model")

        logger.debug("openai_raw_response", content_length=len(content))
        return content
