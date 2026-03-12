"""Generates podcasts from tech news using Google NotebookLM via notebooklm-py."""

import asyncio
from pathlib import Path
from datetime import datetime
from notebooklm import NotebookLMClient

from news_fetcher import Article


async def generate_podcast(
    articles: list[Article],
    articles_text: str,
    output_dir: str = "./podcasts",
    instructions: str = "Make it engaging and accessible for a general tech audience.",
) -> Path:
    """Create a NotebookLM notebook with tech news and generate an audio podcast.

    Args:
        articles: List of Article objects with URLs.
        articles_text: Pre-formatted text digest of the articles.
        output_dir: Directory to save the downloaded podcast.
        instructions: Custom instructions for the AI podcast hosts.

    Returns:
        Path to the downloaded podcast MP3 file.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    notebook_name = f"Tech News Podcast - {datetime.now().strftime('%B %d, %Y')}"
    filename = output_path / f"tech_news_podcast_{timestamp}.mp3"

    async with await NotebookLMClient.from_storage() as client:
        # Create a new notebook for this podcast episode
        print(f"Creating notebook: {notebook_name}")
        notebook = await client.notebooks.create(notebook_name)
        nb_id = notebook.id

        # Add article URLs as sources so NotebookLM can read full content
        urls_added = 0
        for article in articles:
            if not article.url:
                continue
            try:
                print(f"  Adding source: {article.title}")
                await client.sources.add_url(nb_id, article.url, wait=True)
                urls_added += 1
            except Exception as e:
                print(f"  Warning: Could not add URL {article.url}: {e}")

        # If few URLs succeeded, add the text digest as a fallback source
        if urls_added < 3:
            print("  Adding text digest as supplementary source...")
            await client.sources.add_text(nb_id, articles_text, wait=True)

        # Generate the audio overview (podcast)
        print("Generating podcast audio (this may take a few minutes)...")
        status = await client.artifacts.generate_audio(nb_id, instructions=instructions)
        await client.artifacts.wait_for_completion(nb_id, status.task_id)

        # Download the generated audio
        print(f"Downloading podcast to {filename}")
        await client.artifacts.download_audio(nb_id, str(filename))

    print(f"Podcast saved: {filename}")
    return filename
