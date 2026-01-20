#!/usr/bin/env python3
"""
AI News Collector for feed.theones.io

Collects news from RSS feeds and uses Agent Zero to rewrite them
into engaging summaries with full article content for TheOnes.io.
Runs 4x daily via cron.
"""
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

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
    ("MIT Tech Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed", "research"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "news"),
]

OUTPUT_DIR = Path("/home/vizi/feed.theones.io/api")
ARTICLES_DIR = Path("/home/vizi/feed.theones.io/articles")
AGENT_ZERO_URL = os.environ.get(
    "AGENTZERO_API_URL",
    "http://localhost:50001/api_message",
)
AGENT_ZERO_KEY = os.environ.get("AGENTZERO_API_KEY")

MAX_ENTRIES_PER_SOURCE = 3
MAX_TOTAL_NEWS = 20


def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_date(date_str: str) -> str:
    """Parse various date formats to YYYY-MM-DD."""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    
    # Try common formats
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    
    # Fallback: try to extract date-like pattern
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if match:
        return match.group(0)
    
    return datetime.now().strftime("%Y-%m-%d")


def fetch_rss(source: str, url: str, category: str) -> list[dict[str, Any]]:
    """Fetch and parse RSS feed."""
    try:
        feed = feedparser.parse(url)
        entries = []

        for entry in feed.entries[:MAX_ENTRIES_PER_SOURCE]:
            published = entry.get("published", entry.get("updated", ""))
            
            # Get full content if available
            content = ""
            if entry.get("content"):
                content = entry.content[0].get("value", "")
            elif entry.get("summary"):
                content = entry.summary
            
            # Clean content
            content = strip_html(content)
            
            entries.append({
                "id": hashlib.md5(entry.link.encode()).hexdigest()[:8],
                "original_title": strip_html(entry.title),
                "original_content": content[:2000],  # Keep more for article generation
                "source": source,
                "source_url": entry.link,
                "date": parse_date(published),
                "category": category,
            })

        return entries

    except Exception as e:
        print(f"  Error fetching {source}: {e}")
        return []


