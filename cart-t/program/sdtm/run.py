"""Build the ten SDTM datasets from extracted ODM data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import run_section

if __name__ == "__main__":
    run_section("sdtm")
