#!/usr/bin/env python3
"""Validate external services using agent/.env (and LiveKit keys shared with web/).

Run from the agent folder:
  .venv/bin/python scripts/validate_env.py
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"
PASS, FAIL, WARN = f"{GREEN}PASS{RESET}", f"{RED}FAIL{RESET}", f"{YELLOW}WARN{RESET}"

results: list[tuple[str, str, str]] = []


def record(name: str, status: str, detail: str = "") -> None:
    results.append((name, status, detail))
    tag = {"PASS": PASS, "FAIL": FAIL, "WARN": WARN}[status]
    print(f"  [{tag}] {name}" + (f" {DIM}- {detail}{RESET}" if detail else ""))


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        print(f"{RED}No .env at {path}{RESET}")
        sys.exit(1)
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip()
    return env


def section(title: str) -> None:
    print(f"\n{title}")


def check_deepgram(env: dict[str, str]) -> None:
    section("Deepgram (STT)")
    key = env.get("DEEPGRAM_API_KEY", "")
    if not key:
        record("Deepgram key present", "FAIL", "DEEPGRAM_API_KEY empty")
        return
    try:
        r = requests.get(
            "https://api.deepgram.com/v1/projects",
            headers={"Authorization": f"Token {key}"},
            timeout=20,
        )
        if r.status_code == 200:
            n = len(r.json().get("projects", []))
            record("Deepgram auth", "PASS", f"{n} project(s) visible")
        else:
            record("Deepgram auth", "FAIL", f"HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        record("Deepgram auth", "FAIL", str(e))


def check_sarvam(env: dict[str, str]) -> None:
    section("Sarvam AI (STT key + Telugu TTS)")
    key = env.get("SARVAM_API_KEY", "")
    if not key:
        record("Sarvam key present", "FAIL", "SARVAM_API_KEY empty")
        return
    model = env.get("SARVAM_TTS_MODEL", "bulbul:v2")
    speaker = env.get("SARVAM_TTS_SPEAKER", "anushka")
    headers = {"api-subscription-key": key, "Content-Type": "application/json"}
    payloads = [
        {"text": "నమస్కారం", "target_language_code": "te-IN", "speaker": speaker, "model": model},
        {"inputs": ["నమస్కారం"], "target_language_code": "te-IN", "speaker": speaker, "model": model},
    ]
    last = ""
    for body in payloads:
        try:
            r = requests.post("https://api.sarvam.ai/text-to-speech", headers=headers, json=body, timeout=30)
            if r.status_code == 200 and (r.json().get("audios") or r.json().get("audio")):
                record("Sarvam TTS (Telugu)", "PASS", f"{model}/{speaker} synthesized te-IN audio")
                return
            last = f"HTTP {r.status_code}: {r.text[:160]}"
        except Exception as e:
            last = str(e)
    record("Sarvam TTS (Telugu)", "FAIL", last)


def check_elevenlabs(env: dict[str, str]) -> None:
    section("ElevenLabs (English + Hindi TTS)")
    key = env.get("ELEVEN_API_KEY", "")
    if not key:
        record("ElevenLabs key present", "FAIL", "ELEVEN_API_KEY empty")
        return
    model = env.get("ELEVEN_TTS_MODEL", "eleven_flash_v2_5")
    # voices_read (optional)
    try:
        r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key}, timeout=20)
        if r.status_code == 200:
            record("ElevenLabs voices_read", "PASS", f"{len(r.json().get('voices', []))} voice(s)")
        else:
            record("ElevenLabs voices_read", "WARN", f"HTTP {r.status_code} (not required for TTS)")
    except Exception as e:
        record("ElevenLabs voices_read", "WARN", str(e))
    # actual TTS synthesis per language voice
    for lang, var, text in [("EN", "ELEVEN_VOICE_ID_EN", "Hello, this is a test."),
                            ("HI", "ELEVEN_VOICE_ID_HI", "नमस्ते, यह एक परीक्षण है।")]:
        vid = env.get(var, "")
        if not vid:
            record(f"ElevenLabs TTS {lang}", "FAIL", f"{var} empty")
            continue
        try:
            r = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
                headers={"xi-api-key": key, "Content-Type": "application/json"},
                json={"text": text, "model_id": model},
                timeout=30,
            )
            if r.status_code == 200 and r.content:
                record(f"ElevenLabs TTS {lang}", "PASS", f"{len(r.content)} bytes via {model}")
            else:
                record(f"ElevenLabs TTS {lang}", "FAIL", f"HTTP {r.status_code}: {r.text[:160]}")
        except Exception as e:
            record(f"ElevenLabs TTS {lang}", "FAIL", str(e))


def check_gemini(env: dict[str, str]) -> None:
    section("Gemini (LLM)")
    key = env.get("GEMINI_API_KEY", "")
    if not key:
        record("Gemini key present", "FAIL", "GEMINI_API_KEY empty")
        return
    try:
        r = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": key},
            timeout=20,
        )
        if r.status_code == 200:
            names = [m.get("name", "") for m in r.json().get("models", [])]
            record("Gemini auth", "PASS", f"{len(names)} models available")
        else:
            hint = ""
            if not key.startswith("AIza"):
                hint = " | key does not look like an AI Studio API key (expected 'AIza...')"
            record("Gemini auth", "FAIL", f"HTTP {r.status_code}: {r.text[:120]}{hint}")
    except Exception as e:
        record("Gemini auth", "FAIL", str(e))


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _livekit_token(api_key: str, api_secret: str) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": api_key,
        "sub": "env-validator",
        "nbf": now - 5,
        "exp": now + 300,
        "video": {"roomList": True, "roomCreate": False},
    }
    signing_input = f"{_b64url(json.dumps(header).encode())}.{_b64url(json.dumps(payload).encode())}"
    sig = hmac.new(api_secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url(sig)}"


def check_livekit(env: dict[str, str]) -> None:
    section("LiveKit (realtime transport)")
    url = env.get("LIVEKIT_URL", "")
    api_key = env.get("LIVEKIT_API_KEY", "")
    secret = env.get("LIVEKIT_API_SECRET", "")
    if not (url and api_key and secret):
        record("LiveKit config present", "FAIL", "URL/KEY/SECRET incomplete")
        return
    http = url.replace("wss://", "https://").replace("ws://", "http://").rstrip("/")
    try:
        token = _livekit_token(api_key, secret)
        r = requests.post(
            f"{http}/twirp/livekit.RoomService/ListRooms",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            data="{}",
            timeout=20,
        )
        if r.status_code == 200:
            record("LiveKit auth", "PASS", f"ListRooms ok ({len(r.json().get('rooms', []))} room(s))")
        else:
            record("LiveKit auth", "FAIL", f"HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        record("LiveKit auth", "FAIL", str(e))


def check_postgres(env: dict[str, str]) -> None:
    section("Neon PostgreSQL")
    dsn = env.get("DATABASE_URL", "")
    if not dsn:
        record("DATABASE_URL present", "FAIL", "empty")
        return
    try:
        import psycopg
    except ModuleNotFoundError:
        record("Postgres connect", "WARN", "psycopg not installed; skipped")
        return
    try:
        with psycopg.connect(dsn, connect_timeout=20) as conn:
            with conn.cursor() as cur:
                cur.execute("select version()")
                ver = cur.fetchone()[0]
                cur.execute(
                    "select count(*) from information_schema.tables where table_schema='public'"
                )
                tables = cur.fetchone()[0]
        record("Postgres connect", "PASS", f"{ver.split(',')[0]} | {tables} public table(s)")
    except Exception as e:
        record("Postgres connect", "FAIL", str(e))


def main() -> None:
    print(f"Validating services from {ENV_PATH}")
    env = load_env(ENV_PATH)
    check_livekit(env)
    check_deepgram(env)
    check_sarvam(env)
    check_elevenlabs(env)
    check_gemini(env)
    check_postgres(env)

    print("\n" + "=" * 60)
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    warned = sum(1 for _, s, _ in results if s == "WARN")
    print(f"Summary: {GREEN}{passed} passed{RESET}, {RED}{failed} failed{RESET}, {YELLOW}{warned} warnings{RESET}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
