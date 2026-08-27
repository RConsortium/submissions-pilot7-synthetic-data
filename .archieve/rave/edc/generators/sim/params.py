"""
RAVE simulator parameters — the ONLY tunable surface for the Step-6 calibration
loop. Calibration adjusts these values; it never changes model structure
(no new edges, no direct arm→endpoint draws). Each block notes its target and
derivation source (ctgov field / paperclip id / model default).

Load/override at runtime from a params/*.json snapshot for reproducible runs.
"""
from __future__ import annotations
import json
from pathlib import Path
from copy import deepcopy


DEFAULT_PARAMS = {
    # ---- L0 baseline population (from ctgov baselineCharacteristicsModule) -----
    "p_female": 0.492,                 # ctgov 97/197
    "age_mean": 52.8, "age_sd": 15.5,  # ctgov "Age, Continuous" total
    "p_usa": 0.92,                     # ctgov region 181/197
    "p_gpa": 0.75,                     # protocol (WG/GPA vs MPA); ~75% GPA
    "p_pr3": 0.66,                     # stratifier; RAVE ~2:1 PR3:MPO
    "p_new_dx": 0.50,                  # stratifier new vs relapsing
    "bvaswg_mean": 8.0, "bvaswg_sd": 3.1,   # ctgov baseline BVAS/WG
    "vdi_mean": 1.2, "vdi_sd": 1.7,
    "wbc_mean": 8.0, "wbc_sd": 2.2, "wbc_floor": 4.0,   # eligibility WBC>=4000
    "plt_mean": 300, "plt_sd": 80, "plt_floor": 120,

    # ---- Disease-activity / remission process (BVAS/WG) ------------------------
    # remission propensity: logit of complete remission @6mo (target RTX .64 / CYC .53)
    "remit_intercept": 0.62,           # base complete-remission logit
    "remit_rtx": 0.46,                 # RTX advantage (drives 64% vs 53%)
    "remit_relapsing": -0.30,          # relapsing patients harder to fully remit
    "remit_pr3": -0.10,
    "remit_bvas": -0.05,               # higher baseline activity → slightly lower
    "remit_day_median": 45.0,          # median day to BVAS/WG=0 (ctgov ~43-57)
    "remit_day_sigma": 0.55,           # lognormal spread
    "flare_window_start_day": 185,     # flares accrue post-6mo (maintenance phase)

    # ---- Flare process (after remission) --------------------------------------
    "flare_base_haz": 0.045,           # per-visit hazard once in remission (maintenance phase)
    "flare_rtx": -0.20,                # RTX modestly protective (HR~0.9)
    "flare_pr3": 0.62,                 # paperclip PMC8407598 HR 1.69 (log .52); +PMC4520074 56% vs 17%
    "flare_relapsing": 0.35,
    "flare_pred_protect": -0.020,      # per-mg/day prednisone (on-steroid protective)
    "flare_frailty": 1.0,              # coefficient on f_relapse
    "p_flare_severe": 0.45,            # severe vs limited flare

    # ---- Prednisone taper (protocol: off by month 6) --------------------------
    "pred_start_mgkg": 1.0,            # ~1 mg/kg/day
    "pred_taper_end_day": 180,         # 0 by day 180 (month 6)

    # ---- Labs: WBC AR(1) + cyclophosphamide myelosuppression (KEY arm signal) --
    "wbc_ar": 0.5,                     # AR(1) coefficient
    "wbc_cyc_drag": 1.7,              # mean WBC drop on oral CYC (paperclip PMC5880843)
    "wbc_cyc_drag_frailty": 0.7,       # × f_heme
    "wbc_rtx_drag": 0.6,               # RTX late-onset neutropenia (paperclip PMC3539507)
    "wbc_rtx_drag_frailty": 0.4,       # × f_heme
    "wbc_noise": 0.7,
    "hgb_ar": 0.5, "hgb_cyc_drag": 0.5, "hgb_noise": 0.5,
    "plt_ar": 0.5, "plt_cyc_drag": 18.0, "plt_rtx_drag": 10.0, "plt_noise": 22.0,
    "anc_frac": 0.6, "anc_noise": 0.45,

    # ---- AE generators (non-lab): per-visit hazard while exposed ---------------
    # name -> (base_haz, frailty_attr, log_rr_cyc, log_rr_rtx, p_severe)
    "ae_nonlab": {
        "Nausea":        [0.055, "f_GI",     0.25, 0.0,  0.03],
        "Vomiting":      [0.018, "f_GI",     0.50, 0.0,  0.05],
        "Diarrhoea":     [0.060, "f_GI",     0.30, 0.0,  0.03],
        "Alopecia":      [0.022, "f_GI",     0.65, -2.0, 0.01],  # CYC-specific
        "Rash":          [0.030, "f_GI",     0.50, 0.0,  0.02],
        "Arthralgia":    [0.075, "f_relapse",0.0,  0.15, 0.03],
        "Fatigue":       [0.060, "f_GI",     0.0,  0.10, 0.04],
        "Headache":      [0.060, "f_GI",     0.0,  0.05, 0.02],
        "Cough":         [0.065, "f_infect", 0.0,  0.20, 0.03],
    },
    # infection hazard (any-grade); serious fraction separate
    "infect_base_haz": 0.050,
    "infect_frailty": 1.0,             # × f_infect
    "infect_rtx": 0.12,                # RTX B-cell depletion (Gr>=3 infection 18 vs 16; paperclip PMC5570101)
    "infect_cyc": 0.0,
    "infect_pred": 0.004,              # per-mg/day prednisone
    "infect_base_haz_serious_disease": 0.014,  # serious vasculitis/disease-related event hazard
    "serious_disease_rtx": 0.65,       # RTX-arm disease-related serious events (ctgov Wegener's 8 vs 4)
    "p_infect_serious": 0.30,          # serious-infection fraction
    # infusion reaction (RTX real infusions only)
    "infusion_rxn_haz": 0.02,
    # steroid AEs (hyperglycemia/cushingoid/insomnia): hazard ∝ prednisone dose
    "steroid_ae_per_mg": 0.0016,
    "steroid_ae_frailty": 0.8,

    # CTCAE v3.0 leukopenia reporting probabilities by grade (deterministic grade,
    # stochastic reporting) — grade thresholds are FIXED (never tuned).
    "leuko_report": {"1": 0.25, "2": 0.85, "3": 0.97, "4": 1.0},
    "anemia_report": {"1": 0.20, "2": 0.55, "3": 0.95, "4": 1.0},
    "thrombo_report": {"1": 0.20, "2": 0.70, "3": 0.95, "4": 1.0},

    # ---- Discontinuation / crossover / death ----------------------------------
    "disc_intercept": -5.2,
    "disc_frailty": 0.5,               # × f_dropout
    "disc_serious_ae": 0.7,
    "disc_severe_flare": 1.5,
    "p_crossover_nonresponse": 0.10,   # of non-remitters in V5-V8 window
    "death_base": 0.020,               # ~2 per arm over 18 mo
    "death_serious_ae": 0.03,
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
