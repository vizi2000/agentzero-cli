"""News feed from feed.theones.io for display during waiting."""

import json
import random
import time
import urllib.error
import urllib.request
from typing import Any

NEWS_URL = "https://feed.theones.io/api/news.json"
CACHE_TTL = 300  # 5 minutes

_cache: dict[str, Any] | None = None
_cache_time: float = 0

FALLBACK_TIPS = [
    "Clear, specific prompts yield better AI responses.",
    "Chain-of-thought prompting improves reasoning.",
    "The term 'AI' was coined by John McCarthy in 1956.",
    "Context window determines how much text AI can process.",
    "Temperature controls randomness in AI responses.",
    "Few-shot examples help AI understand the task.",
    "Breaking complex tasks into steps improves results.",
    "AI models learn patterns from training data.",
]


def fetch_news() -> list[dict[str, Any]]:
    """Fetch news from API with caching."""
    global _cache, _cache_time

    if _cache and (time.time() - _cache_time) < CACHE_TTL:
        return _cache.get("news", [])

    try:
        with urllib.request.urlopen(NEWS_URL, timeout=3) as resp:
            _cache = json.loads(resp.read().decode("utf-8"))
            _cache_time = time.time()
            return _cache.get("news", [])
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return []


def get_random_news() -> dict[str, Any] | None:
    """Get random news item or fallback tip."""
    news = fetch_news()

    if news:
        return random.choice(news)

    # Fallback to tips if API unavailable
    return {
        "title": random.choice(FALLBACK_TIPS),
        "source": "",
        "url": "",
    }