def rewrite_with_agent_zero(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Use Agent Zero to create engaging summaries and full articles."""

    if not AGENT_ZERO_KEY:
        print("WARNING: AGENTZERO_API_KEY not set. Using original content.")
        for entry in entries:
            entry["title"] = entry["original_title"][:100]
            entry["teaser"] = entry["original_content"][:250] + "..."
            entry["article"] = entry["original_content"]
        return entries

    BATCH_SIZE = 3

    for batch_start in range(0, len(entries), BATCH_SIZE):
        batch = entries[batch_start : batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        print(f"    Processing batch {batch_num}...")

        prompt = """You are a tech journalist. Rewrite these AI news items for TheOnes.io audience.

For each item, create:
1. title: Catchy headline (max 100 chars)
2. teaser: Engaging 2-3 sentence summary that hooks the reader (200-300 chars)
3. article: Full 3-4 paragraph article (800-1200 chars) with insights and context

Output JSON array. KEEP the original id.

"""
        for entry in batch:
            content = entry["original_content"][:800]
            prompt += f'''
---
id: "{entry["id"]}"
source: {entry["source"]}
original_title: {entry["original_title"][:80]}
content: {content}
'''

        prompt += '''
---
Output format:
[{"id":"xxx","title":"...","teaser":"...","article":"..."}]

Write professional, insightful content. No marketing fluff. Focus on what matters to AI practitioners.'''

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

            with urllib.request.urlopen(request, timeout=300) as resp:
                response_text = resp.read().decode("utf-8")

            try:
                data = json.loads(response_text)
                if isinstance(data, dict):
                    content = data.get("message") or data.get("content") or data.get("response") or response_text
                else:
                    content = response_text

                if isinstance(content, str):
                    start = content.find("[")
                    end = content.rfind("]") + 1
                    if start >= 0 and end > start:
                        rewritten = json.loads(content[start:end])
                    else:
                        raise ValueError("No JSON array found")
                else:
                    rewritten = content

                rewrite_map = {r["id"]: r for r in rewritten}

                for entry in batch:
                    if entry["id"] in rewrite_map:
                        r = rewrite_map[entry["id"]]
                        entry["title"] = r.get("title", entry["original_title"])[:100]
                        entry["teaser"] = r.get("teaser", entry["original_content"][:250])
                        entry["article"] = r.get("article", entry["original_content"])
                    else:
                        entry["title"] = entry["original_title"][:100]
                        entry["teaser"] = entry["original_content"][:250] + "..."
                        entry["article"] = entry["original_content"]

                print(f"      Batch {batch_num} rewritten OK")

            except (json.JSONDecodeError, ValueError) as e:
                print(f"      Batch {batch_num} parse error: {e}, using originals")
                for entry in batch:
                    entry["title"] = entry["original_title"][:100]
                    entry["teaser"] = entry["original_content"][:250] + "..."
                    entry["article"] = entry["original_content"]

        except Exception as e:
            print(f"      Batch {batch_num} error: {e}, using originals")
            for entry in batch:
                entry["title"] = entry["original_title"][:100]
                entry["teaser"] = entry["original_content"][:250] + "..."
                entry["article"] = entry["original_content"]

    return entries


def generate_article_page(entry: dict[str, Any]) -> str:
    """Generate static HTML page for an article."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(entry["title"])} | TheOnes.io</title>
    <meta name="description" content="{html.escape(entry["teaser"][:160])}">
    <link rel="canonical" href="https://feed.theones.io/articles/{entry["id"]}.html">
    <meta property="og:title" content="{html.escape(entry["title"])}">
    <meta property="og:description" content="{html.escape(entry["teaser"][:160])}">
    <meta property="og:type" content="article">
    <style>
        :root {{
            --bg: #0a0a0a;
            --surface: #111;
            --border: #222;
            --text: #e5e5e5;
            --muted: #888;
            --accent: #3b82f6;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.7;
        }}
        .container {{ max-width: 720px; margin: 0 auto; padding: 2rem 1rem; }}
        header {{ margin-bottom: 2rem; }}
        .back {{ color: var(--accent); text-decoration: none; font-size: 0.9rem; }}
        .back:hover {{ text-decoration: underline; }}
        h1 {{ font-size: 1.8rem; font-weight: 600; margin: 1rem 0; line-height: 1.3; }}
        .meta {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 2rem; }}
        .meta a {{ color: var(--accent); text-decoration: none; }}
        .category {{
            display: inline-block;
            background: var(--border);
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.7rem;
            text-transform: uppercase;
            margin-left: 1rem;
        }}
        article {{ font-size: 1.05rem; }}
        article p {{ margin-bottom: 1.5rem; }}
        .source-link {{
            margin-top: 2rem;
            padding: 1.5rem;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
        }}
        .source-link a {{
            color: var(--accent);
            text-decoration: none;
            font-weight: 500;
        }}
        .source-link a:hover {{ text-decoration: underline; }}
        footer {{
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid var(--border);
            text-align: center;
            color: var(--muted);
            font-size: 0.8rem;
        }}
        footer a {{ color: var(--accent); text-decoration: none; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <a href="/" class="back">Back to Feed</a>
            <h1>{html.escape(entry["title"])}</h1>
            <div class="meta">
                <a href="{entry["source_url"]}" target="_blank" rel="noopener">{entry["source"]}</a>
                &middot; {entry["date"]}
                <span class="category">{entry["category"]}</span>
            </div>
        </header>
        
        <article>
            {format_article(entry["article"])}
        </article>
        
        <div class="source-link">
            <p>Read the original article:</p>
            <a href="{entry["source_url"]}" target="_blank" rel="noopener">{entry["source_url"]}</a>
        </div>
        
        <footer>
            <p>Powered by Agent Zero | <a href="https://theones.io">TheOnes.io</a></p>
        </footer>
    </div>
</body>
</html>'''


def format_article(text: str) -> str:
    """Format article text into paragraphs."""
    paragraphs = text.split('\n\n')
    if len(paragraphs) == 1:
        # Try splitting by sentences for long single paragraph
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) > 4:
            mid = len(sentences) // 2
            paragraphs = [' '.join(sentences[:mid]), ' '.join(sentences[mid:])]
    
    return '\n'.join(f'<p>{html.escape(p.strip())}</p>' for p in paragraphs if p.strip())


def collect_and_publish():
    """Main collection and publishing workflow."""
    print(f"[{datetime.now().isoformat()}] Starting news collection...")

    all_entries = []
    for source, url, category in RSS_FEEDS:
        print(f"  Fetching {source}...")
        entries = fetch_rss(source, url, category)
        all_entries.extend(entries)
        print(f"    Got {len(entries)} entries")

    if not all_entries:
        print("  No entries collected, aborting")
        return

    all_entries.sort(key=lambda x: x.get("date", ""), reverse=True)
    all_entries = all_entries[:MAX_TOTAL_NEWS]

    print(f"  Total entries to process: {len(all_entries)}")

    print("  Rewriting with Agent Zero...")
    rewritten = rewrite_with_agent_zero(all_entries)

    # Generate article pages
    ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
    print("  Generating article pages...")
    
    for entry in rewritten:
        article_path = ARTICLES_DIR / f"{entry['id']}.html"
        article_path.write_text(generate_article_page(entry), encoding="utf-8")

    # Create feed JSON with links to articles
    output_entries = []
    for entry in rewritten:
        output_entries.append({
            "id": entry["id"],
            "title": entry.get("title", entry.get("original_title", ""))[:100],
            "teaser": entry.get("teaser", "")[:300],
            "source": entry["source"],
            "source_url": entry["source_url"],
            "article_url": f"/articles/{entry['id']}.html",
            "date": entry["date"],
            "category": entry["category"],
        })

    output = {
        "updated": datetime.utcnow().isoformat() + "Z",
        "news": output_entries,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "news.json"
    output_file.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    print(f"  Written {len(output_entries)} entries to {output_file}")
    print(f"  Generated {len(output_entries)} article pages")
    print(f"[{datetime.now().isoformat()}] Done!")


if __name__ == "__main__":
    collect_and_publish()
