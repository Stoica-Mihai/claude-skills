"""Make the top-level `app` module importable from tests/smoke/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
