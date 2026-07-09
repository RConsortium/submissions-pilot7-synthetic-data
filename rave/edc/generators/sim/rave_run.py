"""
Run the RAVE causal-DAG simulator end-to-end:
  L0 baseline → A arm → Lt longitudinal → Y outcomes → CRF emission → CSV files.

Usage:
  python -m rave.rave_run [N] [SEED] [PARAMS.json] [OUT_DIR]
"""
from __future__ import annotations
import sys
from pathlib import Path
import time

import numpy as np
import pandas as pd

from .params import default_params, load_params
from .rave_baseline import make_baseline
from .rave_longitudinal import simulate_trajectory
from .rave_outcomes import derive_endpoints
from .rave_emit import EMITTERS


def simulate_one(subj_num: int, rng: np.random.Generator, params: dict):
    p = make_baseline(subj_num, rng, params)
    simulate_trajectory(p, rng, params)
    derive_endpoints(p, rng, params)
    return p


def run(n_patients: int = 197, seed: int = 20100715, params: dict | None = None,
        out_dir: str | None = None) -> dict:
    """Default N=197 matches RAVE enrollment; seed = protocol date 2010-07-15."""
    params = params or default_params()
    rng = np.random.default_rng(seed)
    out_dir = Path(out_dir or Path(__file__).resolve().parent.parent / "RAVE_output" / "crfs")
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows = {form: [] for form in EMITTERS}
    patients = []
    t0 = time.time()
    for i in range(1, n_patients + 1):
        p = simulate_one(i, rng, params)
        patients.append(p)
        for form, fn in EMITTERS.items():
            all_rows[form].extend(fn(p))

    saved = []
    for form, rows in all_rows.items():
        if not rows:
            continue
        df = pd.DataFrame(rows)
        path = out_dir / f"RAVE_CRF_{form}.csv"
        df.to_csv(path, index=False)
        saved.append(path.name)
    print(f"Simulated {n_patients} patients in {time.time()-t0:.1f}s → {len(saved)} CRFs in {out_dir}")
    return {"out_dir": str(out_dir), "files": saved, "patients": patients}


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 197
    SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 20100715
    PARAMS = load_params(sys.argv[3]) if len(sys.argv) > 3 else default_params()
    OUT = sys.argv[4] if len(sys.argv) > 4 else None
    run(N, SEED, PARAMS, OUT)
