"""Configuration seam for the RAVE EDC generator.

The *default* config reproduces the committed RAVE EDC (CRF) extract: the
published run is ``python -m rave.rave_run 197 123`` (N=197, seed=123). Change
``n_patients`` / ``seed`` (or pass a calibrated ``params`` dict) for a fresh,
internally-consistent cohort.

Unlike cdiscpilot1 (which samples down from a canonical SDTM truth), this study
simulates up from a g-formula structural causal model; there is no SDTM ground
truth, so the downstream SDTM stage is validated for CDISC conformance.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

EDC_DIR = Path(__file__).resolve().parent.parent     # .../rave/edc/


@dataclass
class GenConfig:
    out_dir: Path = EDC_DIR            # forms/ are written under here
    n_patients: int = 197              # RAVE enrollment (RTX 95 / CYC 102)
    seed: int = 123                    # published run seed (reproduces committed CRFs)
    params: "dict | None" = None       # None => calibrated default_params()

    def __post_init__(self) -> None:
        self.out_dir = Path(self.out_dir)
