"""Factories that build STT and TTS engines per user-selected provider and language.

STT is user-selectable (Deepgram, Sarvam AI, ElevenLabs) as required by the assignment.
TTS is routed per language: ElevenLabs for English/Hindi, Sarvam for Telugu (ElevenLabs
has no real-time Telugu support).
"""
from __future__ import annotations

import os

import httpx
import openai
from livekit.agents import llm as llm_base
from livekit.agents import stt as stt_base
from livekit.agents import tts as tts_base
from livekit.plugins import deepgram, elevenlabs, google, openai as openai_plugin, sarvam

from clinic.llm_fallback import RateLimitFallbackLLM

STT_PROVIDERS = ("deepgram", "sarvam", "elevenlabs")
LLM_PROVIDERS = ("auto", "gemini", "ollama")

# app language -> provider-specific language codes
_DEEPGRAM_LANG = {"en": "en-US", "hi": "hi", "te": "multi"}
_SARVAM_STT_LANG = {"en": "en-IN", "hi": "hi-IN", "te": "te-IN"}
_ELEVEN_STT_LANG = {"en": "en", "hi": "hi", "te": "te"}
_SARVAM_TTS_LANG = {"en": "en-IN", "hi": "hi-IN", "te": "te-IN"}
_ELEVEN_TTS_LANG = {"en": "en", "hi": "hi", "te": "te"}


def build_stt(provider: str, language: str) -> stt_base.STT:
    provider = (provider or "deepgram").lower()
    if provider not in STT_PROVIDERS:
        provider = "deepgram"

    if provider == "sarvam":
        return sarvam.STT(
            language=_SARVAM_STT_LANG.get(language, "en-IN"),
            model="saarika:v2.5",
            api_key=os.environ["SARVAM_API_KEY"],
        )
    if provider == "elevenlabs":
        return elevenlabs.STT(
            language_code=_ELEVEN_STT_LANG.get(language, "en"),
            model_id="scribe_v1",
            api_key=os.environ["ELEVEN_API_KEY"],
        )
    return deepgram.STT(
        model="nova-3",
        language=_DEEPGRAM_LANG.get(language, "en-US"),
        api_key=os.environ["DEEPGRAM_API_KEY"],
    )


def build_tts(language: str) -> tts_base.TTS:
    """English + Hindi -> ElevenLabs; Telugu -> Sarvam Bulbul."""
    if language == "te":
        return sarvam.TTS(
            target_language_code=_SARVAM_TTS_LANG["te"],
            model=os.environ.get("SARVAM_TTS_MODEL", "bulbul:v2"),
            speaker=os.environ.get("SARVAM_TTS_SPEAKER", "anushka"),
            api_key=os.environ["SARVAM_API_KEY"],
        )
    voice_id = (
        os.environ.get(f"ELEVEN_VOICE_ID_{language.upper()}")
        or os.environ.get("ELEVEN_VOICE_ID")
        or "EXAVITQu4vr4xnSDxMaL"
    )
    return elevenlabs.TTS(
        voice_id=voice_id,
        model=os.environ.get("ELEVEN_TTS_MODEL", "eleven_flash_v2_5"),
        language=_ELEVEN_TTS_LANG.get(language, "en"),
        api_key=os.environ["ELEVEN_API_KEY"],
    )


def _build_gemini_llm() -> llm_base.LLM:
    return google.LLM(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-001"),
        api_key=os.environ["GEMINI_API_KEY"],
        vertexai=False,
        temperature=0.2,
    )


def _build_ollama_llm() -> llm_base.LLM:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    timeout_s = float(os.environ.get("OLLAMA_TIMEOUT", "90"))
    client = openai.AsyncOpenAI(
        api_key="ollama",
        base_url=base_url,
        timeout=httpx.Timeout(timeout_s, connect=10.0),
    )
    return openai_plugin.LLM.with_ollama(
        model=os.environ.get("OLLAMA_MODEL", "llama3.1:latest"),
        base_url=base_url,
        client=client,
        temperature=0.2,
        parallel_tool_calls=False,
    )


def build_llm() -> llm_base.LLM:
    """LLM routing: auto (Gemini + Ollama on rate limit), gemini-only, or ollama-only."""
    provider = os.environ.get("LLM_PROVIDER", "auto").lower()
    ollama = _build_ollama_llm()

    if provider == "ollama":
        return ollama

    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if provider == "gemini":
        return _build_gemini_llm()

    if provider == "auto" and gemini_key:
        return RateLimitFallbackLLM(primary=_build_gemini_llm(), fallback=ollama)

    # auto without Gemini key, or unknown provider
    return ollama


def llm_mode_label() -> str:
    """Human-readable label for startup logs."""
    provider = os.environ.get("LLM_PROVIDER", "auto").lower()
    if provider == "ollama":
        return "ollama"
    if provider == "gemini":
        return "gemini"
    if provider == "auto" and os.environ.get("GEMINI_API_KEY", "").strip():
        return "auto (gemini→ollama on rate limit)"
    return "ollama (no GEMINI_API_KEY)"
