#!/usr/bin/env python3
"""Tech News Podcast Generator - powered by Google NotebookLM.

Fetches the latest technology news from RSS feeds and generates
an AI-hosted podcast using Google NotebookLM's audio overview feature.

Usage:
    # First-time setup: authenticate with Google
    notebooklm login

    # Generate a podcast with defaults
    python main.py

    # Preview articles without generating
    python main.py --preview

    # Customize output
    python main.py --max-articles 5 --output ./my-podcasts --instructions "Keep it brief"

    # Add a custom RSS feed
    python main.py --feed "My Blog" "https://example.com/feed.xml"
"""

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
import os

from news_fetcher import fetch_articles, articles_to_text, DEFAULT_FEEDS
from podcast_generator import generate_podcast

try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def print_articles_table(articles):
    """Display fetched articles in a formatted table."""
    if HAS_RICH:
        table = Table(title="Tech News Articles", show_lines=True)
        table.add_column("#", style="bold", width=3)
        table.add_column("Title", style="cyan", max_width=50)
        table.add_column("Source", style="green", width=20)
        table.add_column("Date", width=18)
        for i, a in enumerate(articles, 1):
            date = a.published.strftime("%Y-%m-%d %H:%M") if a.published else "—"
            table.add_row(str(i), a.title, a.source, date)
        console.print(table)
    else:
        print(f"\n{'#':<4} {'Title':<50} {'Source':<20} {'Date':<18}")
        print("-" * 92)
        for i, a in enumerate(articles, 1):
            date = a.published.strftime("%Y-%m-%d %H:%M") if a.published else "—"
            print(f"{i:<4} {a.title[:48]:<50} {a.source[:18]:<20} {date:<18}")
        print()


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Generate a tech news podcast using Google NotebookLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--preview", action="store_true",
        help="Preview fetched articles without generating a podcast",
    )
    parser.add_argument(
        "--max-articles", type=int,
        default=int(os.getenv("MAX_ARTICLES", "10")),
        help="Maximum number of articles to include (default: 10)",
    )
    parser.add_argument(
        "--output", type=str,
        default=os.getenv("OUTPUT_DIR", "./podcasts"),
        help="Output directory for podcast files (default: ./podcasts)",
    )
    parser.add_argument(
        "--instructions", type=str,
        default=os.getenv("AUDIO_INSTRUCTIONS",
                          "Make it engaging and accessible for a general tech audience. "
                          "Highlight the most impactful stories first."),
        help="Custom instructions for the AI podcast hosts",
    )
    parser.add_argument(
        "--feed", nargs=2, metavar=("NAME", "URL"), action="append",
        help="Add a custom RSS feed (can be repeated). Example: --feed 'My Blog' 'https://example.com/feed.xml'",
    )
    args = parser.parse_args()

    # Build feed list
    feeds = list(DEFAULT_FEEDS)
    if args.feed:
        for name, url in args.feed:
            feeds.append((name, url))

    # Fetch articles
    print("Fetching latest tech news...")
    articles = fetch_articles(feeds=feeds, max_articles=args.max_articles)

    if not articles:
        print("No articles found. Check your internet connection and try again.")
        sys.exit(1)

    print(f"Found {len(articles)} articles from {len(set(a.source for a in articles))} sources.\n")
    print_articles_table(articles)

    if args.preview:
        print("Preview mode — skipping podcast generation.")
        return

    # Generate podcast
    articles_text = articles_to_text(articles)

    print("\nStarting podcast generation via NotebookLM...")
    print("(Make sure you've run 'notebooklm login' first)\n")

    try:
        output_file = asyncio.run(generate_podcast(
            articles=articles,
            articles_text=articles_text,
            output_dir=args.output,
            instructions=args.instructions,
        ))
        print(f"\nPodcast ready: {output_file}")
    except Exception as e:
        print(f"\nError generating podcast: {e}")
        print("\nTroubleshooting:")
        print("  1. Run 'notebooklm login' to authenticate with Google")
        print("  2. Ensure you have access to NotebookLM (notebook.google.com)")
        print("  3. Check your internet connection")
        sys.exit(1)


if __name__ == "__main__":
    main()
