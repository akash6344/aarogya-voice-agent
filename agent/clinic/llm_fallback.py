"""Gemini-first LLM with Ollama fallback only on rate-limit / quota errors."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterable
from typing import Any

from livekit.agents._exceptions import APIStatusError
from livekit.agents.llm import LLM, ChatChunk, LLMStream
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, NOT_GIVEN, APIConnectOptions, NotGivenOr
from livekit.agents.utils import is_given
from livekit.agents.llm.tool_context import Tool, ToolChoice

logger = logging.getLogger("aarogya-agent")


def is_rate_limited(exc: BaseException) -> bool:
    """True when the cloud LLM hit quota / rate limits and a local fallback is reasonable."""
    if isinstance(exc, APIStatusError):
        if exc.status_code in (429, 503):
            return True
        body = str(exc.body or exc.message).lower()
        if any(token in body for token in ("rate limit", "quota", "resource exhausted", "too many requests")):
            return True
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "quota exceeded" in msg


class RateLimitFallbackLLM(LLM):
    """Use ``primary`` (Gemini) for quality; switch to ``fallback`` (Ollama) only on rate limits."""

    def __init__(self, *, primary: LLM, fallback: LLM) -> None:
        super().__init__()
        self._primary = primary
        self._fallback = fallback

    @property
    def model(self) -> str:
        return f"{self._primary.model}→{self._fallback.model}"

    @property
    def provider(self) -> str:
        return "rate-limit-fallback"

    def chat(
        self,
        *,
        chat_ctx,
        tools: list[Tool] | None = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        parallel_tool_calls: NotGivenOr[bool] = NOT_GIVEN,
        tool_choice: NotGivenOr[ToolChoice] = NOT_GIVEN,
        extra_kwargs: NotGivenOr[dict[str, Any]] = NOT_GIVEN,
    ) -> LLMStream:
        return _RateLimitFallbackStream(
            llm=self,
            primary=self._primary,
            fallback=self._fallback,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
            parallel_tool_calls=parallel_tool_calls,
            tool_choice=tool_choice,
            extra_kwargs=extra_kwargs,
        )

    async def aclose(self) -> None:
        await self._primary.aclose()
        await self._fallback.aclose()


class _RateLimitFallbackStream(LLMStream):
    _llm_request_span_name = "llm_rate_limit_fallback"

    def __init__(
        self,
        llm: RateLimitFallbackLLM,
        *,
        primary: LLM,
        fallback: LLM,
        chat_ctx,
        tools: list[Tool],
        conn_options: APIConnectOptions,
        parallel_tool_calls: NotGivenOr[bool],
        tool_choice: NotGivenOr[ToolChoice],
        extra_kwargs: NotGivenOr[dict[str, Any]],
    ) -> None:
        super().__init__(llm, chat_ctx=chat_ctx, tools=tools, conn_options=conn_options)
        self._primary = primary
        self._fallback = fallback
        self._parallel_tool_calls = parallel_tool_calls
        self._tool_choice = tool_choice
        self._extra_kwargs = extra_kwargs

    async def _stream_from(self, llm: LLM) -> None:
        kwargs: dict[str, Any] = {
            "chat_ctx": self._chat_ctx,
            "tools": self._tools,
            "conn_options": self._conn_options,
        }
        if is_given(self._parallel_tool_calls):
            kwargs["parallel_tool_calls"] = self._parallel_tool_calls
        if is_given(self._tool_choice):
            kwargs["tool_choice"] = self._tool_choice
        if is_given(self._extra_kwargs):
            kwargs["extra_kwargs"] = self._extra_kwargs

        async with llm.chat(**kwargs) as stream:
            async for chunk in stream:
                self._event_ch.send_nowait(chunk)

    async def _run(self) -> None:
        try:
            await self._stream_from(self._primary)
        except Exception as exc:
            if not is_rate_limited(exc):
                raise
            logger.warning(
                "Primary LLM rate-limited (%s); falling back to Ollama for this turn",
                exc,
            )
            await self._stream_from(self._fallback)

    async def _metrics_monitor_task(self, event_aiter: AsyncIterable[ChatChunk]) -> None:
        return
