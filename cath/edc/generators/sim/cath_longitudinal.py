"""
Lₜ — per-visit forward propagation for CATH.

Topological order:
  1. serum 25-OH-D at Day21 (the TREATMENT MEDIATOR): VITD arm rises, PLAC ~flat
  2. safety serum (Ca/PTH/creatinine) at Day21 — no hypercalcemia at 4000 IU
  3. skin biopsy expression at Day21 per compartment/peptide:
        Day21 = Baseline + δ, where δ's MEAN is routed through the realized 25-OH-D rise
        (arm → 25OHD → δ; no direct arm→endpoint edge) and a shared f_amp / f_th2 frailty
        induces within-patient correlation across peptides
  4. saliva / tape-strip cathelicidin (track biopsy CAMP via f_amp), bacterial CFU, PASI
  5. adverse events — sparse (CTGov: 0 serious, no PT ≥5%)

Endpoints are NOT drawn here — only the trajectory state. Non-completers get SCRN+BASE only.
"""
from __future__ import annotations
from typing import Dict, List, Any
import math
import numpy as np

from .dag_state import (CathPatient, TrajectoryRow, BiopsyState, SCHED, COMPARTMENTS,
                        visit_info)
from .params import outcome_cell


def _ae(patient, name, grade, day, key, action="DOSE NOT CHANGED", related="POSSIBLY RELATED"):
    info = visit_info(key)
    vd = patient.visit_date(day)
    sev = ["MILD", "MODERATE", "SEVERE", "LIFE-THREATENING"][max(1, min(grade, 4)) - 1]
    return {
        "USUBJID": patient.patient_id, "VISIT": key, "VISITNUM": info.get("VISITNUM", 0),
        "AEDY": day, "AESTDTC": vd.strftime("%Y-%m-%d"),
        "AETERM": name, "AEDECOD": name.upper(), "AEBODSYS": _SOC.get(name, "General disorders"),
        "AESEV": sev, "AETOXGR": grade, "AEREL": related, "AEACN": action,
        "AESER": "N", "AEOUT": "RECOVERED",
    }


_SOC = {
    "Constipation": "Gastrointestinal disorders", "Nausea": "Gastrointestinal disorders",
    "Abdominal distension": "Gastrointestinal disorders", "Headache": "Nervous system disorders",
    "Skin reaction": "Skin and subcutaneous tissue disorders",
    "Erythema": "Skin and subcutaneous tissue disorders",
}


def _resid_sd(target_sd: float, loading: float) -> float:
    """Residual noise SD so that Var(loading*N(0,1) + N(0,resid)) = target_sd²."""
    return float(np.sqrt(max(0.25, target_sd ** 2 - loading ** 2)))


def _vitals(rng):
    return (int(np.clip(rng.normal(122, 11), 95, 165)),
            int(np.clip(rng.normal(76, 8), 55, 100)),
            int(np.clip(rng.normal(72, 9), 50, 100)),
            round(float(np.clip(rng.normal(36.7, 0.3), 35.8, 38.0)), 1))


