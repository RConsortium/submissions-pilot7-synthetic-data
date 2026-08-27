"""
L0 — RAVE baseline node generation. Each node drawn conditional on its DAG
parents, in topological order. Distributions sourced in DAG.md (ctgov baseline
+ eligibility support; model defaults flagged there).
"""
from __future__ import annotations
from datetime import date, timedelta
import numpy as np

from .dag_state import RavePatient, draw_frailties, expit

SITES = [f"SITE{i:03d}" for i in range(1, 31)]   # RAVE was multicenter (US + NL)


def make_baseline(subj_num: int, rng: np.random.Generator, params: dict,
                  study_id: str = "RAVE",
                  study_start: date = date(2005, 1, 1),
                  enroll_window_days: int = 730) -> RavePatient:
    P = params

    site = str(rng.choice(SITES))
    patient_id = f"{study_id}-{site}-{subj_num:04d}"

    # Demographics ----------------------------------------------------------
    country = "USA" if rng.random() < P["p_usa"] else "NLD"
    race = "WHITE" if rng.random() < 0.85 else str(rng.choice(["BLACK", "ASIAN", "OTHER"]))
    sex = "F" if rng.random() < P["p_female"] else "M"
    age = int(np.clip(rng.normal(P["age_mean"], P["age_sd"]), 15, 90))
    wt = float(np.clip(rng.normal(80 if sex == "M" else 68, 16), 40, 140))

    # Disease characterization ---------------------------------------------
    diagnosis_type = "GPA" if rng.random() < P["p_gpa"] else "MPA"
    anca_type = "PR3" if rng.random() < P["p_pr3"] else "MPO"
    new_dx = bool(rng.random() < P["p_new_dx"])
    # MPO / MPA more renal-predominant
    p_renal = expit(-0.2 + (0.5 if anca_type == "MPO" else 0.0) + (0.4 if diagnosis_type == "MPA" else 0.0))
    renal = bool(rng.random() < p_renal)

    # Disease activity / damage --------------------------------------------
    baseline_bvaswg = float(np.clip(rng.normal(P["bvaswg_mean"], P["bvaswg_sd"]), 3, 30))
    baseline_vdi = int(np.clip(round(rng.normal(P["vdi_mean"], P["vdi_sd"])), 0, 8))

    # Comorbidities (parents: age) -----------------------------------------
    htn = bool(rng.random() < expit(-2.5 + 0.05 * (age - 60)))
    dm = bool(rng.random() < expit(-2.8 + 0.04 * (age - 60)))

    # Frailties (drawn once) ------------------------------------------------
    fr = draw_frailties(rng)

    # Baseline labs (parents: sex, renal, frailty) -------------------------
    base_wbc = float(np.clip(rng.normal(P["wbc_mean"], P["wbc_sd"]) + 0.4 * fr.f_heme, P["wbc_floor"], 16))
    base_anc = float(np.clip(P["anc_frac"] * base_wbc + rng.normal(0, 0.8), 1.5, 10))
    base_hgb = float(np.clip(rng.normal(13.5 if sex == "M" else 12.3, 1.3) - (0.8 if renal else 0)
                             + 0.3 * fr.f_heme, 8.5, 17.5))
    base_plt = float(np.clip(rng.normal(P["plt_mean"], P["plt_sd"]), P["plt_floor"], 600))
    base_creat = float(np.clip(rng.normal(0.9 + (0.8 if renal else 0.0), 0.3)
                               + 0.004 * (age - 55), 0.5, 4.0))
    base_bun = float(np.clip(rng.normal(15 + (12 if renal else 0), 6), 5, 80))
    base_crp = float(np.clip(rng.normal(2.0 + 0.5 * baseline_bvaswg, 4), 0.1, 60))
    base_esr = float(np.clip(rng.normal(20 + 2.5 * baseline_bvaswg, 18), 2, 130))

    # Treatment assignment (randomized 1:1, exogenous) ---------------------
    is_rtx = bool(rng.random() < 0.5)
    arm = "Rituximab" if is_rtx else "Control"

    # Latent remission propensity (logit) ----------------------------------
    rp = (P["remit_intercept"] + P["remit_rtx"] * is_rtx
          + P["remit_relapsing"] * (0 if new_dx else 1)
          + P["remit_pr3"] * (1 if anca_type == "PR3" else 0)
          + P["remit_bvas"] * (baseline_bvaswg - 8.0))

    enrollment_offset = int(rng.integers(0, enroll_window_days))
    baseline_date = study_start + timedelta(days=enrollment_offset)

    return RavePatient(
        patient_id=patient_id, site=site, arm=arm, is_rtx=is_rtx,
        baseline_date=baseline_date, enrollment_offset_days=enrollment_offset,
        age=age, sex=sex, race=race, country=country, weight_kg=wt,
        diagnosis_type=diagnosis_type, anca_type=anca_type, new_diagnosis=new_dx,
        renal_involvement=renal,
        baseline_bvaswg=baseline_bvaswg, baseline_vdi=baseline_vdi,
        htn=htn, dm=dm,
        baseline_wbc=base_wbc, baseline_anc=base_anc, baseline_hgb=base_hgb,
        baseline_plt=base_plt, baseline_creat=base_creat, baseline_bun=base_bun,
        baseline_crp=base_crp, baseline_esr=base_esr,
        frailties=fr, remit_propensity=rp,
    )
