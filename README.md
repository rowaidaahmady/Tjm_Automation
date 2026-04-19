# Desktop Automator

A Python desktop automation tool that dynamically locates the Notepad icon on a
Windows desktop using computer vision, then fetches 10 posts from a public API and
saves each one as a `.txt` file — fully hands-free.

---

## Prerequisites

- Windows 10 / 11
- A **Notepad shortcut visible on the desktop** (the tool looks for the icon there)
- [Python 3.11+](https://python.org)
- [uv](https://docs.astral.sh/uv/) — `pip install uv`

---

## Installation

```bash
uv sync
```

---

## Usage

```bash
# BotCity template-matching strategy
uv run automate --grounding botcity

# OCR text-detection strategy
uv run automate --grounding ocr

# Save annotated screenshots (green bounding box) to screenshots/
uv run automate --grounding botcity --annotate
uv run automate --grounding ocr --annotate

# Supply a custom reference image for BotCity
uv run automate --grounding botcity --reference-image path/to/notepad_icon.png
```

Output files are written to `~/Desktop/tjm-project/post_1.txt … post_10.txt`.

---

## Grounding Strategies

### Strategy 1 — BotCity (`--grounding botcity`)

Uses **template matching** (via BotCity's vision engine or OpenCV as a fallback) to
compare a reference crop of the Notepad icon against the live desktop screenshot.

**Works best when:** the Notepad icon looks identical (or very similar) to the
reference image — same OS theme, same icon pack, no heavy scaling.

**Limitation:** fails if the icon appearance changes (different theme, custom icon,
DPI scaling without a matching reference).

### Strategy 2 — OCR (`--grounding ocr`)

Uses **EasyOCR** to scan the desktop for the text label *"Notepad"* that appears
beneath the icon. No reference image needed — pure text recognition.

**Works best when:** the icon label is clearly readable and not obscured by other
windows or wallpaper patterns.

**Limitation:** may misfire if another item on the desktop has "Notepad" in its name,
or if the desktop font is very small / anti-aliased in a way OCR struggles with.

---

## Known Limitations

| Scenario | Behaviour |
| --- | --- |
| Notepad icon not on desktop | Raises an error after 3 retries |
| API unreachable | Raises `RuntimeError` with a clear message |
| DPI > 100 % (BotCity) | May need a reference image captured at that DPI |
| Notepad "new tab" version (Win 11) | Save-As dialog path may differ; tested on classic Notepad |
| Multiple "Notepad" text on desktop | OCR picks the highest-confidence match |

---

## Project Structure

```text
Tjm_Automation/
├── main.py                          # CLI entry point
├── pyproject.toml                   # uv / hatchling config
├── screenshots/                     # annotated output screenshots
└── src/
    ├── api_client.py                # fetch posts from JSONPlaceholder
    ├── notepad.py                   # Notepad launch / type / save / close
    ├── workflow.py                  # 10-post orchestration loop
    └── grounding/
        ├── base.py                  # GroundingStrategy ABC
        ├── botcity_grounder.py      # BotCity / OpenCV template matching
        └── ocr_grounder.py          # EasyOCR text detection
```
