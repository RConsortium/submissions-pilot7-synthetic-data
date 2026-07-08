"""
Run the ARA06 causal-DAG simulator end-to-end:
  L0 baseline -> A arm -> Lt longitudinal -> Y outcomes -> CRF emission -> CSVs.

Usage:
  python -m ara06.ara06_run [N] [SEED] [PARAMS.json] [OUT_DIR]
Default N=63 matches ctgov enrollment (43 ETN + 20 ADA); seed = study start 2009-03-01.
"""
from __future__ import annotations
import sys, time
from pathlib import Path

import numpy as np
import pandas as pd

from .params import default_params, load_params
from .ara06_baseline import make_baseline
from .ara06_longitudinal import simulate_trajectory
from .ara06_outcomes import derive_endpoints
from .ara06_emit import EMITTERS


def simulate_one(subj_num, rng, params):
    p = make_baseline(subj_num, rng, params)
    simulate_trajectory(p, rng, params)
    derive_endpoints(p, rng, params)
    return p


def run(n_patients: int = 63, seed: int = 20090301, params: dict | None = None,
        out_dir: str | None = None) -> dict:
    params = params or default_params()
    rng = np.random.default_rng(seed)
    out_dir = Path(out_dir or Path(__file__).resolve().parent.parent / "ARA06_output" / "crfs")
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
        pd.DataFrame(rows).to_csv(out_dir / f"ARA06_CRF_{form}.csv", index=False)
        saved.append(f"ARA06_CRF_{form}.csv")
    print(f"Simulated {n_patients} patients in {time.time()-t0:.2f}s -> {len(saved)} CRFs in {out_dir}")
    return {"out_dir": str(out_dir), "files": saved, "patients": patients}


if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 63
    SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 20090301
    PARAMS = load_params(sys.argv[3]) if len(sys.argv) > 3 else default_params()
    OUT = sys.argv[4] if len(sys.argv) > 4 else None
    run(N, SEED, PARAMS, OUT)
