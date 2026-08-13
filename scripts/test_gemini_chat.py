"""Minimal Gemini chat smoke test (loads .env, one user message)."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gemini-2.5-flash-lite"


def main() -> int:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("Missing GEMINI_API_KEY in .env", file=sys.stderr)
        return 1

    model = (os.getenv("GEMINI_MODEL") or DEFAULT_MODEL).strip()
    message = " ".join(sys.argv[1:]).strip() or "Say hello in one short sentence."

    print(f"Model: {model}")
    print(f"You: {message}\n")

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("Install: pip install google-genai", file=sys.stderr)
        return 1

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=message,
            config=types.GenerateContentConfig(max_output_tokens=256),
        )
        text = (response.text or "").strip()
        if not text:
            print("Empty response from API.", file=sys.stderr)
            return 1
        print(f"Gemini: {text}")
        return 0
    except Exception as exc:
        print(f"API error ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
