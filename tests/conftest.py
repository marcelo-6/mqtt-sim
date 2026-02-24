from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"

path_str = str(SRC_DIR)
if path_str not in sys.path:
    sys.path.insert(0, path_str)
