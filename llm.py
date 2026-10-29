from openai import OpenAI

import config

_cache = {}


def client():
    """Client for the current API. Any OpenAI-compatible API works (Groq, Gemini, OpenRouter, Ollama...).

    It is recreated when the key or the address change in the settings.
    """
    key = (config.LLM_API_KEY, config.LLM_BASE_URL)
    if key not in _cache:
        _cache.clear()
        _cache[key] = OpenAI(api_key=config.LLM_API_KEY or "no-key", base_url=config.LLM_BASE_URL, timeout=30)
    return _cache[key]


def test(api_key, base_url, model):
    """Make a minimal call with the given values. Returns (ok, message)."""
    try:
        c = OpenAI(api_key=api_key or "no-key", base_url=base_url, timeout=15)
        c.chat.completions.create(
            model=model, max_tokens=5, messages=[{"role": "user", "content": "Reply: ok"}])
        return True, "Connection works."
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:200]}"
