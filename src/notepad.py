import logging
import os
import time

import pyautogui
import pygetwindow as gw

from .settings import (
    NOTEPAD_TITLE_FRAGMENT,
    OPEN_TIMEOUT_SECONDS,
    POLL_INTERVAL_SECONDS,
    TYPING_INTERVAL_SECONDS,
    AFTER_OPEN_PAUSE,
    AFTER_DIALOG_PAUSE,
)

logger = logging.getLogger(__name__)


def check_window_opened(title: str = NOTEPAD_TITLE_FRAGMENT) -> bool:
    """Return True immediately if a window matching title is currently visible."""
    return bool(gw.getWindowsWithTitle(title))


def wait_for_notepad(timeout: float = OPEN_TIMEOUT_SECONDS) -> bool:
    """Poll until a Notepad window appears; return True if found within timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if check_window_opened():
            logger.info("Notepad window detected.")
            time.sleep(AFTER_OPEN_PAUSE)
            return True
        time.sleep(POLL_INTERVAL_SECONDS)
    logger.warning("Notepad did not open within %ss.", timeout)
    return False


def focus_notepad() -> bool:
    """Bring the first Notepad window to the foreground; return True on success."""
    windows = gw.getWindowsWithTitle(NOTEPAD_TITLE_FRAGMENT)
    if not windows:
        logger.error("No Notepad window found to focus.")
        return False
    windows[0].activate()
    time.sleep(POLL_INTERVAL_SECONDS)
    return True


def type_content(content: str) -> None:
    """Clear the focused Notepad window and type content into it."""
    focus_notepad()
    pyautogui.hotkey("ctrl", "a")
    pyautogui.press("delete")
    pyautogui.typewrite(content, interval=TYPING_INTERVAL_SECONDS)
    logger.info("Typed %d characters into Notepad.", len(content))


def save_as(file_path: str) -> None:
    """Save the Notepad document to file_path via the Save-As dialog."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    focus_notepad()
    pyautogui.hotkey("ctrl", "shift", "s")
    time.sleep(AFTER_DIALOG_PAUSE)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.typewrite(file_path, interval=TYPING_INTERVAL_SECONDS)
    pyautogui.press("enter")
    time.sleep(AFTER_DIALOG_PAUSE)
    pyautogui.press("enter")  # confirm overwrite if prompted
    time.sleep(POLL_INTERVAL_SECONDS)
    logger.info("Saved file to %s.", file_path)


def close_notepad() -> None:
    """Close Notepad, discarding any unsaved changes."""
    focus_notepad()
    pyautogui.hotkey("alt", "F4")
    time.sleep(POLL_INTERVAL_SECONDS)
    pyautogui.press("n")  # "Don't Save" if prompted
    time.sleep(POLL_INTERVAL_SECONDS)
    logger.info("Notepad closed.")
