"""ara06 environment — causal-DAG IPD simulator (EDC) + CRF->SDTM derivation.

ARA06 / NCT00837434: Phase IV 2:1 etanercept vs adalimumab in rheumatoid
arthritis. Unlike cdiscpilot1 (which samples an EDC down from a canonical SDTM
truth), this study *simulates up* from a g-formula structural causal model, so
there is NO SDTM ground truth — the SDTM stage is validated for CDISC conformance
(CORE rules), not round-trip exactness.

Layout (two pipeline stages under this package directory)::

    edc/    generators/ (causal-DAG simulator) -> forms/ (generated CRFs)
            lookups/ (visit schedule)  metadata/ (DAG, CRF spec, intake, params)
    sdtm/   derive_<domain>.R + common.R + run_all.R + validate_sdtm.py (CRF -> SDTM)
            sdtm-derived/  (per-domain CSV)

Use directly::

    from cdt.environments.ara06 import generate_edc, generate_sdtm, GenConfig

    edc = generate_edc(out_dir="/tmp/ara06")          # fresh CRF extract
    sdtm = generate_sdtm(out_dir="/tmp/ara06", seed=7) # EDC -> SDTM CSVs
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDC_DIR = HERE / "edc"               # simulator + generated CRF forms
DERIVE_DIR = HERE / "sdtm"           # CRF -> SDTM derivation programs
SDTM_DERIVED = HERE / "sdtm" / "sdtm-derived"

# The generator lives under edc/ as a `generators` package. Put edc/ on sys.path
# so it imports as the top-level `generators` package (matching cdiscpilot1).
if str(EDC_DIR) not in sys.path:
    sys.path.insert(0, str(EDC_DIR))
from generators.config import GenConfig            # noqa: E402
from generators.build_all import build_edc as _build_edc  # noqa: E402


def generate_edc(out_dir=None, n_patients: int = 63, seed: int = 2009,
                 params=None) -> Path:
    """Generate a fresh EDC (CRF) extract via the causal-DAG simulator.

    out_dir    : where to write the extract (None = the env's own edc/); CRFs land
                 under ``<out_dir>/forms``.
    n_patients : cohort size (default 63 = ctgov enrollment).
    seed       : RNG seed (default 2009 reproduces the committed CRFs).
    params     : calibrated parameter dict, or None for the default.
    Returns the forms directory.
    """
    cfg = GenConfig(out_dir=out_dir or EDC_DIR, n_patients=n_patients,
                    seed=seed, params=params)
    return _build_edc(cfg)


def generate_sdtm(out_dir, n_patients: int = 63, seed: int = 2009,
                  domains=None) -> Path:
    """Generate SDTM end to end (EDC -> SDTM).

    1. ``generate_edc`` writes a fresh CRF extract to ``<out_dir>/edc/forms``.
    2. ``sdtm/run_all.R`` derives every SDTM domain to ``<out_dir>/sdtm`` (CSV).

    out_dir  : run directory (EDC -> ``<out_dir>/edc``, SDTM -> ``<out_dir>/sdtm``).
    domains  : restrict to these SDTM domains (None = all).
    Returns the SDTM output directory.
    """
    out = Path(out_dir)
    edc = out / "edc"
    sdtm = out / "sdtm"
    sdtm.mkdir(parents=True, exist_ok=True)
    generate_edc(out_dir=edc, n_patients=n_patients, seed=seed)
    # The visit lookup is a hand-curated input the simulator does not emit; copy it
    # alongside the freshly generated forms so the derivation can read it.
    import shutil
    (edc / "lookups").mkdir(parents=True, exist_ok=True)
    shutil.copy(EDC_DIR / "lookups" / "visit_schedule.csv", edc / "lookups")

    env = os.environ.copy()
    rscript = env.get("RSCRIPT", "Rscript")
    env["ARA06_EDC_DIR"] = str(edc)
    env["ARA06_SDTM_OUT"] = str(sdtm)
    cmd = [rscript, str(DERIVE_DIR / "run_all.R"), *(list(domains) if domains else [])]
    subprocess.run(cmd, env=env, check=True)
    return sdtm


__all__ = ["GenConfig", "generate_edc", "generate_sdtm",
           "EDC_DIR", "DERIVE_DIR", "SDTM_DERIVED"]
