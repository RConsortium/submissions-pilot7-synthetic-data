"""
L0 — ARA06 baseline node generation. Each node drawn conditional on its DAG
parents, in topological order. Distributions sourced in DAG.md (ctgov baseline +
eligibility support; model defaults flagged there).
"""
from __future__ import annotations
from datetime import date, timedelta
import numpy as np

from .dag_state import Ara06Patient, Frailties, draw_frailties, das28_crp

SITES = [f"SITE{i:02d}" for i in range(1, 9)]   # multi-center (ACE network)
COMP_KEYS = ["tjc", "sjc", "ptglobal", "physglobal", "pain", "haqdi", "crp"]


def make_baseline(subj_num: int, rng: np.random.Generator, params: dict,
                  study_id: str = "ARA06",
                  study_start: date = date(2009, 3, 1),
                  enroll_window_days: int = 730) -> Ara06Patient:
    P = params

    site = str(rng.choice(SITES))
    patient_id = f"{study_id}-{site}-{subj_num:04d}"

    # Treatment assignment (randomized 2:1, exogenous) — deterministic by index so
    # per-arm N matches ctgov enrollment exactly. Arm is independent of features.
    is_etn = subj_num <= P["n_etn"]
    arm = "Etanercept" if is_etn else "Adalimumab"

    # Demographics ----------------------------------------------------------
    sex = "F" if rng.random() < P["p_female"] else "M"
    age = int(np.clip(rng.normal(P["age_mean"], P["age_sd"]), 18, 75))
    race = "WHITE" if rng.random() < P["p_white"] else str(rng.choice(["BLACK", "ASIAN", "OTHER"], p=[0.6, 0.2, 0.2]))
    ethnicity = "HISPANIC" if rng.random() < P["p_hispanic"] else "NOT HISPANIC"
    wt = float(np.clip(rng.normal(82 if sex == "M" else 72, 17), 45, 150))

    # Disease characterization ---------------------------------------------
    ra_dur = float(np.clip(rng.gamma(0.9, P["ra_duration_mean"] / 0.9), 0.25, 40))
    rf_ccp = bool(rng.random() < P["p_rf_ccp_pos"])
    mtx = float(np.clip(rng.normal(P["mtx_dose_mean"], P["mtx_dose_sd"]), 7.5, 25))

    # Frailties (drawn once) ------------------------------------------------
    fr = draw_frailties(rng)

    # Baseline clinical components (parents: disease severity) --------------
    def _draw_clip(mean, sd, lo, hi):
        return float(np.clip(rng.normal(mean, sd), lo, hi))

    tjc = _draw_clip(P["tjc_mean"], P["tjc_sd"], 2, 28)
    sjc = _draw_clip(P["sjc_mean"], P["sjc_sd"], 1, 28)
    crp = float(np.clip(np.exp(rng.normal(np.log(P["crp_mean"]) - 0.4, 0.85)), 0.3, 120))
    ptglobal = _draw_clip(P["ptglobal_mean"], P["ptglobal_sd"], 10, 100)
    physglobal = _draw_clip(P["physglobal_mean"], P["physglobal_sd"], 10, 100)
    pain = _draw_clip(P["pain_mean"], P["pain_sd"], 5, 100)
    haqdi = _draw_clip(P["haqdi_mean"], P["haqdi_sd"], 0, 3)

    # eligibility: active RA, DAS28-CRP > 4.4 — bump patient-global until satisfied
    das = das28_crp(tjc, sjc, crp, ptglobal)
    while das <= P["das28_floor"]:
        ptglobal = min(100.0, ptglobal + 6.0)
        tjc = min(28.0, tjc + 1.0)
        das = das28_crp(tjc, sjc, crp, ptglobal)

    # Baseline mechanistic memory-B + labs (parents: sex, frailty) ----------
    mem_base = float(np.clip(rng.normal(P["mem_base_mean"], P["mem_base_sd"]), 2.0, 45.0))
    wbc = float(np.clip(rng.normal(P["wbc_mean"], P["wbc_sd"]) + 0.3 * fr.f_heme, P["wbc_floor"], 15))
    anc = float(np.clip(P["anc_frac"] * wbc + rng.normal(0, P["anc_noise"]), 1.6, 9))
    alc = float(np.clip(P["alc_frac"] * wbc + rng.normal(0, P["alc_noise"]), 0.6, 4.5))
    hgb_mean = P["hgb_mean_m"] if sex == "M" else P["hgb_mean_f"]
    hgb = float(np.clip(rng.normal(hgb_mean, P["hgb_sd"]) + 0.3 * fr.f_heme, 9.2, 17.5))
    plt = float(np.clip(rng.normal(P["plt_mean"], P["plt_sd"]), P["plt_floor"], 560))
    ast = float(np.clip(rng.normal(P["ast_mean"], P["ast_sd"]) + 3 * fr.f_hepatic, 10, P["ast_uln"] * 1.9))
    alt = float(np.clip(rng.normal(P["alt_mean"], P["alt_sd"]) + 3 * fr.f_hepatic, 8, P["alt_uln"] * 1.9))
    creat = float(np.clip(rng.normal(P["creat_mean"], P["creat_sd"]) + 0.002 * (age - 52), 0.5, P["creat_uln"] * 1.2))
    pred = float(round(rng.uniform(2.5, 10.0))) if rng.random() < P["p_baseline_pred"] else 0.0

    # Latent response strength + per-component multipliers ------------------
    mu = P["resp_mu_etn"] if is_etn else P["resp_mu_ada"]
    resp = float(np.clip(rng.normal(mu, P["resp_sigma"]), P["resp_floor"], P["resp_ceiling"]))
    comp_mult = {k: float(np.clip(rng.normal(1.0, P["comp_mult_sigma"]), 0.3, 1.7)) for k in COMP_KEYS}

    enrollment_offset = int(rng.integers(0, enroll_window_days))
    baseline_date = study_start + timedelta(days=enrollment_offset)

    return Ara06Patient(
        patient_id=patient_id, site=site, arm=arm, is_etn=is_etn,
        baseline_date=baseline_date, enrollment_offset_days=enrollment_offset,
        age=age, sex=sex, race=race, ethnicity=ethnicity, country="USA", weight_kg=wt,
        ra_duration_yr=round(ra_dur, 1), rf_ccp_positive=rf_ccp, mtx_dose=round(mtx, 1),
        baseline_tjc=tjc, baseline_sjc=sjc, baseline_ptglobal=ptglobal,
        baseline_physglobal=physglobal, baseline_pain=pain, baseline_haqdi=haqdi,
        baseline_crp=crp, baseline_das28=das,
        baseline_mem_switched=mem_base,
        baseline_wbc=wbc, baseline_anc=anc, baseline_alc=alc, baseline_hgb=hgb,
        baseline_plt=plt, baseline_ast=ast, baseline_alt=alt, baseline_creat=creat,
        baseline_pred=pred,
        frailties=fr, resp=resp, comp_mult=comp_mult,
    )
