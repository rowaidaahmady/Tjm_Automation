import logging

import requests

from .settings import POSTS_URL, REQUEST_TIMEOUT_SECONDS, MAX_POSTS

logger = logging.getLogger(__name__)


def fetch_posts() -> list[dict]:
    """Fetch the first MAX_POSTS posts from JSONPlaceholder; raise on network failure."""
    logger.info("Fetching posts from %s ...", POSTS_URL)
    try:
        response = requests.get(POSTS_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(f"Cannot reach {POSTS_URL}. Check your internet connection.") from exc
    except requests.exceptions.Timeout as exc:
        raise RuntimeError(f"Request to {POSTS_URL} timed out after {REQUEST_TIMEOUT_SECONDS}s.") from exc
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(f"API returned an error: {exc}") from exc

    posts = response.json()[:MAX_POSTS]
    logger.info("Fetched %d posts.", len(posts))
    return posts


def format_post_content(post: dict) -> str:
    """Format a post dict into the text that will be typed into Notepad."""
    return f"Title: {post['title']}\n\n{post['body']}"
