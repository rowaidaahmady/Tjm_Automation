import os


def _load_env_file(path: str) -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ (without overriding)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(os.path.join(os.path.dirname(__file__), "..", ".env"))


# API
POSTS_URL = "https://jsonplaceholder.typicode.com/posts"
REQUEST_TIMEOUT_SECONDS = 10
MAX_POSTS = 10

# Workflow
MAX_GROUNDING_RETRIES = 3
RETRY_DELAY_SECONDS = 1.0
BETWEEN_POST_PAUSE = 1.5
SHOW_DESKTOP_PAUSE = 1.0  # seconds to wait after Win+D before grounding
DOUBLE_CLICK_PAUSE = 0.3
CACHE_VERIFY_PAUSE = 1.0   # seconds to wait after clicking cached coords before checking window
ICON_LABEL = "Notepad"
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "tjm-project")
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "screenshots")

# Grounding
TEMPLATE_CONFIDENCE_THRESHOLD = 0.7
OCR_SIMILARITY_THRESHOLD = 0.6
DEFAULT_REFERENCE_IMAGE = os.path.join(os.path.dirname(__file__), "resources", "notepad_icon.png")

# LLM grounding fallback — ScreenSeekeR (ScreenSpot-Pro, arXiv:2504.07981):
# a planner proposes candidate regions, then a grounder zooms into each crop.
# Values below come from the .env file at the project root.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
LLM_CONFIDENCE = float(os.environ.get("LLM_CONFIDENCE", "0.8"))
SCREENSEEKER_MAX_CANDIDATES = int(os.environ.get("SCREENSEEKER_MAX_CANDIDATES", "3"))
SCREENSEEKER_CROP_PADDING = int(os.environ.get("SCREENSEEKER_CROP_PADDING", "20"))

# Notepad
NOTEPAD_TITLE_FRAGMENT = "Notepad"
OPEN_TIMEOUT_SECONDS = 10
POLL_INTERVAL_SECONDS = 0.5
TYPING_INTERVAL_SECONDS = 0.02
AFTER_OPEN_PAUSE = 1.0
AFTER_DIALOG_PAUSE = 0.5

# Run config — edit these before running
REFERENCE_IMAGE_PATH = DEFAULT_REFERENCE_IMAGE  # path to notepad icon PNG