def simulate_trajectory(patient: CathPatient, rng: np.random.Generator, params: dict) -> None:
    P = params
    fr = patient.frailties
    is_vitd = patient.is_vitd
    g = patient.dxgroup
    # P(responded) = P(Δ25OHD > threshold) under the VITD rise distribution; used to rescale the
    # per-responder effect so the MARGINAL VITD cell mean equals the calibration target (no bias).
    p_resp = 0.5 * math.erfc((P["mediator_threshold"] - P["vitd_rise_mean"])
                             / (P["vitd_rise_sd"] * math.sqrt(2.0)))
    p_resp = min(max(p_resp, 1e-3), 1.0)

    # ---- SCRN (screening) — serum panel = baseline labs ---------------------
    info = visit_info("SCRN")
    patient.trajectory.append(TrajectoryRow(
        visit_key="SCRN", visit_day=-8, visit_num=info["VISITNUM"],
        vitd_25oh=patient.base_vitd_25oh, calcium=patient.base_calcium, pth=patient.base_pth,
        creat=patient.base_creat, ige=patient.base_ige, rast=patient.base_rast,
        on_treatment=False,
    ))

    # ---- BASE (Day 0) — baseline biopsy/saliva/tape/microbial/PASI + vitals --
    sbp, dbp, pul, tmp = _vitals(rng)
    base_row = TrajectoryRow(
        visit_key="BASE", visit_day=0, visit_num=visit_info("BASE")["VISITNUM"],
        biopsy={c: BiopsyState(c, b.camp, b.hbd3, b.il13, b.il4)
                for c, b in patient.base_biopsy.items()},
        saliva_camp=round(float(max(0.1, P["saliva_camp_base"] * (1 + P["saliva_camp_cv"] * rng.normal())
                                    + 0.5 * fr.f_amp)), 2),
        tape_camp={c: round(float(max(0.1, b.camp * 0.8 + rng.normal(0, 1.5))), 2)
                   for c, b in patient.base_biopsy.items()},
        cfu={c: round(v, 2) for c, v in patient.base_cfu.items()},
        pasi=patient.base_pasi, sysbp=sbp, diabp=dbp, pulse=pul, temp=tmp,
    )
    patient.trajectory.append(base_row)

    # ---- non-completers: discontinue before Day 21 (no D21 visit) ----------
    if not patient.completer:
        if patient.discontinuation_reason == "ADVERSE EVENT":
            # mild AE that triggers withdrawal; reconcile_ae_ds() flags it DRUG WITHDRAWN
            patient.trajectory[-1].aes.append(
                _ae(patient, "Nausea", 2, patient.discontinuation_day or 10, "BASE",
                    action="DOSE NOT CHANGED", related="POSSIBLY RELATED"))
        return

    # ---- D21 — treatment mediator, safety serum, biopsy change, AEs --------
    # 1. mediator: serum 25-OH-D rise
    if is_vitd:
        d25 = rng.normal(P["vitd_rise_mean"], P["vitd_rise_sd"])
    else:
        d25 = rng.normal(P["plac_rise_mean"], P["plac_rise_sd"])
    vitd_d21 = float(np.clip(patient.base_vitd_25oh + d25, 8.0, 90.0))
    responded = 1.0 if (vitd_d21 - patient.base_vitd_25oh) > P["mediator_threshold"] else 0.0

    # 2. safety serum (no hypercalcemia)
    ca_d21 = float(np.clip(patient.base_calcium + rng.normal(0, P["ca_day21_sd"]), 8.4, 10.6))
    pth_d21 = float(np.clip(patient.base_pth - P["pth_vitd_drop"] * is_vitd
                            + rng.normal(0, P["pth_day21_sd"]), 8.0, 90.0))
    creat_d21 = float(np.clip(patient.base_creat + rng.normal(0, P["creat_day21_sd"]), 0.4, 1.5))
    ige_d21 = float(np.clip(patient.base_ige * (1 + P["ige_change_cv"] * rng.normal()), 1.0, 30000.0))

    # 3. biopsy expression change δ per compartment/peptide (mean routed via mediator)
    d21_biopsy: Dict[str, BiopsyState] = {}
    dcamp_store: Dict[str, float] = {}
    for comp in COMPARTMENTS[g]:
        b0 = patient.base_biopsy[comp]

        def delta(peptide, loading, frailty_val):
            m_plac, sd_plac = outcome_cell(peptide, g, comp, "PLAC", P)
            m_vitd, sd_vitd = outcome_cell(peptide, g, comp, "VITD", P)
            if is_vitd:
                # effect realized only in 25-OH-D responders (mediation), but the per-responder
                # effect `eff` is rescaled so the marginal mean p·eff + (1−p)·m_plac == m_vitd.
                eff = (m_vitd - (1.0 - p_resp) * m_plac) / p_resp
                mean = m_plac + (eff - m_plac) * responded
                sd = sd_vitd
            else:
                mean = m_plac
                sd = sd_plac
            return mean + loading * frailty_val + rng.normal(0, _resid_sd(sd, loading))

        dcamp = delta("CAMP", P["f_amp_load"], fr.f_amp)
        dhbd3 = delta("HBD3", P["f_amp_load"], fr.f_amp)
        dil13 = delta("IL13", P["f_th2_load"], fr.f_th2)
        dil4 = 0.5 * dil13 + rng.normal(0, 1.2)        # IL-4 tracks IL-13 (model; no target)
        dcamp_store[comp] = dcamp
        d21_biopsy[comp] = BiopsyState(
            comp,
            camp=round(float(max(0.1, b0.camp + dcamp)), 2),
            hbd3=round(float(max(0.1, b0.hbd3 + dhbd3)), 2),
            il13=round(float(max(0.1, b0.il13 + dil13)), 2),
            il4=round(float(max(0.1, b0.il4 + dil4)), 2),
        )

    # 4. saliva / tape (track biopsy CAMP via f_amp), CFU, PASI
    saliva_d21 = round(float(max(0.1, base_row.saliva_camp + 0.6 * responded * is_vitd
                                 + 0.6 * fr.f_amp + rng.normal(0, 1.5))), 2)
    tape_d21 = {c: round(float(max(0.1, base_row.tape_camp[c] + P["tape_camp_load"] * dcamp_store[c]
                                  + rng.normal(0, 1.2))), 2)
                for c in COMPARTMENTS[g]}
    cfu_d21 = {c: round(float(np.clip(patient.base_cfu[c] + rng.normal(0, 0.3), 1.0, 8.0)), 2)
               for c in COMPARTMENTS[g]}
    pasi_d21 = (float(np.clip(patient.base_pasi + P["pasi_change_mean"] + rng.normal(0, P["pasi_change_sd"]),
                              0.0, 30.0)) if g == "PSO" else None)

    sbp2, dbp2, pul2, tmp2 = _vitals(rng)
    d21_row = TrajectoryRow(
        visit_key="D21", visit_day=21, visit_num=visit_info("D21")["VISITNUM"],
        vitd_25oh=round(vitd_d21, 1), calcium=round(ca_d21, 1), pth=round(pth_d21, 1),
        creat=round(creat_d21, 2), ige=round(ige_d21, 1), rast=patient.base_rast,
        biopsy=d21_biopsy, saliva_camp=saliva_d21, tape_camp=tape_d21,
        cfu={c: v for c, v in cfu_d21.items()},
        pasi=round(pasi_d21, 1) if pasi_d21 is not None else None,
        sysbp=sbp2, diabp=dbp2, pulse=pul2, temp=tmp2,
    )

    # 5. sparse adverse events (mild, non-serious)
    for nm in P["ae_terms"]:
        if rng.random() < P["ae_base_haz"]:
            d21_row.aes.append(_ae(patient, nm, 1, 21, "D21"))
    for nm in P["ae_proc_terms"]:
        if rng.random() < P["ae_proc_haz"]:
            d21_row.aes.append(_ae(patient, nm, 1, 21, "D21", related="NOT RELATED"))

    patient.trajectory.append(d21_row)
