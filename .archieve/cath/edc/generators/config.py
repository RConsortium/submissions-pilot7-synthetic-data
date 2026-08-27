"""Configuration seam for the CATH EDC generator.

The *default* config reproduces the committed CATH EDC (CRF) extract: the
published run is ``python -m cath.cath_run 88`` (seed=88), N=82 fixed by the
6-cell design (Non-AD/AD/Pso x VitD/Placebo). Change ``seed`` (or pass a
calibrated ``params`` dict) for a fresh internally-consistent cohort; ``scale``
multiplies every design cell for population-level validation.

Unlike cdiscpilot1 (which samples down from a canonical SDTM truth), this study
simulates up from a g-formula structural causal model; there is no SDTM ground
truth, so the downstream SDTM stage is validated for CDISC conformance.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

EDC_DIR = Path(__file__).resolve().parent.parent     # .../cath/edc/


@dataclass
class GenConfig:
    out_dir: Path = EDC_DIR            # forms/ are written under here
    seed: int = 88                     # published run seed (reproduces committed CRFs)
    scale: int = 1                     # >1 multiplies each design cell (pop. validation)
    params: "dict | None" = None       # None => calibrated default_params()

    def __post_init__(self) -> None:
        self.out_dir = Path(self.out_dir)
