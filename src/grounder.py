import base64
import json
import logging
import os
import re
import time

import cv2
import easyocr
import mss
import numpy as np
import requests
from botcity.core import DesktopBot

from .settings import (
    GEMINI_API_KEY,
    GEMINI_API_URL,
    GEMINI_MODEL,
    ICON_LABEL,
    LLM_CONFIDENCE,
    LLM_REQUEST_TIMEOUT,
    MAX_GROUNDING_RETRIES,
    RETRY_DELAY_SECONDS,
    REFERENCE_IMAGE_PATH,
    SCREENSEEKER_CROP_PADDING,
    SCREENSEEKER_MAX_CANDIDATES,
    TEMPLATE_CONFIDENCE_THRESHOLD,
    OCR_SIMILARITY_THRESHOLD,
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
    """Try template matching, then OCR, then LLM. Returns (center, confidence, method)."""
    # if os.path.exists(REFERENCE_IMAGE_PATH):
    #     result = _template_match()
    #     if result:
    #         center, confidence = result
    #         return center, confidence, "Template"
    #     logger.warning("Template match failed; falling back to OCR.")
    # else:
    #     logger.warning("Reference image not found at %s; using OCR.", REFERENCE_IMAGE_PATH)

    # result = _ocr_find()
    # if result:
    #     center, confidence = result
    #     return center, confidence, "OCR"

    logger.warning("OCR failed; falling back to ScreenSeekeR (LLM).")
    result = _screenseeker_find()
    if result:
        center, confidence = result
        return center, confidence, "ScreenSeekeR"
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


def _screenseeker_find() -> tuple[tuple[int, int], float] | None:
    """ScreenSeekeR (arXiv:2504.07981): planner proposes regions, grounder zooms into each."""
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set; skipping ScreenSeekeR.")
        return None

    with mss.mss() as sct:
        raw = sct.grab(sct.monitors[0])
    screenshot = cv2.cvtColor(np.array(raw), cv2.COLOR_BGRA2RGB)
    height, width = screenshot.shape[:2]

    logger.info("ScreenSeekeR: planning candidate regions for '%s'...", ICON_LABEL)
    candidates = _plan_candidates(screenshot)
    if not candidates:
        logger.warning("Planner returned no candidates; grounding full screenshot.")
        candidates = [(0, 0, width, height)]

    for index, (x0, y0, x1, y1) in enumerate(candidates, start=1):
        logger.info("ScreenSeekeR: grounding candidate %d/%d at %s...",
                    index, len(candidates), (x0, y0, x1, y1))
        crop = screenshot[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        point = _ground_in_crop(crop)
        if point is None:
            continue
        y_norm, x_norm = point
        crop_h, crop_w = crop.shape[:2]
        x = int(x0 + x_norm / 1000 * crop_w)
        y = int(y0 + y_norm / 1000 * crop_h)
        logger.info("ScreenSeekeR located '%s' at (%d, %d) via candidate %d.",
                    ICON_LABEL, x, y, index)
        return (x, y), LLM_CONFIDENCE

    logger.warning("ScreenSeekeR exhausted all candidates without a hit.")
    return None


def _plan_candidates(image: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Planner stage: ask the LLM for candidate bboxes in descending probability."""
    height, width = image.shape[:2]
    prompt = (
        f"You are a GUI planner. Identify the regions of this desktop screenshot most likely to "
        f"contain the '{ICON_LABEL}' icon. Reply with ONLY a JSON object of the form "
        f"{{\"candidates\": [{{\"box_2d\": [ymin, xmin, ymax, xmax]}}]}} where coordinates are "
        f"normalized 0-1000. List up to {SCREENSEEKER_MAX_CANDIDATES} regions in descending "
        f"probability. No other text."
    )
    text = _gemini_call(prompt, image)
    if text is None:
        return []

    data = _parse_json_object(text)
    if not data:
        logger.warning("Planner reply was not parseable JSON: %r", text)
        return []

    bboxes: list[tuple[int, int, int, int]] = []
    for item in data.get("candidates", [])[:SCREENSEEKER_MAX_CANDIDATES]:
        box = item.get("box_2d") if isinstance(item, dict) else None
        if not (isinstance(box, list) and len(box) == 4):
            continue
        try:
            ymin, xmin, ymax, xmax = (float(v) for v in box)
        except (TypeError, ValueError):
            continue
        x0 = max(0, int(xmin / 1000 * width) - SCREENSEEKER_CROP_PADDING)
        y0 = max(0, int(ymin / 1000 * height) - SCREENSEEKER_CROP_PADDING)
        x1 = min(width, int(xmax / 1000 * width) + SCREENSEEKER_CROP_PADDING)
        y1 = min(height, int(ymax / 1000 * height) + SCREENSEEKER_CROP_PADDING)
        if x1 > x0 and y1 > y0:
            bboxes.append((x0, y0, x1, y1))
    return bboxes


def _ground_in_crop(crop: np.ndarray) -> tuple[float, float] | None:
    """Grounder stage: ask the LLM for the icon point inside a cropped region."""
    prompt = (
        f"This is a cropped region of a desktop screenshot. Locate the '{ICON_LABEL}' icon "
        f"inside it. Reply with ONLY a JSON object of the form {{\"point\": [y, x]}} where "
        f"y and x are normalized 0-1000 to this crop and mark the icon center. "
        f"If the icon is not visible in this crop, reply {{\"point\": null}}. No other text."
    )
    text = _gemini_call(prompt, crop)
    if text is None:
        return None

    data = _parse_json_object(text)
    if not data:
        return None
    point = data.get("point")
    if not (isinstance(point, list) and len(point) == 2):
        return None
    try:
        return float(point[0]), float(point[1])
    except (TypeError, ValueError):
        return None


def _gemini_call(prompt: str, image: np.ndarray) -> str | None:
    """POST an image+prompt to Gemini and return the reply text, or None on failure."""
    ok, buf = cv2.imencode(".png", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    if not ok:
        logger.warning("Failed to encode image for Gemini.")
        return None
    image_b64 = base64.b64encode(buf.tobytes()).decode("ascii")
    body = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/png", "data": image_b64}},
            ]
        }]
    }
    try:
        response = requests.post(
            GEMINI_API_URL.format(model=GEMINI_MODEL),
            params={"key": GEMINI_API_KEY},
            json=body,
            timeout=LLM_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as exc:
        logger.warning("Gemini request failed: %s", exc)
        return None


def _parse_json_object(text: str) -> dict | None:
    """Extract the first JSON object from text, tolerating code fences and stray prose."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        result = json.loads(match.group(0))
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        return None
