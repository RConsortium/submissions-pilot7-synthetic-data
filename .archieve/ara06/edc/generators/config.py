"""Configuration seam for the ARA06 EDC generator.

The *default* config reproduces the committed ARA06 EDC (CRF) extract exactly:
the published run is ``python -m ara06.ara06_run 63 2009`` (N=63, seed=2009), so
the defaults here match. Change ``n_patients`` / ``seed`` (or pass a calibrated
``params`` dict) to make the EDC dynamic — the simulator is a g-formula causal-DAG
forward model, so a different seed yields a fresh, internally-consistent cohort.

Unlike cdiscpilot1 (which *samples down* from a canonical SDTM truth), this study
*simulates up* from a structural causal model; there is no SDTM ground truth, so
the downstream SDTM stage is validated for CDISC conformance, not round-trip.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# .../ara06/edc/  (parent of the generators package; receives forms/).
EDC_DIR = Path(__file__).resolve().parent.parent


@dataclass
class GenConfig:
    out_dir: Path = EDC_DIR            # forms/ are written under here
    n_patients: int = 63               # ctgov enrollment (43 ETN + 20 ADA)
    seed: int = 2009                   # published run seed (reproduces committed CRFs)
    params: "dict | None" = None       # None => calibrated default_params()

    def __post_init__(self) -> None:
        self.out_dir = Path(self.out_dir)
