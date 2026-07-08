"""Build the RAVE synthetic EDC (CRF) extract from the causal-DAG simulator.

    python3 -m generators.build_all

With the default config this reproduces the committed RAVE CRFs (N=197, seed=123).
Pass a GenConfig (different n_patients / seed / params) to build_edc() to vary it.

Outputs one ``RAVE_CRF_<form>.csv`` per CRF page under ``<out_dir>/forms`` — the
raw EDC layer the sdtm/ stage derives SDTM from.
"""

from __future__ import annotations

from pathlib import Path

from .config import GenConfig
from .sim.rave_run import run
from .sim.params import default_params


def build_edc(cfg: "GenConfig | None" = None) -> Path:
    cfg = cfg or GenConfig()
    forms = Path(cfg.out_dir) / "forms"
    forms.mkdir(parents=True, exist_ok=True)
    params = cfg.params or default_params()
    print(f"Building RAVE synthetic EDC under {forms} (N={cfg.n_patients}, seed={cfg.seed})")
    run(n_patients=cfg.n_patients, seed=cfg.seed, params=params, out_dir=str(forms))
    return forms


if __name__ == "__main__":
    build_edc()
