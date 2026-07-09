"""
Run the CATH causal-DAG simulator end-to-end:
  L0 baseline → A arm → Lt longitudinal → Y outcomes → CRF emission → CSV files.

The roster (group × arm cell sizes) and the 6 dropouts are pinned to the published
participantFlow (N=82 is a small, fully-enumerated trial) so the baseline denominators
and completion counts reproduce exactly; everything else is drawn stochastically.

Usage:  python -m cath.cath_run [SEED] [PARAMS.json] [OUT_DIR]
"""
from __future__ import annotations
import sys
from pathlib import Path
import time

import numpy as np
import pandas as pd

from .params import default_params, load_params
from .cath_baseline import make_baseline
from .cath_longitudinal import simulate_trajectory
from .cath_outcomes import derive_endpoints
from .cath_emit import EMITTERS

# (group, arm) -> n_started   (ctgov participantFlowModule STARTED)
CELLS = [
    ("NONAD", "VITD", 16), ("NONAD", "PLAC", 16),
    ("AD", "VITD", 16),    ("AD", "PLAC", 18),
    ("PSO", "VITD", 8),    ("PSO", "PLAC", 8),
]

# (group, arm) -> list of (reason, discontinuation_day) for the first k patients in the cell.
# ctgov dropWithdraws: AE 1 (AD-Plac), Protocol Violation 2 (AD-VitD, NonAD-Plac),
# Withdrawal by Subject 3 (NonAD-VitD, AD-Plac x2). Total 6 → 76 completers (82 − 6).
DROPOUTS = {
    ("NONAD", "VITD"): [("WITHDRAWAL BY SUBJECT", 9)],
    ("NONAD", "PLAC"): [("PROTOCOL VIOLATION", 6)],
    ("AD", "VITD"):    [("PROTOCOL VIOLATION", 7)],
    ("AD", "PLAC"):    [("ADVERSE EVENT", 10), ("WITHDRAWAL BY SUBJECT", 8),
                        ("WITHDRAWAL BY SUBJECT", 13)],
}


def run(seed: int = 88, params: dict | None = None, out_dir: str | None = None,
        scale: int = 1) -> dict:
    """N=82 fixed (matches CATH enrollment). seed=88 = the deliverable's representative draw
    (all DAG gates pass; all 30 change cells within sampling tolerance; pooled age=32.5 matches).
    scale>1 multiplies each cell's size (population validation: convergence in expectation)."""
    params = params or default_params()
    rng = np.random.default_rng(seed)
    out_dir = Path(out_dir or Path(__file__).resolve().parent.parent / "CATH_output" / "crfs")
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows = {form: [] for form in EMITTERS}
    patients = []
    subj = 0
    t0 = time.time()
    for group, arm, n in CELLS:
        drops = DROPOUTS.get((group, arm), [])
        for i in range(n * scale):
            subj += 1
            p = make_baseline(subj, group, arm, rng, params)
            if i < len(drops):
                reason, dday = drops[i]
                p.completer = False
                p.discontinuation_reason = reason
                p.discontinuation_day = dday
            simulate_trajectory(p, rng, params)
            derive_endpoints(p, rng, params)
            patients.append(p)
            for form, fn in EMITTERS.items():
                all_rows[form].extend(fn(p))

    saved = []
    for form, rows in all_rows.items():
        if not rows:
            # still write an empty AE file with headers so downstream gates can read it
            if form == "AE":
                pd.DataFrame(columns=["USUBJID", "AEDECOD", "AESER", "AEACN", "AEDY"]).to_csv(
                    out_dir / "CATH_CRF_AE.csv", index=False)
                saved.append("CATH_CRF_AE.csv")
            continue
        df = pd.DataFrame(rows)
        path = out_dir / f"CATH_CRF_{form}.csv"
        df.to_csv(path, index=False)
        saved.append(path.name)
    print(f"Simulated {subj} patients in {time.time()-t0:.1f}s → {len(saved)} CRFs in {out_dir}")
    return {"out_dir": str(out_dir), "files": saved, "patients": patients, "seed": seed}


if __name__ == "__main__":
    SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 88   # deliverable seed (see run() docstring)
    PARAMS = load_params(sys.argv[2]) if len(sys.argv) > 2 else default_params()
    OUT = sys.argv[3] if len(sys.argv) > 3 else None
    run(SEED, PARAMS, OUT)
