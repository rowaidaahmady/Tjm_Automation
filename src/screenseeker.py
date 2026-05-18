"""ScreenSeekeR LLM grounding .

A planner LLM proposes candidate regions, a grounder LLM points to the icon
inside each crop, then pixel coordinates are mapped back to the full screenshot.
"""

import json
import logging
import re

import mss
from google import genai
from PIL import Image

from .settings import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    ICON_LABEL,
    LLM_CONFIDENCE,
    SCREENSEEKER_CROP_PADDING,
    SCREENSEEKER_MAX_CANDIDATES,
)

logger = logging.getLogger(__name__)

_client: genai.Client | None = None

Box = tuple[int, int, int, int]


def find_icon() -> tuple[tuple[int, int], float] | None:
    """Plan candidate regions, then ground the icon inside each crop."""
    client = _get_client()
    if client is None:
        logger.warning("GEMINI_API_KEY not set; skipping ScreenSeekeR.")
        return None

    screenshot = _capture_screen()
    candidates = _plan_candidates(client, screenshot)
    if not candidates:
        logger.warning("Planner returned no candidates; grounding full screenshot.")
        candidates = [(0, 0, screenshot.width, screenshot.height)]

    for index, box in enumerate(candidates, start=1):
        logger.info("ScreenSeekeR: grounding candidate %d/%d at %s",
                    index, len(candidates), box)
        center = _ground_in_box(client, screenshot, box)
        if center is None:
            continue
        logger.info("ScreenSeekeR located '%s' at %s via candidate %d.",
                    ICON_LABEL, center, index)
        return center, LLM_CONFIDENCE

    logger.warning("ScreenSeekeR exhausted all candidates without a hit.")
    return None


def _get_client() -> genai.Client | None:
    """Lazily build and cache the Gemini client."""
    global _client
    if _client is None and GEMINI_API_KEY:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def _capture_screen() -> Image.Image:
    """Grab the full desktop as a PIL Image."""
    with mss.mss() as sct:
        raw = sct.grab(sct.monitors[0])
    return Image.frombytes("RGB", raw.size, raw.rgb)


def _plan_candidates(client: genai.Client, image: Image.Image) -> list[Box]:
    """Planner stage: ask Gemini for candidate bboxes in descending probability."""
    prompt = (
        f"You are a GUI planner. Identify regions of this desktop screenshot most likely "
        f"to contain the '{ICON_LABEL}' icon. Reply with ONLY JSON of the form "
        f'{{"candidates": [{{"box_2d": [ymin, xmin, ymax, xmax]}}]}} '
        f"with coordinates normalized 0-1000. List up to {SCREENSEEKER_MAX_CANDIDATES} "
        f"regions in descending probability. No other text."
    )
    data = _ask(client, prompt, image)
    if not data:
        return []

    boxes: list[Box] = []
    for item in data.get("candidates", [])[:SCREENSEEKER_MAX_CANDIDATES]:
        box = _denormalize_box(item.get("box_2d") if isinstance(item, dict) else None,
                               image.width, image.height)
        if box:
            boxes.append(box)
    return boxes


def _ground_in_box(client: genai.Client, image: Image.Image, box: Box) -> tuple[int, int] | None:
    """Grounder stage: crop the box, ask for the icon point, map back to full-image pixels."""
    x0, y0, x1, y1 = box
    crop = image.crop(box)
    if crop.width == 0 or crop.height == 0:
        return None

    prompt = (
        f"This is a cropped region of a desktop screenshot. Locate the '{ICON_LABEL}' icon. "
        f'Reply with ONLY JSON of the form {{"point": [y, x]}} normalized 0-1000 to this '
        f'crop, marking the icon center. If the icon is not visible here, reply '
        f'{{"point": null}}. No other text.'
    )
    data = _ask(client, prompt, crop)
    point = data.get("point") if data else None
    if not (isinstance(point, list) and len(point) == 2):
        return None
    try:
        y_norm, x_norm = float(point[0]), float(point[1])
    except (TypeError, ValueError):
        return None

    x = int(x0 + x_norm / 1000 * crop.width)
    y = int(y0 + y_norm / 1000 * crop.height)
    return x, y


def _denormalize_box(box: object, width: int, height: int) -> Box | None:
    """Convert a [ymin, xmin, ymax, xmax] 0-1000 bbox to padded pixel coords."""
    if not (isinstance(box, list) and len(box) == 4):
        return None
    try:
        ymin, xmin, ymax, xmax = (float(v) for v in box)
    except (TypeError, ValueError):
        return None
    pad = SCREENSEEKER_CROP_PADDING
    x0 = max(0, int(xmin / 1000 * width) - pad)
    y0 = max(0, int(ymin / 1000 * height) - pad)
    x1 = min(width, int(xmax / 1000 * width) + pad)
    y1 = min(height, int(ymax / 1000 * height) + pad)
    return (x0, y0, x1, y1) if x1 > x0 and y1 > y0 else None


def _ask(client: genai.Client, prompt: str, image: Image.Image) -> dict | None:
    """Send prompt + image to Gemini and return the first JSON object in the reply."""
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[image, prompt],
        )
    except Exception as exc:
        logger.warning("Gemini request failed: %s", exc)
        return None

    text = response.text or ""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        logger.warning("Gemini reply contained no JSON object: %r", text)
        return None
    try:
        result = json.loads(match.group(0))
    except json.JSONDecodeError:
        logger.warning("Gemini reply was invalid JSON: %r", text)
        return None
    return result if isinstance(result, dict) else None
