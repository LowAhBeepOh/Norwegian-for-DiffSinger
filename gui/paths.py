"""Project-relative paths shared by the GUI and its logic modules."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PHONEMES_FILE = PROJECT_ROOT / "phonemes.txt"
CREDITS_FILE = PROJECT_ROOT / "CREDITS.md"
REQUIREMENTS_FILE = Path(__file__).resolve().parent / "requirements.txt"
# Downloaded models, MFA corpus staging and NoFA files live here (git-ignored).
TOOLS_DIR = PROJECT_ROOT / ".nofa_tools"
