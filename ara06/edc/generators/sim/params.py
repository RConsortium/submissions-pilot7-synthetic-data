"""
ARA06 simulator parameters — the ONLY tunable surface for the Step-6 calibration
loop. Calibration adjusts these values; it never changes model structure (no new
edges, no direct arm->endpoint draws). Each block notes its target/derivation.

Load/override at runtime from a params/*.json snapshot for reproducible runs.
"""
from __future__ import annotations
import json
from pathlib import Path
from copy import deepcopy


DEFAULT_PARAMS = {
    # ---- Arm allocation (2:1 ETN:ADA, ctgov enrolled 43:20) --------------------
    "n_etn": 43, "n_ada": 20,

    # ---- L0 baseline population (ctgov baselineCharacteristicsModule, mITT) ----
    "p_female": 0.793,                 # ctgov 46/58
    "age_mean": 52.0, "age_sd": 11.0,
    "p_white": 0.83, "p_hispanic": 0.155,
    "ra_duration_mean": 5.3, "ra_duration_sd": 7.0,
    "p_rf_ccp_pos": 0.759,             # ctgov 44/58
    "mtx_dose_mean": 17.9, "mtx_dose_sd": 3.9,
    "p_baseline_pred": 0.45,           # fraction on low-dose prednisone (<=10 mg/day)

    # baseline clinical components (ctgov + protocol DAS28>4.4 eligibility)
    "tjc_mean": 12.3, "tjc_sd": 6.7,
    "sjc_mean": 9.7, "sjc_sd": 6.0,
    "crp_mean": 13.8, "crp_sd": 12.0,  # ctgov mean 13.8; sd compressed (lognormal-ish, clipped)
    "ptglobal_mean": 52.0, "ptglobal_sd": 18.0,
    "physglobal_mean": 50.0, "physglobal_sd": 17.0,
    "pain_mean": 55.0, "pain_sd": 20.0,
    "haqdi_mean": 1.4, "haqdi_sd": 0.7,
    "das28_floor": 4.4,                # eligibility: active RA DAS28>4.4

    # baseline labs (screening eligibility floors + RA-on-MTX norms)
    "wbc_mean": 7.2, "wbc_sd": 2.0, "wbc_floor": 3.5,
    "anc_frac": 0.60, "anc_noise": 0.5,
    "alc_frac": 0.28, "alc_noise": 0.30,
    "hgb_mean_f": 12.6, "hgb_mean_m": 14.2, "hgb_sd": 1.3,
    "plt_mean": 290, "plt_sd": 75, "plt_floor": 110,
    "ast_mean": 24, "ast_sd": 9, "ast_uln": 40,
    "alt_mean": 26, "alt_sd": 11, "alt_uln": 45,
    "creat_mean": 0.85, "creat_sd": 0.18, "creat_uln": 1.2,

    # ---- Mechanistic PRIMARY: switched memory B cells (% of B cells) -----------
    # baseline higher; TNF blockade lowers it; both arms ~null difference (ctgov p=0.3)
    "mem_base_mean": 18.4, "mem_base_sd": 7.6,
    "mem_decay": 0.76,                 # wk12 multiplier on baseline (mean ~13.5)
    "mem_arm_etn": -0.5,               # ETN ~null lower (trial p=0.3; anti-TNF does NOT
                                       #   reduce switched memory — paperclip PMC2714135)
    "mem_noise": 4.5,                  # so wk12 SD ~7.3
    "mem_wk24_extra_decay": 0.97,      # modest further change by wk24

    # ---- Clinical response process (latent maximal fractional improvement) -----
    # resp ~ N(mu_arm, sigma); ADA modestly deeper (ctgov ACR50 ADA>ETN); anti-TNF
    # class effect on ACR is comparable across agents (paperclip PMC2377247).
    "resp_mu_etn": 0.59, "resp_mu_ada": 0.66, "resp_sigma": 0.30,
    "resp_floor": 0.0, "resp_ceiling": 0.95,
    "ramp_wk12": 0.92, "ramp_wk24": 1.05,  # response builds over time
    "comp_mult_sigma": 0.30,           # per-component spread (drives ACR "3 of 5")
    "visit_noise_clin": 0.04,          # small per-visit measurement noise on improvement
    "crp_resp_scale": 1.05,            # CRP responds slightly more than joint counts

    # ---- Labs longitudinal: MTX myelosuppression + anti-TNF, AR(1) ------------
    "wbc_ar": 0.55, "wbc_mtx_drag": 0.45, "wbc_mtx_drag_frailty": 0.55, "wbc_noise": 0.7,
    "hgb_ar": 0.55, "hgb_mtx_drag": 0.03, "hgb_drag_frailty": 0.22, "hgb_noise": 0.5,
    "plt_ar": 0.55, "plt_mtx_drag": 8.0, "plt_noise": 20.0,
    "alc_ar": 0.5, "alc_etn_drag": 0.10, "alc_frailty": 0.12, "alc_noise": 0.18,
    # transaminases: MTX (+anti-TNF) hepatic drag, AR(1); ETN higher (ctgov AST 10/39 vs
    # 3/19; MTX+etanercept 23.5% elevated transaminases — paperclip PMC6186305). Strong
    # shared f_hepatic loading makes AST/ALT co-elevate within patient (gate g3).
    "ast_ar": 0.5, "ast_mtx_drag": 1.0, "ast_etn_extra": 2.8, "ast_frailty": 6.0, "ast_noise": 4.0,
    "alt_ar": 0.5, "alt_mtx_drag": 1.0, "alt_etn_extra": 1.2, "alt_frailty": 6.5, "alt_noise": 4.5,
    "creat_ar": 0.6, "creat_etn_extra": 0.05, "creat_frailty": 0.06, "creat_noise": 0.05,

    # CTCAE-style reporting probabilities for lab-derived AEs (grade thresholds FIXED).
    # AE present iff lab crosses threshold AND a Bernoulli(report) fires.
    "anaemia_report": {"1": 0.20, "2": 0.85, "3": 0.97, "4": 1.0},
    "leuko_report":   {"1": 0.20, "2": 0.80, "3": 0.97, "4": 1.0},
    "neutro_report":  {"1": 0.20, "2": 0.80, "3": 0.97, "4": 1.0},
    "lympho_report":  {"1": 0.20, "2": 0.70, "3": 0.95, "4": 1.0},
    "ast_report":     {"1": 0.46, "2": 0.90, "3": 1.0,  "4": 1.0},  # grade1 = >ULN..<2.5xULN
    "alt_report":     {"1": 0.38, "2": 0.90, "3": 1.0,  "4": 1.0},
    "creat_report":   {"1": 0.45, "2": 0.85, "3": 1.0,  "4": 1.0},

    # ---- Non-lab AE generators: per-visit hazard while exposed -----------------
    # name -> (base_haz, frailty_attr, log_rr_etn, p_severe)  (etn vs ada contrast)
    "ae_nonlab": {
        "Upper respiratory tract infection": [0.017, "f_infect", 0.55, 0.02],
        "Nasopharyngitis":                   [0.020, "f_infect", 0.10, 0.01],
        "Bronchitis":                        [0.015, "f_infect", 0.30, 0.03],
        "Headache":                          [0.022, "f_msk",    0.95, 0.01],
        "Pain in extremity":                 [0.020, "f_msk",    0.45, 0.02],
        "Arthralgia":                        [0.019, "f_msk",    0.70, 0.03],
        "Rash":                              [0.015, "f_infect", 0.30, 0.02],
    },

    # serious AEs (rare; ctgov 2/39 ETN, 1/19 ADA). disease-flare SAE slightly ADA;
    # idiosyncratic SAE (GERD / suicide attempt) slightly ETN.
    "sae_flare_haz": 0.0015, "sae_flare_ada": 0.6,       # RA-flare SAE (ADA arm had 1)
    "sae_idio_haz": 0.0016, "sae_idio_etn": 0.5,         # GERD / psychiatric (ETN arm had 2)

    # ---- Discontinuation (administrative-dominant; ctgov shows ~0 AE-driven) ----
    # ETN 9/43 noncompletion (mostly physician decision / noncompliance / logistics),
    # ADA 1/20 (lost to follow-up). NO AE-driven discontinuations in this trial.
    "disc_intercept_etn": -3.25, "disc_intercept_ada": -5.0,
    "disc_frailty": 0.5,
    # administrative reason mix (ctgov disposition reasons; NOT adverse-event)
    "disc_reasons": ["PHYSICIAN DECISION", "LOST TO FOLLOW-UP", "PROTOCOL DEVIATION",
                     "NONCOMPLIANCE", "WITHDRAWAL BY SPONSOR", "OTHER"],
    "disc_reason_p": [0.34, 0.18, 0.16, 0.18, 0.07, 0.07],
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
