"""rave environment — causal-DAG IPD simulator (EDC) + CRF->SDTM derivation.

RAVE / NCT00104299 (ITN021AI): randomized, double-blind, double-dummy trial of
rituximab vs cyclophosphamide->azathioprine for remission induction in
ANCA-associated vasculitis, over 18 months. Like the other environments it
*simulates up* from a g-formula structural causal model, so there is NO SDTM
ground truth — the SDTM stage is validated for CDISC conformance (CORE rules),
not round-trip exactness.

Layout::

    edc/    generators/ (causal-DAG simulator) -> forms/ (12 generated CRFs)
            lookups/ (visit schedule)  metadata/ (DAG, CRF spec, intake, params)
    sdtm/   derive_<domain>.R + common.R + run_all.R + validate_sdtm.py (CRF -> SDTM)
            sdtm-derived/  (per-domain CSV)

Use directly::

    from cdt.environments.rave import generate_edc, generate_sdtm, GenConfig

    edc = generate_edc(out_dir="/tmp/rave")            # fresh CRF extract
    sdtm = generate_sdtm(out_dir="/tmp/rave", seed=7)  # CRF -> SDTM CSVs
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDC_DIR = HERE / "edc"
DERIVE_DIR = HERE / "sdtm"
SDTM_DERIVED = HERE / "sdtm" / "sdtm-derived"

if str(EDC_DIR) not in sys.path:
    sys.path.insert(0, str(EDC_DIR))
from generators.config import GenConfig            # noqa: E402
from generators.build_all import build_edc as _build_edc  # noqa: E402


def generate_edc(out_dir=None, n_patients: int = 197, seed: int = 123,
                 params=None) -> Path:
    """Generate a fresh EDC (CRF) extract via the causal-DAG simulator.

    out_dir    : where to write the extract (None = the env's own edc/); CRFs land
                 under ``<out_dir>/forms``.
    n_patients : cohort size (default 197 = RAVE enrollment).
    seed       : RNG seed (default 123 reproduces the committed CRFs).
    params     : calibrated parameter dict, or None for the default.
    """
    cfg = GenConfig(out_dir=out_dir or EDC_DIR, n_patients=n_patients,
                    seed=seed, params=params)
    return _build_edc(cfg)


def generate_sdtm(out_dir, n_patients: int = 197, seed: int = 123,
                  domains=None) -> Path:
    """Generate SDTM end to end (EDC -> SDTM).

    1. ``generate_edc`` writes a fresh CRF extract to ``<out_dir>/edc/forms``.
    2. ``sdtm/run_all.R`` derives every SDTM domain to ``<out_dir>/sdtm`` (CSV).
    """
    out = Path(out_dir)
    edc = out / "edc"
    sdtm = out / "sdtm"
    sdtm.mkdir(parents=True, exist_ok=True)
    generate_edc(out_dir=edc, n_patients=n_patients, seed=seed)
    import shutil
    (edc / "lookups").mkdir(parents=True, exist_ok=True)
    shutil.copy(EDC_DIR / "lookups" / "visit_schedule.csv", edc / "lookups")

    env = os.environ.copy()
    rscript = env.get("RSCRIPT", "Rscript")
    env["RAVE_EDC_DIR"] = str(edc)
    env["RAVE_SDTM_OUT"] = str(sdtm)
    cmd = [rscript, str(DERIVE_DIR / "run_all.R"), *(list(domains) if domains else [])]
    subprocess.run(cmd, env=env, check=True)
    return sdtm


__all__ = ["GenConfig", "generate_edc", "generate_sdtm",
           "EDC_DIR", "DERIVE_DIR", "SDTM_DERIVED"]
