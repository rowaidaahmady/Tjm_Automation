import logging
import msvcrt
import os
import time

import pyautogui

from .api_client import fetch_posts, format_post_content
from .grounder import locate_icon
from .utils import take_screenshot, annotate_screenshot, save_annotated_screenshot
from . import notepad
from .settings import (
    ANNOTATE,
    BETWEEN_POST_PAUSE,
    CACHE_VERIFY_PAUSE,
    DOUBLE_CLICK_PAUSE,
    ICON_LABEL,
    NOTEPAD_TITLE_FRAGMENT,
    OUTPUT_DIR,
    SHOW_DESKTOP_PAUSE,
)

logger = logging.getLogger(__name__)


def run_workflow() -> None:
    """Fetch 10 posts, open Notepad for each, type the content, and save it."""
    logger.info("Showing desktop...")
    pyautogui.hotkey("win", "d")
    time.sleep(SHOW_DESKTOP_PAUSE)

    posts = fetch_posts()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    cached_center = None

    for post in posts:
        if msvcrt.kbhit() and msvcrt.getch() == b"\x1b":
            logger.warning("ESC pressed — stopping workflow.")
            break

        post_id = post["id"]
        logger.info("--- Processing post %d ---", post_id)

        desktop_shot = take_screenshot() if ANNOTATE else None
        center = _open_notepad(cached_center)
        cached_center = center

        if ANNOTATE:
            save_annotated_screenshot(annotate_screenshot(desktop_shot, center, ICON_LABEL), post_id)

        notepad.type_content(format_post_content(post))
        notepad.save_as(os.path.join(OUTPUT_DIR, f"post_{post_id}.txt"))
        notepad.close_notepad()

        logger.info("Finished post %d.", post_id)
        time.sleep(BETWEEN_POST_PAUSE)

    logger.info("All posts processed. Files saved to %s", OUTPUT_DIR)


def _open_notepad(cached_center: tuple[int, int] | None) -> tuple[int, int]:
    """Try cached coordinates first; re-ground and retry if Notepad does not open."""
    if cached_center:
        pyautogui.doubleClick(*cached_center)
        time.sleep(CACHE_VERIFY_PAUSE)
        if notepad.check_window_opened(NOTEPAD_TITLE_FRAGMENT):
            logger.info("Notepad opened using cached coordinates %s.", cached_center)
            return cached_center
        logger.info("Cached coordinates did not open Notepad; re-grounding...")

    center = locate_icon()
    pyautogui.doubleClick(*center)
    time.sleep(DOUBLE_CLICK_PAUSE)
    if not notepad.wait_for_notepad():
        raise RuntimeError(f"Notepad did not open after clicking at {center}.")
    return center
