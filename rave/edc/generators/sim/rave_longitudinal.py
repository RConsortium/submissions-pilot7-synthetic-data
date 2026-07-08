"""
Lt — per-visit forward propagation for RAVE.

Topological order within each visit:
  1. drug-exposure indicators (rituximab infusion, CYC induction, AZA maintenance)
  2. prednisone dose (protocol taper; completes only if heading to complete remission)
  3. labs: WBC AR(1) + CYC myelosuppression drag (the key arm signal), HGB, PLT, renal, CRP/ESR
  4. BVAS/WG disease activity (decay to remission; flare process), VDI
  5. AEs: deterministic CTCAE grading of labs (leukopenia/neutropenia/anemia/thrombocytopenia)
          + non-lab AEs from frailty cluster + arm + infection + infusion reaction + steroid AEs
  6. dose modification (cytopenia → hold/reduce; pre-infusion WBC<3 → withhold)
  7. crossover / discontinuation

Every downstream node sees only its DAG parents. Endpoints are NOT drawn here.
"""
from __future__ import annotations
from typing import Dict, List, Any
import numpy as np

from .dag_state import (RavePatient, TrajectoryRow, SCHED,
                        RTX_INFUSION_VISITS, ADMIN_CENSOR_DAY,
                        expit, visit_info)


# ---- CTCAE v3.0 grading (FIXED rules — never tuned) ------------------------
def leuko_grade(wbc: float) -> int:           # WBC ×10⁹/L, LLN≈4.0
    if wbc >= 4.0: return 0
    if wbc >= 3.0: return 1
    if wbc >= 2.0: return 2
    if wbc >= 1.0: return 3
    return 4
def neutro_grade(anc: float) -> int:          # ANC ×10⁹/L, LLN≈1.5
    if anc >= 1.5: return 0
    if anc >= 1.0: return 1
    if anc >= 0.5: return 2
    if anc >= 0.2: return 3
    return 4
def anemia_grade(hgb: float) -> int:          # Hgb g/dL
    if hgb >= 10.0: return 0
    if hgb >= 8.0:  return 1
    if hgb >= 6.5:  return 2
    return 3
def thrombo_grade(plt: float) -> int:         # PLT ×10⁹/L
    if plt >= 75: return 0
    if plt >= 50: return 1
    if plt >= 25: return 2
    return 3


SOC = {
    "Leukopenia": "Blood and lymphatic system disorders",
    "Neutropenia": "Blood and lymphatic system disorders",
    "Anaemia": "Blood and lymphatic system disorders",
    "Thrombocytopenia": "Blood and lymphatic system disorders",
    "Nausea": "Gastrointestinal disorders", "Vomiting": "Gastrointestinal disorders",
    "Diarrhoea": "Gastrointestinal disorders",
    "Alopecia": "Skin and subcutaneous tissue disorders", "Rash": "Skin and subcutaneous tissue disorders",
    "Arthralgia": "Musculoskeletal and connective tissue disorders",
    "Fatigue": "General disorders", "Headache": "Nervous system disorders",
    "Cough": "Respiratory, thoracic and mediastinal disorders",
    "Infection": "Infections and infestations",
    "Infusion related reaction": "Immune system disorders",
    "Hyperglycaemia": "Metabolism and nutrition disorders",
    "Cushingoid": "Endocrine disorders", "Insomnia": "Psychiatric disorders",
}
STEROID_AES = ["Hyperglycaemia", "Cushingoid", "Insomnia"]
SEV_WORD = ["MILD", "MODERATE", "SEVERE", "LIFE-THREATENING"]


def _ae(patient, name, grade, related, action, day, key, serious=None):
    info = visit_info(key)
    vd = patient.visit_date(day)
    g = max(1, min(grade, 4))
    ser = serious if serious is not None else (grade >= 3)
    return {
        "USUBJID": patient.patient_id, "VISIT": key, "VISITLBL": info.get("VISIT", key),
        "VISITNUM": info.get("VISITNUM", 0), "AEDY": day, "AESTDTC": vd.strftime("%Y-%m-%d"),
        "AETERM": name, "AEDECOD": name.upper(), "AEBODSYS": SOC.get(name, "Other"),
        "AESEV": SEV_WORD[g - 1], "AETOXGR": grade, "AEREL": related, "AEACN": action,
        "AESER": "Y" if ser else "N",
        "AEOUT": "RECOVERING" if grade >= 3 else "RECOVERED", "AEENDTC": "",
    }


