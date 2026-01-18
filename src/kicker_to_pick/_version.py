from pathlib import Path

VERSION_FILE = Path(__file__).resolve().parents[2] / "VERSION"
BASE_VERSION = VERSION_FILE.read_text().strip()

__version__ = BASE_VERSION
