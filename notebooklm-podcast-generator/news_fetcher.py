"""Fetches technology news articles from RSS feeds."""

import feedparser
from dataclasses import dataclass
from datetime import datetime


# Curated list of technology news RSS feeds
DEFAULT_FEEDS = [
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("Hacker News (Top)", "https://hnrss.org/frontpage"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
]


@dataclass
class Article:
    title: str
    url: str
    source: str
    published: datetime | None
    summary: str


def fetch_articles(feeds: list[tuple[str, str]] | None = None, max_articles: int = 10) -> list[Article]:
    """Fetch recent articles from RSS feeds, sorted by recency.

    Args:
        feeds: List of (name, url) tuples. Uses DEFAULT_FEEDS if None.
        max_articles: Maximum number of articles to return.

    Returns:
        List of Article objects sorted newest-first.
    """
    feeds = feeds or DEFAULT_FEEDS
    articles: list[Article] = []

    for source_name, feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:  # Take top 5 per feed
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])

                summary = ""
                if hasattr(entry, "summary"):
                    summary = entry.summary[:500]

                articles.append(Article(
                    title=entry.get("title", "Untitled"),
                    url=entry.get("link", ""),
                    source=source_name,
                    published=published,
                    summary=summary,
                ))
        except Exception as e:
            print(f"Warning: Failed to fetch from {source_name}: {e}")

    # Sort by published date (newest first), articles without dates go last
    articles.sort(key=lambda a: a.published or datetime.min, reverse=True)
    return articles[:max_articles]


def articles_to_text(articles: list[Article]) -> str:
    """Format articles into a text document suitable for NotebookLM ingestion."""
    lines = [
        f"Technology News Digest - {datetime.now().strftime('%B %d, %Y')}",
        "=" * 60,
        "",
    ]
    for i, article in enumerate(articles, 1):
        date_str = article.published.strftime("%Y-%m-%d %H:%M") if article.published else "Unknown date"
        lines.extend([
            f"--- Article {i} ---",
            f"Title: {article.title}",
            f"Source: {article.source}",
            f"Date: {date_str}",
            f"URL: {article.url}",
            "",
            article.summary if article.summary else "(No summary available)",
            "",
        ])
    return "\n".join(lines)
