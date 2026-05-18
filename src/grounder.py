import logging
import os
import time

import cv2
import easyocr
import mss
import numpy as np
from botcity.core import DesktopBot

from .screenseeker import find_icon as _screenseeker_find
from .settings import (
    ICON_LABEL,
    MAX_GROUNDING_RETRIES,
    RETRY_DELAY_SECONDS,
    REFERENCE_IMAGE_PATH,
    TEMPLATE_CONFIDENCE_THRESHOLD,
    OCR_SIMILARITY_THRESHOLD,
    USE_LLM_GROUNDING,
)

logger = logging.getLogger(__name__)

_ocr_reader: easyocr.Reader | None = None


def _get_ocr_reader() -> easyocr.Reader:
    """Return the cached EasyOCR reader, initialising it on the first call."""
    global _ocr_reader
    if _ocr_reader is None:
        logger.info("Loading EasyOCR model (first use only)...")
        _ocr_reader = easyocr.Reader(["en"], gpu=False)
    return _ocr_reader


def locate_icon() -> tuple[tuple[int, int], float, str]:
    """Find the icon with retries; return (center, confidence, method) or raise."""
    for attempt in range(1, MAX_GROUNDING_RETRIES + 1):
        logger.info("Grounding attempt %d/%d ...", attempt, MAX_GROUNDING_RETRIES)
        result = _find_icon()
        if result:
            return result
        if attempt < MAX_GROUNDING_RETRIES:
            logger.warning("Icon not found; retrying in %ss...", RETRY_DELAY_SECONDS)
            time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"Could not locate '{ICON_LABEL}' after {MAX_GROUNDING_RETRIES} attempts. "
        "Ensure a Notepad shortcut is visible on the desktop."
    )


def _find_icon() -> tuple[tuple[int, int], float, str] | None:
    """Run ScreenSeekeR if USE_LLM_GROUNDING is true; otherwise try template then OCR."""
    if USE_LLM_GROUNDING:
        logger.info("USE_LLM_GROUNDING=true; using ScreenSeekeR only.")
        result = _screenseeker_find()
        if result:
            center, confidence = result
            return center, confidence, "ScreenSeekeR"
        return None

    if os.path.exists(REFERENCE_IMAGE_PATH):
        result = _template_match()
        if result:
            center, confidence = result
            return center, confidence, "Template"
        logger.warning("Template match failed; falling back to OCR.")
    else:
        logger.warning("Reference image not found at %s; using OCR.", REFERENCE_IMAGE_PATH)

    result = _ocr_find()
    if result:
        center, confidence = result
        return center, confidence, "OCR"
    return None


def _template_match() -> tuple[tuple[int, int], float] | None:
    """Locate the icon using BotCity image matching; return (center, confidence) or None."""
    try:
        bot = DesktopBot()
        bot.add_image(ICON_LABEL, REFERENCE_IMAGE_PATH)
        element = bot.find(ICON_LABEL, matching=TEMPLATE_CONFIDENCE_THRESHOLD, waiting_time=0)
        if element is None:
            logger.debug("BotCity returned no match.")
            return None
        center = (element.left + element.width // 2, element.top + element.height // 2)
        logger.info("BotCity found icon at %s.", center)
        return center, TEMPLATE_CONFIDENCE_THRESHOLD
    except Exception as exc:
        logger.warning("BotCity raised an error: %s", exc)
        return None


def _ocr_find() -> tuple[tuple[int, int], float] | None:
    """Use EasyOCR to scan the desktop for the icon label; return (center, confidence) or None."""
    logger.info("Running OCR scan for '%s'...", ICON_LABEL)

    with mss.mss() as sct:
        raw = sct.grab(sct.monitors[0])
    screenshot = cv2.cvtColor(np.array(raw), cv2.COLOR_BGRA2RGB)

    reader = _get_ocr_reader()
    best_center, best_score = None, 0.0

    for bbox, text, confidence in reader.readtext(screenshot):
        similarity = _text_similarity(text, ICON_LABEL)
        score = confidence * similarity
        if similarity > OCR_SIMILARITY_THRESHOLD and score > best_score:
            best_score = score
            best_center = _bbox_center(bbox)

    if best_center:
        logger.info("OCR found '%s' at %s (score %.2f).", ICON_LABEL, best_center, best_score)
        return best_center, best_score
    logger.warning("OCR could not find '%s'.", ICON_LABEL)
    return None


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
    return len(bigrams(a) & bigrams(b)) / denom if denom else 0.0  #handles edge case 


def _bbox_center(bbox) -> tuple[int, int]:
    """Return the integer center (x, y) of an EasyOCR bounding box."""
    xs, ys = [p[0] for p in bbox], [p[1] for p in bbox]
    return int(sum(xs) / len(xs)), int(sum(ys) / len(ys))
