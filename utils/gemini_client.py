"""Gemini Developer API (AI Studio key via google-genai — not Vertex AI)."""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-3.1-flash-lite"

_client: Any = None
_last_request_at: float = 0.0


def get_api_key() -> str | None:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return key or None


def gemini_model() -> str:
    return (os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _max_retries() -> int:
    return max(1, int(os.environ.get("GEMINI_MAX_RETRIES", "3")))


def _min_request_interval_s() -> float:
    """Stay under free-tier RPM (default ~4.5s ≈ 13 req/min). Set 0 to disable."""
    raw = os.environ.get("GEMINI_MIN_REQUEST_INTERVAL_S", "4.5").strip()
    if raw.lower() in ("0", "false", "off", "no"):
        return 0.0
    return max(0.0, float(raw))


def models_for_api() -> list[str]:
    """Primary GEMINI_MODEL plus optional comma-separated GEMINI_MODEL_FALLBACKS."""
    primary = gemini_model()
    raw = os.environ.get("GEMINI_MODEL_FALLBACKS", "").strip()
    fallbacks = [m.strip() for m in raw.split(",") if m.strip()] if raw else []
    ordered: list[str] = []
    seen: set[str] = set()
    for name in [primary, *fallbacks]:
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def _is_quota_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "429" in text or "resource_exhausted" in text or "quota exceeded" in text


def _is_billing_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "prepayment credits" in text or "prepay" in text


def _is_rate_limit_error(exc: BaseException) -> bool:
    if not _is_quota_error(exc) or _is_billing_error(exc):
        return False
    text = str(exc).lower()
    return (
        "rate limit" in text
        or "rpm" in text
        or "requests per minute" in text
        or "retrydelay" in text
        or "resource_exhausted" in text
    )


def retry_delay_seconds(exc: BaseException) -> float:
    text = str(exc)
    patterns = [
        r"retryDelay['\"]?\s*[:=]\s*['\"]?(\d+(?:\.\d+)?)s?",
        r"retry in (\d+(?:\.\d+)?)s",
        r'"retryDelay"\s*:\s*"(\d+)s?"',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return min(float(match.group(1)) + 1.0, 120.0)
    return 55.0


def _wait_for_rate_limit(min_interval: float) -> None:
    global _last_request_at
    if min_interval <= 0:
        return
    elapsed = time.monotonic() - _last_request_at
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)


def _mark_request_sent() -> None:
    global _last_request_at
    _last_request_at = time.monotonic()


def get_client():
    """Singleton genai.Client using GEMINI_API_KEY (AI Studio / Developer API)."""
    global _client
    if _client is None:
        api_key = get_api_key()
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        from google import genai

        _client = genai.Client(api_key=api_key)
    return _client


def generate_text(
    prompt: str,
    *,
    system_instruction: str | None = None,
    model: str | None = None,
    max_output_tokens: int = 1024,
    temperature: float | None = None,
) -> str:
    from google.genai import types

    config_kwargs: dict[str, Any] = {"max_output_tokens": max_output_tokens}
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction
    if temperature is not None:
        config_kwargs["temperature"] = temperature

    client = get_client()
    model_name = model or gemini_model()
    min_interval = _min_request_interval_s()
    last_error: Exception | None = None

    for attempt in range(_max_retries()):
        _wait_for_rate_limit(min_interval)
        try:
            _mark_request_sent()
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            text = (response.text or "").strip()
            if not text:
                raise RuntimeError("Gemini returned an empty response.")
            return text
        except Exception as exc:
            last_error = exc
            if _is_rate_limit_error(exc) and attempt + 1 < _max_retries():
                delay = retry_delay_seconds(exc)
                logger.warning(
                    "Gemini rate limit on %s (attempt %s/%s); waiting %.0fs",
                    model_name,
                    attempt + 1,
                    _max_retries(),
                    delay,
                )
                time.sleep(delay)
                continue
            raise

    raise RuntimeError(f"Gemini request failed after retries: {last_error}") from last_error


def ask(prompt: str, *, model: str | None = None) -> str:
    """Minimal generate_content wrapper (TriEndure-style)."""
    return generate_text(prompt, model=model, max_output_tokens=256)


def generate_text_with_fallbacks(
    prompt: str,
    *,
    system_instruction: str | None = None,
    max_output_tokens: int = 1024,
    temperature: float | None = None,
) -> tuple[str, str]:
    """Try models in order; return (text, model_used)."""
    last_error: Exception | None = None
    for model in models_for_api():
        try:
            text = generate_text(
                prompt,
                system_instruction=system_instruction,
                model=model,
                max_output_tokens=max_output_tokens,
                temperature=temperature,
            )
            return text, model
        except Exception as exc:
            last_error = exc
            if _is_rate_limit_error(exc):
                logger.warning("Gemini model %s rate limited: %s", model, exc)
            else:
                logger.warning("Gemini model %s failed: %s", model, exc)
            continue
    raise RuntimeError(f"Gemini request failed for all models: {last_error}") from last_error