def _prednisone(day: int, weight: float, cr6: bool, P: dict) -> float:
    """Protocol taper: ~1 mg/kg/day start, to 0 by day 180 IF heading to complete
    remission; non-responders stay on a residual maintenance dose."""
    start = P["pred_start_mgkg"] * weight
    end_day = P["pred_taper_end_day"]
    if day <= 1:
        return float(round(start))
    if day >= end_day:
        return 0.0 if cr6 else 7.5     # responders off; non-responders residual steroid
    frac = 1.0 - (day - 1) / (end_day - 1)
    floor = 0.0 if cr6 else 7.5
    return float(round(max(floor, start * frac)))


def simulate_trajectory(patient: RavePatient, rng: np.random.Generator, params: dict) -> None:
    P = params
    fr = patient.frailties
    is_rtx = patient.is_rtx

    # ---- Latent disease-course assignment (multi-parent → trajectory shape) ----
    p_remit_ever = 0.93                                   # most reach BVAS/WG=0 transiently
    remit_ever = rng.random() < p_remit_ever
    cr6 = (rng.random() < expit(patient.remit_propensity)) and remit_ever  # complete remission @6mo
    if remit_ever:
        rday = int(np.clip(np.exp(rng.normal(np.log(P["remit_day_median"]), P["remit_day_sigma"])), 8, 175))
    else:
        rday = 10**9
    patient.remission_day = rday if remit_ever else None

    # State
    wbc = patient.baseline_wbc; anc = patient.baseline_anc
    hgb = patient.baseline_hgb; plt = patient.baseline_plt
    creat = patient.baseline_creat; bun = patient.baseline_bun
    crp = patient.baseline_crp; esr = patient.baseline_esr
    bvas = patient.baseline_bvaswg
    vdi = patient.baseline_vdi
    cum_gc = 0.0
    prev_day = 1
    in_remission = False
    discontinued = False
    crossed = False
    ae_hist = {name: False for name in P["ae_nonlab"]}

    for (key, num, day, label) in SCHED:
        if key == "SCRN":
            continue
        if day > ADMIN_CENSOR_DAY:
            break
        if discontinued:
            break

        # 1. exposure indicators
        rtx_infusion = is_rtx and key in RTX_INFUSION_VISITS          # real infusions (RTX arm)
        rtx_placebo_inf = (not is_rtx) and key in RTX_INFUSION_VISITS  # placebo infusions (control)
        cyc_active = (not is_rtx) and (1 <= day <= 90)                # control induction (oral CYC)
        aza_active = (not is_rtx) and (day > 90)                      # control maintenance (AZA)

        # 2. prednisone (protocol taper); cumulative = dose × days since last visit
        pred = _prednisone(day, patient.weight_kg, cr6, P)
        cum_gc += pred * max(1, day - prev_day)

        # 3. labs --------------------------------------------------------------
        # WBC drag: CYC induction (largest) > RTX late-onset > AZA maintenance
        if cyc_active:
            wbc_drag = P["wbc_cyc_drag"] + P["wbc_cyc_drag_frailty"] * fr.f_heme
        elif is_rtx:
            wbc_drag = P["wbc_rtx_drag"] + P["wbc_rtx_drag_frailty"] * fr.f_heme
        elif aza_active:
            wbc_drag = 0.6 + 0.3 * fr.f_heme
        else:
            wbc_drag = 0.0
        wbc = (P["wbc_ar"] * wbc + (1 - P["wbc_ar"]) * patient.baseline_wbc
               - wbc_drag + rng.normal(0, P["wbc_noise"]))
        wbc = float(np.clip(wbc, 0.3, 18))
        anc = float(np.clip(P["anc_frac"] * wbc + rng.normal(0, P["anc_noise"]), 0.1, 12))
        hgb = float(np.clip(P["hgb_ar"] * hgb + (1 - P["hgb_ar"]) * patient.baseline_hgb
                            - (P["hgb_cyc_drag"] + 0.2 * fr.f_heme if cyc_active else 0.0)
                            + rng.normal(0, P["hgb_noise"]), 6.0, 17.5))
        plt = float(np.clip(P["plt_ar"] * plt + (1 - P["plt_ar"]) * patient.baseline_plt
                            - (P["plt_cyc_drag"] + 8 * fr.f_heme if cyc_active else 0.0)
                            - (P["plt_rtx_drag"] if rtx_infusion else 0.0)
                            + rng.normal(0, P["plt_noise"]), 10, 650))
        # renal + inflammatory markers improve as disease activity falls
        creat = float(np.clip(0.7 * creat + 0.3 * patient.baseline_creat
                              - 0.10 * (1 if in_remission else 0) + rng.normal(0, 0.06), 0.4, 5.0))
        bun = float(np.clip(0.7 * bun + 0.3 * patient.baseline_bun + rng.normal(0, 2), 4, 90))

        # 4. BVAS/WG disease activity -----------------------------------------
        flare_label = "NONE"
        if remit_ever and day >= rday:
            # In remission ⇒ BVAS/WG = 0 by definition (decay happens before rday)
            if not in_remission:
                in_remission = True
                if patient.time_to_remission_day is None:
                    patient.time_to_remission_day = rday
            bvas = 0.0
        else:
            if remit_ever:   # declining toward 0, linear to remission day
                target = max(0.0, patient.baseline_bvaswg * (1 - (day - 1) / max(1, rday - 1)))
            else:            # partial responder plateau (never fully remits)
                target = max(2.0, patient.baseline_bvaswg * 0.45)
            bvas = float(max(0.0, 0.4 * bvas + 0.6 * target + rng.normal(0, 0.3)))
            if bvas < 0.5:
                bvas = 0.0

        # flare process once in remission (post-6mo maintenance phase: drives
        # secondary flare endpoints without corrupting the month-6 primary readout)
        if in_remission and bvas == 0.0 and day > max(rday, P["flare_window_start_day"]):
            log_h = (np.log(P["flare_base_haz"]) + P["flare_rtx"] * is_rtx
                     + P["flare_pr3"] * (patient.anca_type == "PR3")
                     + P["flare_relapsing"] * (0 if patient.new_diagnosis else 1)
                     + P["flare_pred_protect"] * pred + P["flare_frailty"] * fr.f_relapse)
            if rng.random() < min(0.6, np.exp(log_h)):
                severe = rng.random() < P["p_flare_severe"]
                flare_label = "SEVERE" if severe else "LIMITED"
                bvas = float(rng.uniform(3, 8) if severe else rng.uniform(1, 3))
                in_remission = False
                vdi = min(8, vdi + (1 if severe and rng.random() < 0.4 else 0))
                if patient.flare_day is None:
                    patient.flare_day = day
                    patient.flare_event = 1
        crp = float(np.clip(0.5 * crp + 0.5 * (1.0 + 0.6 * bvas) + rng.normal(0, 1.5), 0.1, 60))
        esr = float(np.clip(0.5 * esr + 0.5 * (8 + 2.0 * bvas) + rng.normal(0, 6), 2, 130))
        hematuria = int(np.clip(round((bvas / 4.0) * (1.5 if patient.renal_involvement else 0.6)
                                      + rng.normal(0, 0.3)), 0, 3)) if patient.renal_involvement else 0
        remission_now = (bvas == 0.0)

        # 5. AEs ---------------------------------------------------------------
        aes: List[Dict[str, Any]] = []
        # 5a. deterministic CTCAE grading of labs
        for name, val, grader, repkey in [
            ("Leukopenia", wbc, leuko_grade, "leuko_report"),
            ("Neutropenia", anc, neutro_grade, "leuko_report"),
            ("Anaemia", hgb, anemia_grade, "anemia_report"),
            ("Thrombocytopenia", plt, thrombo_grade, "thrombo_report"),
        ]:
            g = grader(val)
            if g >= 1 and rng.random() < P[repkey][str(min(g, 4))]:
                rel = "RELATED" if (cyc_active or aza_active or g >= 2) else "POSSIBLY RELATED"
                act = "DOSE REDUCED" if (g >= 3 and (cyc_active or aza_active)) else "DOSE NOT CHANGED"
                # Cytopenias rarely meet "serious" criteria (CTGov: ~0 serious leukopenia
                # despite 39 events) — flag serious only at Gr4 (life-threatening).
                aes.append(_ae(patient, name, g, rel, act, day, key, serious=(g >= 4)))
        # 5b. infection (any-grade; serious fraction)
        log_hi = (np.log(P["infect_base_haz"]) + P["infect_frailty"] * fr.f_infect
                  + P["infect_rtx"] * is_rtx + P["infect_cyc"] * (cyc_active or aza_active)
                  + P["infect_pred"] * pred)
        if rng.random() < min(0.6, np.exp(log_hi)):
            serious = rng.random() < P["p_infect_serious"]
            g = 3 if serious else (1 if rng.random() < 0.6 else 2)
            aes.append(_ae(patient, "Infection", g, "POSSIBLY RELATED",
                           "DOSE NOT CHANGED", day, key, serious=serious))
        # 5b'. serious disease-related event (vasculitis flare / pulmonary / cardiac /
        # renal serious AE — dominates the CTGov serious-event table beyond cytopenias)
        if rng.random() < P["infect_base_haz_serious_disease"] * np.exp(
                0.5 * fr.f_relapse + P["serious_disease_rtx"] * is_rtx):
            aes.append(_ae(patient, "Vasculitis-related event", 3, "NOT RELATED",
                           "DOSE NOT CHANGED", day, key, serious=True))
        # 5c. infusion reaction (RTX real infusions)
        if rtx_infusion and rng.random() < P["infusion_rxn_haz"]:
            g = 2 if rng.random() < 0.8 else 3
            aes.append(_ae(patient, "Infusion related reaction", g, "RELATED",
                           "DOSE NOT CHANGED" if g < 3 else "DRUG INTERRUPTED", day, key))
        # 5d. steroid AEs (∝ current prednisone dose)
        if pred > 0:
            ph = P["steroid_ae_per_mg"] * pred * np.exp(P["steroid_ae_frailty"] * fr.f_steroid)
            for nm in STEROID_AES:
                if rng.random() < min(0.5, ph):
                    aes.append(_ae(patient, nm, 1 if rng.random() < 0.8 else 2,
                                   "RELATED", "DOSE NOT CHANGED", day, key))
        # 5e. non-lab AEs (frailty cluster + arm)
        for name, (base, fattr, lrc, lrr, psev) in P["ae_nonlab"].items():
            log_h = np.log(base) + getattr(fr, fattr) + lrc * (cyc_active or aza_active) + lrr * is_rtx
            if ae_hist[name]:
                log_h += 0.3
            if rng.random() < min(0.9, 1 - np.exp(-np.exp(log_h))):
                severe = rng.random() < psev
                g = (3 if rng.random() < 0.85 else 4) if severe else (1 if rng.random() < 0.65 else 2)
                aes.append(_ae(patient, name, g, "POSSIBLY RELATED", "DOSE NOT CHANGED", day, key))
                ae_hist[name] = True

        if any(a["AESER"] == "Y" for a in aes):
            patient.serious_ae = 1

        # 6. dose modification --------------------------------------------------
        dose_action = "NONE"
        if (cyc_active or aza_active) and (leuko_grade(wbc) >= 3 or neutro_grade(anc) >= 3):
            dose_action = "REDUCED"
        if (rtx_infusion or rtx_placebo_inf) and wbc < 3.0:
            dose_action = "WITHHELD"     # protocol: pre-infusion WBC<3000 → withhold

        # record row
        patient.trajectory.append(TrajectoryRow(
            visit_key=key, visit_day=day, visit_num=num,
            bvaswg=round(bvas, 1), remission=remission_now, flare=flare_label, vdi=vdi,
            prednisone_dose=pred, cum_gc=round(cum_gc, 0),
            cyc_active=cyc_active, aza_active=aza_active,
            rtx_infusion=(rtx_infusion or rtx_placebo_inf), dose_action=dose_action,
            wbc=round(wbc, 2), anc=round(anc, 2), hgb=round(hgb, 1), plt=round(plt, 0),
            creat=round(creat, 2), bun=round(bun, 0), crp=round(crp, 1), esr=round(esr, 0),
            hematuria=hematuria, aes=aes, on_treatment=not discontinued,
        ))
        prev_day = day

        # 7. crossover (non-responders, V5–V8 window) + discontinuation --------
        if (not crossed) and (not remit_ever) and key in {"V5", "V6", "V7"} \
                and rng.random() < P["p_crossover_nonresponse"]:
            crossed = True
            patient.crossover_day = day
        log_hd = (P["disc_intercept"] + P["disc_frailty"] * fr.f_dropout
                  + P["disc_serious_ae"] * (1 if patient.serious_ae else 0)
                  + P["disc_severe_flare"] * (1 if flare_label == "SEVERE" else 0))
        if rng.random() < expit(log_hd):
            discontinued = True
            patient.discontinuation_day = day
            if flare_label == "SEVERE":
                patient.discontinuation_reason = "DISEASE FLARE"
            elif patient.serious_ae:
                patient.discontinuation_reason = "ADVERSE EVENT"
            else:
                patient.discontinuation_reason = str(rng.choice(
                    ["WITHDRAWAL BY SUBJECT", "PHYSICIAN DECISION", "OTHER"], p=[0.55, 0.3, 0.15]))

    # stash latent for outcomes
    patient._cr6_latent = cr6
