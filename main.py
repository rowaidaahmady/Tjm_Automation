import logging
import sys

from src.workflow import run_workflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")


def main() -> None:
    """Run the desktop automation workflow."""
    try:
        run_workflow()
    except RuntimeError as exc:
        logging.error("Automation failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
