"""
Lt — per-visit forward propagation for ARA06.

Topological order within each visit:
  1. drug-exposure indicators (anti-TNF arm, background MTX both arms, prednisone)
  2. clinical disease-activity components decay by latent response (CLINICAL_VISITS)
     and DAS28-CRP is computed deterministically from them (protocol Appendix C)
  3. mechanistic memory-B-cell % (BCELL_VISITS) — AR toward arm-specific target
  4. labs (SAFETY_LAB_VISITS): WBC/ANC/ALC/HGB/PLT MTX-myelosuppression AR(1),
     AST/ALT hepatic drag (MTX + anti-TNF), creatinine
  5. AEs: deterministic CTCAE grading of labs (anaemia/leukopenia/neutropenia/
     lymphopenia/AST/ALT/creatinine) + non-lab AEs from frailty cluster + arm
     (infections, MSK, rash) + rare serious AEs
  6. dose modification (Grade>=3 lab toxicity -> drug interrupted)
  7. discontinuation (administrative; NOT adverse-event-driven, per ctgov)

Every downstream node sees only its DAG parents. Endpoints are NOT drawn here.
"""
from __future__ import annotations
from typing import Dict, List, Any
import numpy as np

from .dag_state import (Ara06Patient, TrajectoryRow, SCHED, das28_crp,
                        CLINICAL_VISITS, BCELL_VISITS, SAFETY_LAB_VISITS,
                        ADMIN_CENSOR_DAY, expit, visit_info)


# ---- CTCAE-style grading (FIXED rules — never tuned) -----------------------
def anaemia_grade(hgb: float, sex: str) -> int:
    lln = 13.5 if sex == "M" else 12.0
    if hgb >= lln: return 0
    if hgb >= 10.0: return 1
    if hgb >= 8.0:  return 2
    if hgb >= 6.5:  return 3
    return 4
def leuko_grade(wbc: float) -> int:           # LLN 4.0
    if wbc >= 4.0: return 0
    if wbc >= 3.0: return 1
    if wbc >= 2.0: return 2
    if wbc >= 1.0: return 3
    return 4
def neutro_grade(anc: float) -> int:          # LLN ~1.5
    if anc >= 1.5: return 0
    if anc >= 1.0: return 1
    if anc >= 0.5: return 2
    if anc >= 0.2: return 3
    return 4
def lympho_grade(alc: float) -> int:          # LLN ~1.0
    if alc >= 1.0: return 0
    if alc >= 0.8: return 1
    if alc >= 0.5: return 2
    if alc >= 0.2: return 3
    return 4
def enzyme_grade(val: float, uln: float) -> int:   # AST/ALT increased
    if val <= uln:          return 0
    if val < 2.5 * uln:     return 1
    if val < 5.0 * uln:     return 2
    if val < 20.0 * uln:    return 3
    return 4
def creat_grade(val: float, uln: float) -> int:
    if val <= uln:          return 0
    if val < 1.5 * uln:     return 1
    if val < 3.0 * uln:     return 2
    if val < 6.0 * uln:     return 3
    return 4


SOC = {
    "Anaemia": "Blood and lymphatic system disorders",
    "Leukopenia": "Blood and lymphatic system disorders",
    "Neutropenia": "Blood and lymphatic system disorders",
    "Lymphopenia": "Blood and lymphatic system disorders",
    "Aspartate aminotransferase increased": "Investigations",
    "Alanine aminotransferase increased": "Investigations",
    "Blood creatinine increased": "Investigations",
    "Upper respiratory tract infection": "Infections and infestations",
    "Nasopharyngitis": "Infections and infestations",
    "Bronchitis": "Infections and infestations",
    "Headache": "Nervous system disorders",
    "Pain in extremity": "Musculoskeletal and connective tissue disorders",
    "Arthralgia": "Musculoskeletal and connective tissue disorders",
    "Rash": "Skin and subcutaneous tissue disorders",
    "Gastrooesophageal reflux disease": "Gastrointestinal disorders",
    "Rheumatoid arthritis flare": "Musculoskeletal and connective tissue disorders",
    "Suicide attempt": "Psychiatric disorders",
}
SEV_WORD = ["MILD", "MODERATE", "SEVERE", "LIFE-THREATENING"]


def _ae(patient, name, grade, related, action, day, key, serious=False):
    info = visit_info(key)
    vd = patient.visit_date(day)
    g = max(1, min(grade, 4))
    return {
        "USUBJID": patient.patient_id, "VISIT": key, "VISITLBL": info.get("VISIT", key),
        "VISITNUM": info.get("VISITNUM", 0), "AEDY": day, "AESTDTC": vd.strftime("%Y-%m-%d"),
        "AETERM": name, "AEDECOD": name.upper(), "AEBODSYS": SOC.get(name, "Other"),
        "AESEV": SEV_WORD[g - 1], "AETOXGR": grade, "AEREL": related, "AEACN": action,
        "AESER": "Y" if serious else "N",
        "AEOUT": "RECOVERING" if grade >= 3 else "RECOVERED", "AEENDTC": "",
    }


