import logging
import os
import time

import cv2
import easyocr
import mss
import numpy as np
from botcity.core import DesktopBot

from .settings import (
    ICON_LABEL,
    MAX_GROUNDING_RETRIES,
    RETRY_DELAY_SECONDS,
    REFERENCE_IMAGE_PATH,
    TEMPLATE_CONFIDENCE_THRESHOLD,
    OCR_SIMILARITY_THRESHOLD,
)

logger = logging.getLogger(__name__)


def locate_icon() -> tuple[int, int]:
    """Find the Notepad icon with retries; raise RuntimeError if all attempts fail."""
    for attempt in range(1, MAX_GROUNDING_RETRIES + 1):
        logger.info("Grounding attempt %d/%d ...", attempt, MAX_GROUNDING_RETRIES)
        center = _find_icon()
        if center:
            return center
        if attempt < MAX_GROUNDING_RETRIES:
            logger.warning("Icon not found; retrying in %ss...", RETRY_DELAY_SECONDS)
            time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"Could not locate '{ICON_LABEL}' after {MAX_GROUNDING_RETRIES} attempts. "
        "Ensure a Notepad shortcut is visible on the desktop."
    )


def _find_icon() -> tuple[int, int] | None:
    """Try template matching first; fall back to OCR if it fails or no image exists."""
    if os.path.exists(REFERENCE_IMAGE_PATH):
        center = _template_match()
        if center:
            return center
        logger.warning("Template match failed; falling back to OCR.")
    else:
        logger.warning("Reference image not found at %s; using OCR.", REFERENCE_IMAGE_PATH)

    return _ocr_find()


def _template_match() -> tuple[int, int] | None:
    """Locate the icon using BotCity's image matching against a live desktop screenshot."""
    try:
        bot = DesktopBot()
        bot.add_image(ICON_LABEL, REFERENCE_IMAGE_PATH)
        element = bot.find(ICON_LABEL, matching=TEMPLATE_CONFIDENCE_THRESHOLD, waiting_time=0)
        if element is None:
            logger.debug("BotCity returned no match.")
            return None
        center = (element.left + element.width // 2, element.top + element.height // 2)
        logger.info("BotCity found icon at %s.", center)
        return center
    except Exception as exc:
        logger.warning("BotCity raised an error: %s", exc)
        return None


def _ocr_find() -> tuple[int, int] | None:
    """Use EasyOCR to scan the desktop for the icon label; return center (x, y) or None."""
    logger.info("Running OCR scan for '%s'...", ICON_LABEL)

    with mss.mss() as sct:
        raw = sct.grab(sct.monitors[0])
    screenshot = cv2.cvtColor(np.array(raw), cv2.COLOR_BGRA2RGB)

    reader = easyocr.Reader(["en"], gpu=False)
    best_center, best_score = None, 0.0

    for bbox, text, confidence in reader.readtext(screenshot):
        similarity = _text_similarity(text, ICON_LABEL)
        score = confidence * similarity
        if similarity > OCR_SIMILARITY_THRESHOLD and score > best_score:
            best_score = score
            best_center = _bbox_center(bbox)

    if best_center:
        logger.info("OCR found '%s' at %s.", ICON_LABEL, best_center)
    else:
        logger.warning("OCR could not find '%s'.", ICON_LABEL)
    return best_center


def _text_similarity(found: str, target: str) -> float:
    """Return a bigram overlap ratio between two strings (case-insensitive)."""
    a, b = found.strip().lower(), target.strip().lower()
    if a == b:
        return 1.0
    if b in a or a in b:
        return min(len(a), len(b)) / max(len(a), len(b), 1)
    def bigrams(s):
        return {s[i:i + 2] for i in range(len(s) - 1)}
    denom = len(bigrams(b))
    return len(bigrams(a) & bigrams(b)) / denom if denom else 0.0


def _bbox_center(bbox) -> tuple[int, int]:
    """Return the integer center (x, y) of an EasyOCR bounding box."""
    xs, ys = [p[0] for p in bbox], [p[1] for p in bbox]
    return int(sum(xs) / len(xs)), int(sum(ys) / len(ys))
