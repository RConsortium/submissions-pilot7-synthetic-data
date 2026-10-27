"""Build nine ADaM datasets, starting with ADSL, from published SDTM."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import run_section

if __name__ == "__main__":
    run_section("adam")
