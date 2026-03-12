# Tech News Podcast Generator

Generate AI-hosted podcasts about the latest technology news using [Google NotebookLM](https://notebooklm.google.com/) via the [`notebooklm-py`](https://github.com/teng-lin/notebooklm-py) package.

The app fetches recent articles from curated tech RSS feeds (Ars Technica, TechCrunch, The Verge, Hacker News, MIT Technology Review), sends them to NotebookLM, and generates an audio overview — a podcast-style conversation between two AI hosts discussing the news.

## Prerequisites

- Python 3.10+
- A Google account with access to [NotebookLM](https://notebooklm.google.com/)

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browser for Google authentication
playwright install chromium

# Authenticate with Google (one-time, opens a browser)
notebooklm login

# Copy and customize settings (optional)
cp .env.example .env
```

## Usage

```bash
# Preview which articles will be included
python main.py --preview

# Generate a podcast with defaults
python main.py

# Limit to 5 articles
python main.py --max-articles 5

# Custom output directory and host instructions
python main.py --output ./episodes --instructions "Keep it under 10 minutes and focus on AI"

# Add a custom RSS feed alongside the defaults
python main.py --feed "My Blog" "https://example.com/feed.xml"
```

## Default News Sources

| Source | Feed |
|---|---|
| Ars Technica | `feeds.arstechnica.com/arstechnica/index` |
| TechCrunch | `techcrunch.com/feed/` |
| The Verge | `theverge.com/rss/index.xml` |
| Hacker News (Top) | `hnrss.org/frontpage` |
| MIT Technology Review | `technologyreview.com/feed/` |

## Configuration

Settings can be configured via `.env` file or command-line arguments:

| Setting | Default | Description |
|---|---|---|
| `OUTPUT_DIR` | `./podcasts` | Where to save podcast MP3 files |
| `AUDIO_INSTRUCTIONS` | General tech audience | Custom instructions for AI hosts |
| `MAX_ARTICLES` | `10` | Max articles per podcast |

## How It Works

1. **Fetch** — Pulls latest articles from tech RSS feeds using `feedparser`
2. **Source** — Creates a NotebookLM notebook and adds article URLs as sources
3. **Generate** — Triggers NotebookLM's audio overview generation
4. **Download** — Saves the resulting podcast MP3 locally

## Note

`notebooklm-py` is an unofficial library that uses NotebookLM's internal APIs. It may break if Google changes their endpoints. Use a dedicated Google account for testing.
