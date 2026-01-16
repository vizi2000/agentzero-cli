#!/usr/bin/env python3
"""
AI News Collector for feed.theones.io

Collects news from RSS feeds and uses Agent Zero to rewrite them
into fresh, unique content. Runs 4x daily via cron.
"""
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

# Try to import feedparser, install hint if missing
try:
    import feedparser
except ImportError:
    print("ERROR: feedparser not installed. Run: pip install feedparser")
    sys.exit(1)


# Configuration
RSS_FEEDS = [
    ("Anthropic", "https://www.anthropic.com/feed.xml", "models"),
    ("OpenAI", "https://openai.com/blog/rss.xml", "models"),
    ("Google AI", "https://blog.google/technology/ai/rss/", "research"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml", "open-source"),
    ("AI News", "https://www.artificialintelligence-news.com/feed/", "industry"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/", "business"),
    (
        "MIT Tech Review AI",
        "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "research",
    ),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "news"),
]

OUTPUT_DIR = Path("/home/vizi/feed.theones.io/api")
AGENT_ZERO_URL = os.environ.get(
    "AGENTZERO_API_URL",
    "http://194.181.240.37:50001/api_message",
)
AGENT_ZERO_KEY = os.environ.get("AGENTZERO_API_KEY")

MAX_ENTRIES_PER_SOURCE = 3
MAX_TOTAL_NEWS = 20


def fetch_rss(source: str, url: str, category: str) -> list[dict[str, Any]]:
    """Fetch and parse RSS feed."""
    try:
        feed = feedparser.parse(url)
        entries = []

        for entry in feed.entries[:MAX_ENTRIES_PER_SOURCE]:
            # Get published date
            published = entry.get("published", entry.get("updated", ""))

            entries.append(
                {
                    "id": hashlib.md5(entry.link.encode()).hexdigest()[:8],
                    "original_title": entry.title,
                    "original_summary": entry.get("summary", "")[:500],
                    "source": source,
                    "url": entry.link,
                    "date": (
                        published[:10]
                        if len(published) >= 10
                        else datetime.now().strftime("%Y-%m-%d")
                    ),
                    "category": category,
                }
            )

        return entries

    except Exception as e:
        print(f"  Error fetching {source}: {e}")
        return []


def rewrite_with_agent_zero(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Use Agent Zero to rewrite news into unique content."""

    if not AGENT_ZERO_KEY:
        print("ERROR: AGENTZERO_API_KEY not set. Skipping rewrite step.")
        return entries

    # Process in smaller batches for reliability
    BATCH_SIZE = 5

    for batch_start in range(0, len(entries), BATCH_SIZE):
        batch = entries[batch_start : batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        print(f"    Processing batch {batch_num}...")

        # Optimized prompt - shorter, clearer, MUST include id
        prompt = """Rewrite these AI news items. Output JSON array with id, title, summary.

Rules:
- KEEP the original id in output
- title: catchy, max 80 chars
- summary: engaging, max 150 chars, no HTML

Input:
"""
        for entry in batch:
            # Clean summary from HTML
            summary = entry["original_summary"][:150].replace("<", "").replace(">", "")
            prompt += f'id="{entry["id"]}" | {entry["original_title"][:60]}: {summary}\n'

        prompt += '\nOutput JSON array like: [{"id":"xxx","title":"...","summary":"..."}]'

        payload = {
            "message": prompt,
            "lifetime_hours": 1,
        }

        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": AGENT_ZERO_KEY,
        }

        try:
            body = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                AGENT_ZERO_URL, data=body, headers=headers, method="POST"
            )

            # Increased timeout to 300s (5 min)
            with urllib.request.urlopen(request, timeout=300) as resp:
                response_text = resp.read().decode("utf-8")

            # Try to parse response
            try:
                data = json.loads(response_text)
                # Handle various response formats
                if isinstance(data, dict):
                    if "message" in data:
                        content = data["message"]
                    elif "content" in data:
                        content = data["content"]
                    elif "response" in data:
                        content = data["response"]
                    else:
                        content = response_text
                else:
                    content = response_text

                # Extract JSON from content
                if isinstance(content, str):
                    start = content.find("[")
                    end = content.rfind("]") + 1
                    if start >= 0 and end > start:
                        rewritten = json.loads(content[start:end])
                    else:
                        raise ValueError("No JSON array found")
                else:
                    rewritten = content

                # Merge rewritten content back to batch entries
                rewrite_map = {r["id"]: r for r in rewritten}

                for entry in batch:
                    if entry["id"] in rewrite_map:
                        r = rewrite_map[entry["id"]]
                        entry["title"] = r.get("title", entry["original_title"])[:80]
                        entry["summary"] = r.get("summary", entry["original_summary"])[:150]
                    else:
                        entry["title"] = entry["original_title"][:80]
                        entry["summary"] = entry["original_summary"][:150]

                print(f"      Batch {batch_num} rewritten OK")

            except (json.JSONDecodeError, ValueError) as e:
                print(f"      Batch {batch_num} parse error: {e}, using originals")
                for entry in batch:
                    entry["title"] = entry["original_title"][:80]
                    entry["summary"] = entry["original_summary"][:150]

        except Exception as e:
            print(f"      Batch {batch_num} error: {e}, using originals")
            for entry in batch:
                entry["title"] = entry["original_title"][:80]
                entry["summary"] = entry["original_summary"][:150]

    return entries


def collect_and_publish():
    """Main collection and publishing workflow."""
    print(f"[{datetime.now().isoformat()}] Starting news collection...")

    # Collect from all sources
    all_entries = []
    for source, url, category in RSS_FEEDS:
        print(f"  Fetching {source}...")
        entries = fetch_rss(source, url, category)
        all_entries.extend(entries)
        print(f"    Got {len(entries)} entries")

    if not all_entries:
        print("  No entries collected, aborting")
        return

    # Sort by date (newest first) and limit
    all_entries.sort(key=lambda x: x.get("date", ""), reverse=True)
    all_entries = all_entries[:MAX_TOTAL_NEWS]

    print(f"  Total entries to process: {len(all_entries)}")

    # Rewrite with Agent Zero
    print("  Rewriting with Agent Zero...")
    rewritten = rewrite_with_agent_zero(all_entries)

    # Clean up entries for output (remove original_* fields)
    output_entries = []
    for entry in rewritten:
        output_entries.append(
            {
                "id": entry["id"],
                "title": entry.get("title", entry.get("original_title", ""))[:80],
                "summary": entry.get("summary", entry.get("original_summary", ""))[:150],
                "source": entry["source"],
                "url": entry["url"],
                "date": entry["date"],
                "category": entry["category"],
            }
        )

    # Write output
    output = {
        "updated": datetime.utcnow().isoformat() + "Z",
        "news": output_entries,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "news.json"
    output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print(f"  Written {len(output_entries)} entries to {output_file}")
    print(f"[{datetime.now().isoformat()}] Done!")


if __name__ == "__main__":
    collect_and_publish()
