"""
L0 — CATH baseline node generation. Each node drawn conditional on its DAG parents,
in topological order. Per-cell distributions sourced from targets.json (ctgov baseline);
absolute biopsy levels and secondary readouts are model defaults (flagged in DAG.md).
"""
from __future__ import annotations
from datetime import date, timedelta
import numpy as np

from .dag_state import CathPatient, BiopsyState, COMPARTMENTS, draw_frailties
from .params import baseline_cell

SITES = ["UCSD001", "UCSD002", "UCSD003"]   # CTGov: three US centers


def _lognormal_params(mean: float, sd: float):
    """Method-of-moments lognormal (μ, σ) reproducing a target arithmetic mean & SD."""
    if mean <= 0:
        return 0.0, 0.5
    var = sd * sd
    sigma2 = np.log(1.0 + var / (mean * mean))
    mu = np.log(mean) - 0.5 * sigma2
    return mu, float(np.sqrt(sigma2))


def make_baseline(subj_num: int, group: str, arm_code: str, rng: np.random.Generator,
                  params: dict, study_id: str = "CATH",
                  study_start: date = date(2009, 1, 1),
                  enroll_window_days: int = 300) -> CathPatient:
    P = params
    is_vitd = (arm_code == "VITD")
    arm = "Vitamin D3" if is_vitd else "Placebo"
    site = str(rng.choice(SITES))
    patient_id = f"{study_id}-{site}-{subj_num:04d}"

    # Demographics (per-cell) ------------------------------------------------
    age_m, age_s = baseline_cell("age_years", group, arm_code)
    age = int(np.clip(rng.normal(age_m, age_s), 18, 70))
    bmi_m, bmi_s = baseline_cell("bmi_kgm2", group, arm_code)
    bmi = float(np.clip(rng.normal(bmi_m, bmi_s), 16.0, 45.0))

    # sex: per-cell female fraction (count / n started)
    cell = f"{group}|{arm_code}"
    fem_ct = {"NONAD|VITD": 9, "AD|VITD": 11, "PSO|VITD": 4,
              "NONAD|PLAC": 9, "AD|PLAC": 7, "PSO|PLAC": 4}[cell]
    n_ct = {"NONAD|VITD": 16, "AD|VITD": 16, "PSO|VITD": 8,
            "NONAD|PLAC": 16, "AD|PLAC": 18, "PSO|PLAC": 8}[cell]
    sex = "F" if rng.random() < fem_ct / n_ct else "M"

    # race / ethnicity (pooled multinomial; CTGov totals) --------------------
    race = str(rng.choice(["WHITE", "ASIAN", "BLACK", "OTHER"], p=[54/82, 10/82, 9/82, 9/82]))
    ethnic = "HISPANIC" if rng.random() < 9/82 else "NOT HISPANIC"

    # Fitzpatrick (pooled multinomial; darker skin slightly more likely if BLACK) ----
    fitz_p = np.array([3, 20, 26, 22, 4, 6], dtype=float)  # I..VI (drop the 1 unknown)
    if race == "BLACK":
        fitz_p = np.array([0, 1, 2, 4, 6, 8], dtype=float)
    fitz = int(rng.choice([1, 2, 3, 4, 5, 6], p=fitz_p / fitz_p.sum()))

    height_cm = float(np.clip(rng.normal(176 if sex == "M" else 163, 8), 145, 200))
    weight_kg = round(bmi * (height_cm / 100.0) ** 2, 1)

    # Baseline serum 25-OH-D (parents: age, BMI, Fitzpatrick) -----------------
    # center covariate terms so the per-cell MEAN is preserved; literature: older /
    # higher BMI / darker skin → lower 25(OH)D.
    vd_m, vd_s = baseline_cell("vitd_25oh_ngml", group, arm_code)
    cov = (-0.12 * (age - age_m) - 0.20 * (bmi - bmi_m) - 1.2 * (fitz - 3))
    resid_sd = float(np.sqrt(max(0.5, vd_s ** 2 - 9.0)))   # leave variance for covariate terms
    base_vitd = float(np.clip(vd_m + cov + rng.normal(0, resid_sd), 8.0, 80.0))

    ca_m, ca_s = baseline_cell("calcium_mgdl", group, arm_code)
    base_ca = float(np.clip(rng.normal(ca_m, ca_s), 8.4, 10.6))
    pth_m, pth_s = baseline_cell("pth_pgml", group, arm_code)
    base_pth = float(np.clip(rng.normal(pth_m, pth_s) - 0.4 * (base_vitd - vd_m), 8.0, 90.0))
    cr_m, cr_s = baseline_cell("creatinine_mgdl", group, arm_code)
    base_creat = float(np.clip(rng.normal(cr_m, max(0.05, cr_s)), 0.4, 1.3))

    # Total IgE (parent: dxgroup → atopy). AD ≫ Non-AD/Pso ; lognormal. ------
    ige_m, ige_s = baseline_cell("ige_kul", group, arm_code)
    mu, sg = _lognormal_params(ige_m, ige_s)
    base_ige = float(np.clip(rng.lognormal(mu, sg), 1.0, 30000.0))
    base_rast = int(np.clip(round((np.log10(base_ige + 1) - 1.0) * 1.3 + rng.normal(0, 0.6)), 0, 6))

    # Frailties (drawn once) -------------------------------------------------
    fr = draw_frailties(rng)

    # Baseline skin biopsy expression per compartment (model levels) ---------
    base_biopsy = {}
    cv = P["base_level_cv"]
    off = P["base_level_offset"]
    for comp in COMPARTMENTS[group]:
        lev = P["base_levels"][group][comp]
        # absolute level = (model level + offset); noise sd = cv*level (modest, keeps ordering).
        base_biopsy[comp] = BiopsyState(
            compartment=comp,
            camp=float(max(0.1, lev["CAMP"] + off + cv * lev["CAMP"] * rng.normal())),
            hbd3=float(max(0.1, lev["HBD3"] + off + cv * lev["HBD3"] * rng.normal())),
            il13=float(max(0.1, lev["IL13"] + off + cv * lev["IL13"] * rng.normal())),
            il4=float(max(0.1, lev["IL4"] + off + cv * lev["IL4"] * rng.normal())),
        )
    # baseline PASI (psoriasis only) + baseline bacterial colony counts
    base_pasi = float(np.clip(rng.normal(8.0, 3.0), 1.0, 30.0)) if group == "PSO" else None
    base_cfu = {comp: float(np.clip(rng.normal(P["cfu_base_log10"]
                + (P["cfu_lesional_bump"] if comp == "LESIONAL" else 0.0), P["cfu_sd"]), 1.0, 8.0))
                for comp in COMPARTMENTS[group]}

    enroll_off = int(rng.integers(0, enroll_window_days))
    baseline_date = study_start + timedelta(days=enroll_off)

    return CathPatient(
        patient_id=patient_id, site=site, dxgroup=group, arm=arm, is_vitd=is_vitd,
        baseline_date=baseline_date, enrollment_offset_days=enroll_off,
        age=age, sex=sex, race=race, ethnic=ethnic, country="USA",
        height_cm=round(height_cm, 1), weight_kg=weight_kg, bmi=round(bmi, 1), fitzpatrick=fitz,
        base_vitd_25oh=round(base_vitd, 1), base_calcium=round(base_ca, 1),
        base_pth=round(base_pth, 1), base_creat=round(base_creat, 2),
        base_ige=round(base_ige, 1), base_rast=base_rast,
        base_biopsy=base_biopsy, base_pasi=base_pasi, base_cfu=base_cfu,
        frailties=fr,
    )
