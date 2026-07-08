"""
Yₜ — CATH endpoint derivation from the simulated trajectory.

The endpoint is the CHANGE (Day21 − Baseline) in each peptide/compartment, read off the
SB/LB trajectory rows — never drawn directly. Non-completers have no Day21 row → change = None.
"""
from __future__ import annotations
from typing import Optional
import numpy as np

from .dag_state import CathPatient, COMPARTMENTS


def _get(traj, key):
    for r in traj:
        if r.visit_key == key:
            return r
    return None


def derive_endpoints(patient: CathPatient, rng, params: dict) -> None:
    traj = patient.trajectory
    base = _get(traj, "BASE")          # baseline biopsy (Day 0)
    scrn = _get(traj, "SCRN")          # baseline serum (screening)
    d21 = _get(traj, "D21")            # Day 21

    ch = {k: None for k in ("dCAMP_LES", "dCAMP_NL", "dHBD3_LES", "dHBD3_NL",
                            "dIL13_LES", "dIL13_NL", "dVITD25OH", "dPASI", "dIGE")}

    if patient.completer and d21 is not None and base is not None:
        skin_to_suffix = {"LESIONAL": "LES", "NONLESIONAL": "NL"}
        for comp in COMPARTMENTS[patient.dxgroup]:
            sfx = skin_to_suffix[comp]
            b0, b1 = base.biopsy[comp], d21.biopsy[comp]
            ch[f"dCAMP_{sfx}"] = round(b1.camp - b0.camp, 2)
            ch[f"dHBD3_{sfx}"] = round(b1.hbd3 - b0.hbd3, 2)
            ch[f"dIL13_{sfx}"] = round(b1.il13 - b0.il13, 2)
        if scrn is not None and d21.vitd_25oh is not None:
            ch["dVITD25OH"] = round(d21.vitd_25oh - scrn.vitd_25oh, 1)
        if base.pasi is not None and d21.pasi is not None:
            ch["dPASI"] = round(d21.pasi - base.pasi, 1)
        if scrn is not None and d21.ige is not None:
            ch["dIGE"] = round(d21.ige - scrn.ige, 1)

    patient.change = ch

    # serious-AE flag (should be 0 — CTGov posted no serious AEs)
    patient.serious_ae = int(any(a.get("AESER") == "Y" for r in traj for a in r.aes))

    # disposition / last contact (disposition + reason are set deterministically in run.py
    # from the published participantFlow; here we only finalize last_contact + AE↔DS link)
    if patient.completer:
        patient.disposition = "COMPLETED"
        patient.discontinuation_reason = None
        patient.last_contact_day = 21
    else:
        patient.disposition = "DISCONTINUED"
        patient.last_contact_day = patient.discontinuation_day or 10

    reconcile_ae_ds(patient)


def reconcile_ae_ds(patient: CathPatient) -> None:
    """AE↔DS traceability: a patient who left due to an adverse event must have exactly one
    AE flagged AEACN='DRUG WITHDRAWN' naming the cause. Deterministic projection of the existing
    AE→withdrawal→discontinuation edge (no new edge, no fresh draw)."""
    if patient.discontinuation_reason != "ADVERSE EVENT":
        return
    cutoff = patient.last_contact_day
    cands = [a for r in patient.trajectory for a in r.aes if a["AEDY"] <= cutoff]
    if not cands:
        return
    trigger = max(cands, key=lambda a: a["AEDY"])
    trigger["AEACN"] = "DRUG WITHDRAWN"
