"""Build the CATH synthetic EDC (CRF) extract from the causal-DAG simulator.

    python3 -m generators.build_all

With the default config this reproduces the committed CATH CRFs (N=82, seed=88).
Pass a GenConfig (different seed / scale / params) to build_edc() to vary it.

Outputs one ``CATH_CRF_<form>.csv`` per CRF page under ``<out_dir>/forms`` — the
raw EDC layer the sdtm/ stage derives SDTM from.
"""

from __future__ import annotations

from pathlib import Path

from .config import GenConfig
from .sim.cath_run import run
from .sim.params import default_params


def build_edc(cfg: "GenConfig | None" = None) -> Path:
    cfg = cfg or GenConfig()
    forms = Path(cfg.out_dir) / "forms"
    forms.mkdir(parents=True, exist_ok=True)
    params = cfg.params or default_params()
    print(f"Building CATH synthetic EDC under {forms} (seed={cfg.seed}, scale={cfg.scale})")
    run(seed=cfg.seed, params=params, out_dir=str(forms), scale=cfg.scale)
    return forms


if __name__ == "__main__":
    build_edc()
