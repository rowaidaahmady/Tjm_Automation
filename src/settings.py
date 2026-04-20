import os

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

# Notepad
NOTEPAD_TITLE_FRAGMENT = "Notepad"
OPEN_TIMEOUT_SECONDS = 10
POLL_INTERVAL_SECONDS = 0.5
TYPING_INTERVAL_SECONDS = 0.02
AFTER_OPEN_PAUSE = 1.0
AFTER_DIALOG_PAUSE = 0.5

# Run config — edit these before running
REFERENCE_IMAGE_PATH = DEFAULT_REFERENCE_IMAGE  # path to notepad icon PNG
