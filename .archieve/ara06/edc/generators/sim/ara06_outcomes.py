"""
Y — ARA06 endpoint derivation from the simulated trajectory. All endpoints are
READ OFF the trajectory (never drawn directly):

  PRIMARY (mechanistic): mem_b_wk12 = switched-memory-B % at the Week-12 visit.
  SECONDARY (clinical, deterministic ACR/EULAR rules on the component trajectory):
    - das28resp_wk{12,24} = EULAR good-or-moderate response (DAS28 value + change)
    - acr20/acr50_wk{12,24} = ACR improvement rule (TJC & SJC + 3-of-5 components)
"""
from __future__ import annotations
from typing import Optional

from .dag_state import (Ara06Patient, eular_response,
                        PRIMARY_ENDPOINT_DAY, WEEK24_DAY)


def _acr(base_row, row, thr: float) -> int:
    """ACR-thr response vs the RECORDED baseline (V2) assessment: >=thr improvement
    in BOTH TJC and SJC, AND in >=3 of {patient global, physician global, pain, HAQ,
    CRP}. Uses the V2 trajectory row (not the latent baseline) so the endpoint is a
    pure function of the emitted DA trajectory (Step-4 gate g4)."""
    def imp(base, cur):
        return (base - cur) / base if base > 0 else 0.0
    tjc_ok = imp(base_row.tjc, row.tjc) >= thr
    sjc_ok = imp(base_row.sjc, row.sjc) >= thr
    five = [
        imp(base_row.ptglobal, row.ptglobal),
        imp(base_row.physglobal, row.physglobal),
        imp(base_row.pain, row.pain),
        imp(base_row.haqdi, row.haqdi),
        imp(base_row.crp, row.crp),
    ]
    n_five = sum(1 for v in five if v >= thr)
    return int(tjc_ok and sjc_ok and n_five >= 3)


def derive_endpoints(patient: Ara06Patient, rng, params: dict) -> None:
    traj = patient.trajectory
    v_base = next((r for r in traj if r.visit_key == "V2"), None)
    v_wk12 = next((r for r in traj if r.visit_day == PRIMARY_ENDPOINT_DAY), None)
    v_wk24 = next((r for r in traj if r.visit_day == WEEK24_DAY), None)
    das_base = v_base.das28 if v_base is not None else patient.baseline_das28

    # PRIMARY — switched-memory-B % at Week 12 (per-protocol: needs the visit) ---
    patient.mem_b_wk12 = v_wk12.mem_switched_pct if v_wk12 is not None else None

    # SECONDARY clinical (responder if the patient reached that visit) -----------
    if v_wk12 is not None and v_base is not None:
        patient.das28resp_wk12 = int(eular_response(v_wk12.das28, das_base) in ("GOOD", "MODERATE"))
        patient.acr20_wk12 = _acr(v_base, v_wk12, 0.20)
        patient.acr50_wk12 = _acr(v_base, v_wk12, 0.50)
    if v_wk24 is not None and v_base is not None:
        patient.das28resp_wk24 = int(eular_response(v_wk24.das28, das_base) in ("GOOD", "MODERATE"))
        patient.acr20_wk24 = _acr(v_base, v_wk24, 0.20)
        patient.acr50_wk24 = _acr(v_base, v_wk24, 0.50)

    # disposition ---------------------------------------------------------------
    if patient.discontinuation_day is not None:
        patient.disposition = "DISCONTINUED"
        patient.last_contact_day = patient.discontinuation_day
    else:
        patient.disposition = "COMPLETED"
        patient.last_contact_day = traj[-1].visit_day if traj else WEEK24_DAY

    reconcile_ae_ds(patient)


def reconcile_ae_ds(patient: Ara06Patient) -> None:
    """AE<->DS traceability (skill Step-5/6 gate). If a patient leaves due to an
    adverse event, the AE domain must name the cause (AEACN='DRUG WITHDRAWN').
    In ARA06 NO discontinuations are adverse-event-driven (ctgov disposition
    reasons are all administrative), so the AE-discontinuation set is empty and
    the gate holds trivially. This deterministic projection still resolves the
    link if a future calibration introduces an AE-driven reason."""
    if patient.discontinuation_reason != "ADVERSE EVENT":
        return
    cutoff = patient.last_contact_day
    candidates = [a for r in patient.trajectory for a in r.aes
                  if a["AESER"] == "Y" and a["AEDY"] <= cutoff]
    if not candidates:
        return
    trigger = max(candidates, key=lambda a: a["AEDY"])
    trigger["AEACN"] = "DRUG WITHDRAWN"
