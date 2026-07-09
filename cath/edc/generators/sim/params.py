"""
CATH simulator parameters — the ONLY tunable surface for the Step-6 calibration loop.
Calibration adjusts these values; it never changes model structure (no new edges, no
direct arm→endpoint draws). Per-cell baseline and outcome means/SDs are read from
`CATH_output/intake/targets.json` (single source of truth = the posted CTGov results);
the knobs below govern the structural equations that reproduce them.

Load/override at runtime from a params/*.json snapshot for reproducible runs.
"""
from __future__ import annotations
import json
from pathlib import Path
from copy import deepcopy

from .dag_state import GROUP_LBL, ARM_LBL, SKIN_LBL

# Vendored into environments/cath/edc/generators/sim/ ; the ctgov targets live
# under the env's edc/metadata/intake/ (parents[2] = .../cath/edc).
_TARGETS_PATH = Path(__file__).resolve().parents[2] / "metadata" / "intake" / "targets.json"
TARGETS = json.loads(_TARGETS_PATH.read_text())


DEFAULT_PARAMS = {
    # ---- treatment mediator: serum 25-OH-D rise over 21 days (drives biopsy δ) ----
    # paperclip: 4000 IU/d raises 25(OH)D well within safe range over weeks.
    "vitd_rise_mean": 10.0, "vitd_rise_sd": 4.0,   # VITD arm Δ25OHD (ng/mL)
    "plac_rise_mean": 0.3,  "plac_rise_sd": 2.0,   # PLAC arm Δ25OHD ≈ flat
    "mediator_threshold": 4.0,                     # Δ25OHD above which "responded" (routes arm→δ)

    # ---- safety serum panel at Day 21 (no hypercalcemia at 4000 IU) ----
    "pth_vitd_drop": 2.0,        # physiologic PTH suppression in VITD arm (pg/mL)
    "pth_day21_sd": 4.0,
    "ca_day21_sd": 0.15,         # calcium drift; clipped < 10.8 (never hypercalcemic)
    "creat_day21_sd": 0.05,

    # ---- biopsy expression-change frailty loadings (within-patient correlation) ----
    "f_amp_load": 0.8,   # f_amp loading on ΔCAMP and ΔHBD3 (shared AMP cluster → gate g3)
    "f_th2_load": 0.6,   # f_th2 loading on ΔIL13

    # ---- global calibration multipliers on the change submodel (default identity) ----
    "change_mean_scale": 1.0,    # multiplies the per-cell target mean of δ
    "change_sd_scale": 1.0,      # multiplies the per-cell target SD of δ

    # ---- baseline ABSOLUTE biopsy expression levels (model; only the CHANGE is calibrated) ----
    # group -> skin -> peptide -> mean (+ base_level_offset). SD = base_level_cv * mean.
    # Grounded in Ong NEJM 2002 direction (psoriasis lesional cathelicidin/HBD high; AD lesional
    # blunted; IL-13 high in AD lesional). The offset keeps absolute expression well above the
    # change-noise SD so the physical floor (≥0.1) never clips the change distribution.
    "base_level_offset": 25.0,
    "base_level_cv": 0.30,
    "base_levels": {
        "NONAD": {"NONLESIONAL": {"CAMP": 15.0, "HBD3": 12.0, "IL13": 5.0, "IL4": 3.0}},
        "AD": {
            "LESIONAL":    {"CAMP": 9.0,  "HBD3": 8.0,  "IL13": 18.0, "IL4": 9.0},
            "NONLESIONAL": {"CAMP": 13.0, "HBD3": 11.0, "IL13": 8.0,  "IL4": 4.0},
        },
        "PSO": {
            "LESIONAL":    {"CAMP": 30.0, "HBD3": 25.0, "IL13": 6.0,  "IL4": 3.0},
            "NONLESIONAL": {"CAMP": 14.0, "HBD3": 10.0, "IL13": 4.0,  "IL4": 2.0},
        },
    },

    # ---- secondary skin readouts (model; non-calibrated) ----
    "saliva_camp_base": 8.0, "saliva_camp_cv": 0.35,
    "tape_camp_load": 0.7,             # tape cathelicidin tracks biopsy CAMP via f_amp
    "cfu_base_log10": 4.0, "cfu_sd": 0.5, "cfu_lesional_bump": 0.6,
    "pasi_change_mean": -0.6, "pasi_change_sd": 2.0,   # PSO only; slight improvement
    "ige_change_cv": 0.10, "rast_classes": 6,

    # ---- adverse events (sparse: CTGov posted 0 serious, no PT >=5%) ----
    # mild non-serious vitamin-D GI complaints + procedure events; low per-patient hazard.
    "ae_base_haz": 0.04,         # per completer, per mild PT
    "ae_terms": ["Constipation", "Nausea", "Abdominal distension", "Headache"],
    "ae_proc_terms": ["Skin reaction", "Erythema"],  # biopsy-site / tape reactions
    "ae_proc_haz": 0.03,
}


def default_params() -> dict:
    return deepcopy(DEFAULT_PARAMS)


def load_params(path: str | Path) -> dict:
    p = default_params()
    override = json.loads(Path(path).read_text())
    p.update(override)
    return p


def save_params(params: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(params, indent=2))


# ---- target-table accessors -------------------------------------------------
def baseline_cell(metric: str, group: str, arm: str):
    """(mean, sd) for a per-cell continuous baseline characteristic."""
    key = f"{GROUP_LBL[group]}|{ARM_LBL[arm]}"
    return tuple(TARGETS["baseline"][metric][key])


def outcome_cell(peptide: str, group: str, skin: str, arm: str, params: dict):
    """(mean, sd) for the Day21−Baseline change in one peptide/compartment/arm,
    with the global calibration multipliers applied."""
    key = f"{GROUP_LBL[group]}|{SKIN_LBL[skin]}|{ARM_LBL[arm]}"
    mean, sd = TARGETS["outcomes"][peptide][key]
    return mean * params["change_mean_scale"], sd * params["change_sd_scale"]
