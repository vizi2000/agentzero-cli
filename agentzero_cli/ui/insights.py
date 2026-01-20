"""
Mixed feed: AI News + Project Insights for TUI activity panel.

Provides contextual information during agent thinking:
- AI industry news from feed.theones.io
- Project-specific insights (bugs, suggestions, tips)
"""

import json
import random
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

NEWS_URL = "https://feed.theones.io/api/news.json"
NEWS_CACHE_TTL = 300  # 5 minutes

_news_cache: dict[str, Any] | None = None
_news_cache_time: float = 0


# Project insight templates - filled with actual analysis
PROJECT_INSIGHTS = [
    # Code quality
    {"type": "tip", "text": "Consider adding type hints to improve code maintainability"},
    {"type": "tip", "text": "Functions over 50 lines may benefit from refactoring"},
    {"type": "tip", "text": "Consistent naming conventions improve readability"},
    
    # Security
    {"type": "security", "text": "Never commit .env files - use .env.example as template"},
    {"type": "security", "text": "Validate all user inputs before processing"},
    {"type": "security", "text": "Use parameterized queries to prevent SQL injection"},
    
    # Performance
    {"type": "perf", "text": "Cache expensive computations when possible"},
    {"type": "perf", "text": "Async operations improve responsiveness in I/O-bound tasks"},
    {"type": "perf", "text": "Profile before optimizing - measure, don't guess"},
    
    # Best practices
    {"type": "practice", "text": "Write tests alongside code, not after"},
    {"type": "practice", "text": "Document the 'why', not just the 'what'"},
    {"type": "practice", "text": "Small, focused commits are easier to review"},
    
    # AI/LLM specific
    {"type": "ai", "text": "Streaming responses improve perceived latency"},
    {"type": "ai", "text": "Load balancing between models increases reliability"},
    {"type": "ai", "text": "Temperature 0.7 balances creativity and consistency"},
]


def fetch_news() -> list[dict[str, Any]]:
    """Fetch news from TheOnes.io API with caching."""
    global _news_cache, _news_cache_time

    if _news_cache and (time.time() - _news_cache_time) < NEWS_CACHE_TTL:
        return _news_cache.get("news", [])

    try:
        req = urllib.request.Request(NEWS_URL, headers={"User-Agent": "AgentZeroCLI/0.2"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            _news_cache = json.loads(resp.read().decode("utf-8"))
            _news_cache_time = time.time()
            return _news_cache.get("news", [])
    except Exception:
        return []


def get_news_item() -> dict[str, Any] | None:
    """Get a random news item."""
    news = fetch_news()
    if news:
        item = random.choice(news)
        return {
            "type": "news",
            "title": item.get("title", ""),
            "source": item.get("source", ""),
            "teaser": item.get("teaser", item.get("summary", "")),
        }
    return None


def get_project_insight() -> dict[str, Any]:
    """Get a random project insight/tip."""
    return random.choice(PROJECT_INSIGHTS)


def analyze_workspace(workspace_path: str) -> list[dict[str, Any]]:
    """
    Analyze workspace and generate specific insights.
    Called periodically to provide context-aware suggestions.
    """
    insights = []
    ws = Path(workspace_path)
    
    if not ws.exists():
        return insights
    
    try:
        # Check for common issues
        
        # No .gitignore
        if not (ws / ".gitignore").exists():
            insights.append({
                "type": "suggestion",
                "text": "Consider adding a .gitignore file to exclude build artifacts"
            })
        
        # .env file present (potential security issue)
        if (ws / ".env").exists():
            insights.append({
                "type": "security",
                "text": "Found .env file - ensure it's in .gitignore"
            })
        
        # No tests directory
        if not (ws / "tests").exists() and not (ws / "test").exists():
            insights.append({
                "type": "suggestion",
                "text": "No tests directory found - consider adding unit tests"
            })
        
        # Large files check
        for py_file in ws.rglob("*.py"):
            if py_file.stat().st_size > 30000:  # > 30KB
                insights.append({
                    "type": "refactor",
                    "text": f"{py_file.name} is large ({py_file.stat().st_size // 1000}KB) - consider splitting"
                })
                break
        
        # No README
        if not (ws / "README.md").exists() and not (ws / "readme.md").exists():
            insights.append({
                "type": "suggestion",
                "text": "No README found - add documentation for your project"
            })
        
        # requirements.txt without version pins
        req_file = ws / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text()
            if "==" not in content and ">=" not in content:
                insights.append({
                    "type": "tip",
                    "text": "Pin dependency versions in requirements.txt for reproducibility"
                })
    
    except Exception:
        pass
    
    return insights


def get_mixed_feed_item(workspace_path: str | None = None) -> dict[str, Any]:
    """
    Get a mixed feed item - either news or project insight.
    
    Probability:
    - 40% AI News
    - 30% Project insight (if workspace analyzed)
    - 30% General tips
    """
    roll = random.random()
    
    # Try news first (40%)
    if roll < 0.4:
        news = get_news_item()
        if news:
            return news
    
    # Project-specific insight (30%)
    if workspace_path and roll < 0.7:
        insights = analyze_workspace(workspace_path)
        if insights:
            return random.choice(insights)
    
    # General tip (30% or fallback)
    return get_project_insight()


def format_feed_item(item: dict[str, Any]) -> str:
    """Format feed item for display in activity panel."""
    item_type = item.get("type", "tip")
    
    if item_type == "news":
        title = item.get("title", "")[:60]
        source = item.get("source", "")
        if source:
            return f"[NEWS] {title} ({source})"
        return f"[NEWS] {title}"
    
    elif item_type == "security":
        return f"[SEC] {item.get('text', '')}"
    
    elif item_type == "suggestion":
        return f"[HINT] {item.get('text', '')}"
    
    elif item_type == "refactor":
        return f"[CODE] {item.get('text', '')}"
    
    elif item_type == "perf":
        return f"[PERF] {item.get('text', '')}"
    
    else:
        return f"[TIP] {item.get('text', '')}"