def _ramp(key: str, P: dict) -> float:
    if key in ("SCRN", "V2"):
        return 0.0
    if key == "V5":
        return P["ramp_wk12"]
    if key == "V8":
        return P["ramp_wk24"]
    return 0.0


def simulate_trajectory(patient: Ara06Patient, rng: np.random.Generator, params: dict) -> None:
    P = params
    fr = patient.frailties
    is_etn = patient.is_etn

    # State carried across visits
    wbc = patient.baseline_wbc; anc = patient.baseline_anc; alc = patient.baseline_alc
    hgb = patient.baseline_hgb; plt = patient.baseline_plt
    ast = patient.baseline_ast; alt = patient.baseline_alt; creat = patient.baseline_creat
    crp = patient.baseline_crp
    tjc = patient.baseline_tjc; sjc = patient.baseline_sjc
    ptg = patient.baseline_ptglobal; phg = patient.baseline_physglobal
    pain = patient.baseline_pain; haq = patient.baseline_haqdi
    das = patient.baseline_das28
    mem = patient.baseline_mem_switched
    pred = patient.baseline_pred

    discontinued = False
    ae_hist: Dict[str, bool] = {name: False for name in P["ae_nonlab"]}

    for (key, num, day, label) in SCHED:
        if key == "SCRN":
            continue
        if day > ADMIN_CENSOR_DAY or discontinued:
            break

        # 1. exposure: anti-TNF (arm) + background MTX (both arms) + prednisone (constant)
        # 2. clinical components (only updated at clinical assessment visits) ------
        if key in CLINICAL_VISITS:
            r = _ramp(key, P)
            def improve(base, comp, scale=1.0):
                frac = np.clip(patient.resp * r * patient.comp_mult[comp] * scale, 0.0, 0.97)
                v = base * (1.0 - frac) * (1.0 + rng.normal(0, P["visit_noise_clin"]))
                return float(max(0.0, v))
            tjc = round(improve(patient.baseline_tjc, "tjc"), 0)
            sjc = round(improve(patient.baseline_sjc, "sjc"), 0)
            ptg = improve(patient.baseline_ptglobal, "ptglobal")
            phg = improve(patient.baseline_physglobal, "physglobal")
            pain = improve(patient.baseline_pain, "pain")
            haq = round(improve(patient.baseline_haqdi, "haqdi"), 2)
            crp = float(np.clip(improve(patient.baseline_crp, "crp", P["crp_resp_scale"]), 0.1, 120))
            das = round(das28_crp(tjc, sjc, crp, ptg), 2)

        # 3. mechanistic memory-B-cell % (AR toward arm target) ------------------
        if key in BCELL_VISITS:
            if key == "V2":
                mem = float(np.clip(patient.baseline_mem_switched + rng.normal(0, 1.0), 1.0, 50))
            elif key == "V5":
                target = patient.baseline_mem_switched * P["mem_decay"] + P["mem_arm_etn"] * is_etn
                mem = float(np.clip(target + rng.normal(0, P["mem_noise"]), 0.5, 50))
            elif key == "V8":
                mem = float(np.clip(mem * P["mem_wk24_extra_decay"] + rng.normal(0, P["mem_noise"] * 0.6), 0.5, 50))

        # 4. labs (only at safety-lab visits) ------------------------------------
        if key in SAFETY_LAB_VISITS:
            wbc = float(np.clip(P["wbc_ar"] * wbc + (1 - P["wbc_ar"]) * patient.baseline_wbc
                                - (P["wbc_mtx_drag"] + P["wbc_mtx_drag_frailty"] * fr.f_heme)
                                + rng.normal(0, P["wbc_noise"]), 0.6, 16))
            anc = float(np.clip(P["anc_frac"] * wbc + rng.normal(0, P["anc_noise"]), 0.1, 11))
            alc = float(np.clip(P["alc_ar"] * alc + (1 - P["alc_ar"]) * patient.baseline_alc
                                - (P["alc_etn_drag"] * is_etn + P["alc_frailty"] * fr.f_heme)
                                + rng.normal(0, P["alc_noise"]), 0.1, 5))
            hgb = float(np.clip(P["hgb_ar"] * hgb + (1 - P["hgb_ar"]) * patient.baseline_hgb
                                - (P["hgb_mtx_drag"] + P["hgb_drag_frailty"] * fr.f_heme)
                                + rng.normal(0, P["hgb_noise"]), 6.0, 17.5))
            plt = float(np.clip(P["plt_ar"] * plt + (1 - P["plt_ar"]) * patient.baseline_plt
                                - (P["plt_mtx_drag"] + 6 * fr.f_heme) + rng.normal(0, P["plt_noise"]), 20, 600))
            ast = float(np.clip(P["ast_ar"] * ast + (1 - P["ast_ar"]) * patient.baseline_ast
                                + P["ast_mtx_drag"] + P["ast_etn_extra"] * is_etn
                                + P["ast_frailty"] * fr.f_hepatic + rng.normal(0, P["ast_noise"]), 8, 600))
            alt = float(np.clip(P["alt_ar"] * alt + (1 - P["alt_ar"]) * patient.baseline_alt
                                + P["alt_mtx_drag"] + P["alt_etn_extra"] * is_etn
                                + P["alt_frailty"] * fr.f_hepatic + rng.normal(0, P["alt_noise"]), 6, 600))
            creat = float(np.clip(P["creat_ar"] * creat + (1 - P["creat_ar"]) * patient.baseline_creat
                                  + P["creat_etn_extra"] * is_etn + P["creat_frailty"] * fr.f_hepatic
                                  + rng.normal(0, P["creat_noise"]), 0.4, 6))

        # 5. AEs ----------------------------------------------------------------
        aes: List[Dict[str, Any]] = []
        # 5a. deterministic CTCAE grading of labs (only at lab visits)
        if key in SAFETY_LAB_VISITS:
            lab_aes = [
                ("Anaemia", anaemia_grade(hgb, patient.sex), "anaemia_report"),
                ("Leukopenia", leuko_grade(wbc), "leuko_report"),
                ("Neutropenia", neutro_grade(anc), "neutro_report"),
                ("Lymphopenia", lympho_grade(alc), "lympho_report"),
                ("Aspartate aminotransferase increased", enzyme_grade(ast, P["ast_uln"]), "ast_report"),
                ("Alanine aminotransferase increased", enzyme_grade(alt, P["alt_uln"]), "alt_report"),
                ("Blood creatinine increased", creat_grade(creat, P["creat_uln"]), "creat_report"),
            ]
            for name, g, repkey in lab_aes:
                if g >= 1 and rng.random() < P[repkey][str(min(g, 4))]:
                    rel = "POSSIBLY RELATED"   # background MTX +/- anti-TNF
                    act = "DRUG INTERRUPTED" if g >= 3 else "DOSE NOT CHANGED"
                    aes.append(_ae(patient, name, g, rel, act, day, key, serious=(g >= 4)))

        # 5b. non-lab AEs (frailty cluster + arm), first-occurrence per PT
        for name, (base, fattr, lrr_etn, psev) in P["ae_nonlab"].items():
            log_h = np.log(base) + getattr(fr, fattr) + lrr_etn * is_etn
            if ae_hist[name]:
                log_h += 0.2
            if rng.random() < min(0.9, 1 - np.exp(-np.exp(log_h))):
                # non-lab AEs here are non-serious (the trial's only SAEs were GERD,
                # RA flare, suicide attempt — generated separately in 5c)
                g = 3 if rng.random() < psev else (1 if rng.random() < 0.7 else 2)
                aes.append(_ae(patient, name, g, "POSSIBLY RELATED", "DOSE NOT CHANGED", day, key,
                               serious=False))
                ae_hist[name] = True

        # 5c. rare serious AEs (disease flare slightly ADA; idiosyncratic slightly ETN)
        if rng.random() < P["sae_flare_haz"] * np.exp(P["sae_flare_ada"] * (0 if is_etn else 1) + 0.4 * fr.f_msk):
            aes.append(_ae(patient, "Rheumatoid arthritis flare", 3, "NOT RELATED",
                           "DOSE NOT CHANGED", day, key, serious=True))
        if rng.random() < P["sae_idio_haz"] * np.exp(P["sae_idio_etn"] * (1 if is_etn else 0)):
            term = str(rng.choice(["Gastrooesophageal reflux disease", "Suicide attempt"], p=[0.6, 0.4]))
            aes.append(_ae(patient, term, 3, "NOT RELATED", "DOSE NOT CHANGED", day, key, serious=True))

        if any(a["AESER"] == "Y" for a in aes):
            patient.serious_ae = 1

        # 6. dose modification ---------------------------------------------------
        dose_action = "NONE"
        if key in SAFETY_LAB_VISITS and (leuko_grade(wbc) >= 3 or neutro_grade(anc) >= 3
                                         or enzyme_grade(ast, P["ast_uln"]) >= 3
                                         or enzyme_grade(alt, P["alt_uln"]) >= 3):
            dose_action = "DRUG INTERRUPTED"

        patient.trajectory.append(TrajectoryRow(
            visit_key=key, visit_day=day, visit_num=num,
            tjc=tjc, sjc=sjc, ptglobal=round(ptg, 0), physglobal=round(phg, 0),
            pain=round(pain, 0), haqdi=haq, das28=das,
            mem_switched_pct=round(mem, 1),
            prednisone_dose=pred, dose_action=dose_action,
            wbc=round(wbc, 2), anc=round(anc, 2), alc=round(alc, 2), hgb=round(hgb, 1),
            plt=round(plt, 0), ast=round(ast, 0), alt=round(alt, 0), creat=round(creat, 2),
            crp=round(crp, 1), aes=aes, on_treatment=not discontinued,
        ))

        # 7. discontinuation (administrative — never AE-driven, per ctgov) --------
        intercept = P["disc_intercept_etn"] if is_etn else P["disc_intercept_ada"]
        if rng.random() < expit(intercept + P["disc_frailty"] * fr.f_dropout):
            discontinued = True
            patient.discontinuation_day = day
            patient.discontinuation_reason = str(rng.choice(P["disc_reasons"], p=P["disc_reason_p"]))
